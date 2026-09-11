"""Source-backed visual queries. Business semantics belong to the calling model."""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import math
import re
import tempfile
import warnings
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit

import httpx
from PIL import Image

from .media import MAX_IMAGE_PIXELS, _AssetError, download_assets, render_region
from .normalize import normalize_design
from .text import text_spec
from .variants import VariantSelectionError, public_asset, select_variants, validate_downloaded_variant


class DesignError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def parse_design_reference(url: str, design_id: str | None = None) -> dict:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in {"lanhuapp.com", "www.lanhuapp.com"}:
        raise DesignError("InvalidURL", "Use a full https://lanhuapp.com design URL.")
    route, _, query = parsed.fragment.partition("?")
    params = {key: values[-1] for key, values in parse_qs(query or parsed.query).items()}
    project_id = params.get("pid") or params.get("project_id")
    selected = design_id or params.get("image_id")
    if not project_id or not selected:
        raise DesignError("DesignRequired", "Select a design_id from lanhu_get_designs or use its detail URL.")
    if not design_id and (route.endswith("/product") or (
        params.get("docType") == "axure" and params.get("type") != "image" and "detailDetach" not in route
    )):
        raise DesignError("NotDesignURL", "This link selects a prototype. Supply an explicit design_id.")
    return {"project_id": project_id, "team_id": params.get("tid") or params.get("team_id"),
            "design_id": selected, "url_version": params.get("versionId"),
            "mixed_document_query": bool(params.get("docId") and params["docId"] != selected)}


def select_version(image: dict, requested: str | None) -> dict:
    versions = image.get("versions") or []
    if not versions:
        raise DesignError("VersionUnavailable", "The design has no accessible versions.")
    if requested and requested != "latest":
        selected = next((v for v in versions if str(v.get("id")) == requested), None)
        if selected is None:
            raise DesignError("VersionUnavailable", "The requested version does not belong to this design.")
    else:
        latest = image.get("latest_version")
        selected = next((v for v in versions if v.get("id") == latest), versions[0])
    if not selected.get("id") or not selected.get("json_url"):
        raise DesignError("SourceUnavailable", "The selected version has no raw design data.")
    return selected


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".design-", delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(value)
            handle.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def _atomic_json(path: Path, value: object) -> None:
    _atomic_bytes(path, json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8"))


def _public_asset(asset: dict) -> dict:
    return public_asset(asset)


def _processed_image_url(url: str, operation: str) -> str:
    parts = urlsplit(url)
    query = parse_qs(parts.query, keep_blank_values=True)
    query["x-oss-process"] = [operation]
    return urlunsplit(parts._replace(query=urlencode(query, doseq=True)))


def _image_size(data: bytes, *, verify: bool = False) -> dict:
    # Reading dimensions does not decode a giant raster. Full raster decoding
    # retains the strict pixel limit in media._open_raster.
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                size = {"width": image.width, "height": image.height}
                if verify:
                    if image.width * image.height > MAX_IMAGE_PIXELS:
                        raise DesignError("image_too_large", "Processed image exceeds the decoder pixel limit.")
                    image.verify()
                return size
    except DesignError:
        raise
    except Image.DecompressionBombError as exc:
        raise DesignError("image_too_large", "Source exceeds supported image-header limits.") from exc
    except Exception as exc:
        raise DesignError("InvalidReference", "The reference image cannot be decoded.") from exc


def _font_requirements(nodes: list[dict]) -> list[dict]:
    families = {}
    for node in nodes:
        for requirement in text_spec(node)["font_requirements"]:
            family = requirement["family"]
            if family not in families:
                families[family] = {"family": family, "availability": "not_checked", "source": "design",
                                    "weights": [], "node_count": 0, "sample_node_ids": []}
            entry = families[family]
            entry["weights"] = sorted(set(entry["weights"]) | set(requirement.get("weights") or []),
                                      key=lambda value: (isinstance(value, str), str(value)))
            entry["node_count"] += 1
            if len(entry["sample_node_ids"]) < 5:
                entry["sample_node_ids"].append(node["node_id"])
    return list(families.values())


def _intersects(bounds: dict | None, region: dict) -> bool:
    return bool(bounds and bounds["x"] < region["x"] + region["width"]
                and bounds["x"] + bounds["width"] > region["x"]
                and bounds["y"] < region["y"] + region["height"]
                and bounds["y"] + bounds["height"] > region["y"])


class DesignService:
    def __init__(self, root: Path, cookie: str = "", dds_cookie: str = "", timeout: float = 30):
        # A changed account/session must not retrieve an old account's cached artifacts.
        # This is still a single configured-account server, not per-caller authorization.
        namespace = _digest({"cookie": cookie, "dds_cookie": dds_cookie or cookie})[:24]
        self.root = Path(root) / namespace
        self.cookie = cookie
        self.dds_cookie = dds_cookie or cookie
        self.timeout = timeout
        self._lock = asyncio.Lock()

    async def fetch_bytes(self, url: str) -> bytes:
        """Origin-scoped credentials, bounded reads, and validated redirects."""
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False) as client:
            for _ in range(5):
                parsed = urlsplit(url)
                host = parsed.hostname or ""
                allowed = (host == "lanhuapp.com" or host.endswith(".lanhuapp.com") or host in {
                    "lanhu.oss-cn-beijing.aliyuncs.com", "lanhu-dds-backend.oss-cn-beijing.aliyuncs.com"})
                if parsed.scheme != "https" or not allowed or parsed.username or parsed.port not in (None, 443):
                    raise DesignError("UnsupportedResourceHost", "The resource host is not an approved Lanhu origin.")
                headers = {"Referer": "https://lanhuapp.com/", "User-Agent": "Lanhu-MCP-design-context/1"}
                if host == "lanhuapp.com":
                    headers["Cookie"] = self.cookie
                elif host == "dds.lanhuapp.com":
                    headers.update({"Cookie": self.dds_cookie, "Referer": "https://dds.lanhuapp.com/",
                                    "Authorization": "Basic dW5kZWZpbmVkOg=="})
                async with client.stream("GET", url, headers=headers) as response:
                    if response.is_redirect:
                        url = urljoin(url, response.headers.get("location", ""))
                        continue
                    if response.status_code in (401, 403):
                        raise DesignError("AccessDenied", "Lanhu rejected this resource. Check login and project access.")
                    if response.status_code >= 400:
                        raise DesignError("DownloadFailed", f"Resource returned HTTP {response.status_code}.")
                    data = bytearray()
                    async for chunk in response.aiter_bytes():
                        data.extend(chunk)
                        if len(data) > 64 * 1024 * 1024:
                            raise DesignError("ResourceTooLarge", "A source resource exceeds 64 MiB.")
                    return bytes(data)
        raise DesignError("RedirectLimit", "Resource redirected too many times.")

    async def fetch_json(self, url: str) -> dict:
        try:
            value = json.loads(await self.fetch_bytes(url))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise DesignError("InvalidSource", "Expected JSON, possibly an expired login or unavailable source.") from exc
        if not isinstance(value, dict):
            raise DesignError("InvalidSource", "Expected a JSON object.")
        return value

    @staticmethod
    def _api_result(data: dict) -> dict:
        if str(data.get("code")) not in {"0", "00000"}:
            raise DesignError("APIRejected", "Lanhu API rejected the request (code=" + str(data.get("code")) + ").")
        return data.get("result") or data.get("data") or {}

    def _snapshot_dir(self, snapshot_id: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{32}", snapshot_id):
            raise DesignError("InvalidSnapshot", "Invalid snapshot identifier.")
        return self.root / snapshot_id

    def load(self, snapshot_id: str) -> dict:
        path = self._snapshot_dir(snapshot_id) / "snapshot.json"
        if not path.is_file():
            raise DesignError("SnapshotMissing", "Prepare the design first; this snapshot is not cached here.")
        return json.loads(path.read_text(encoding="utf-8"))

    async def prepare(self, url: str, design_id: str | None = None, version_id: str | None = None) -> dict:
        ref = parse_design_reference(url, design_id)
        requested = version_id if version_id is not None else ref["url_version"]
        query = {"project_id": ref["project_id"], "image_id": ref["design_id"], "dds_status": 1}
        if ref["team_id"]:
            query["team_id"] = ref["team_id"]
        info = self._api_result(await self.fetch_json("https://lanhuapp.com/api/project/image?" + urlencode(query)))
        if info.get("id") and str(info["id"]) != ref["design_id"]:
            raise DesignError("DesignMismatch", "The returned design does not match the requested ID.")
        if info.get("type") in {"axure", "pdf", "word", "ppt", "excel"}:
            raise DesignError("NotDesign", "Use a UI design image, not a product document.")
        version = select_version(info, requested)
        raw = await self.fetch_json(version["json_url"])
        normalized = normalize_design(raw)
        canvas = normalized["canvas"]
        if any(g.get("code") == "nonzero_canvas_origin_unverified" for g in normalized["gaps"]):
            raise DesignError("UnsupportedCoordinates", "This source has a nonzero canvas origin whose mapping is not verified.")
        if not canvas.get("width") or not canvas.get("height"):
            raise DesignError("UnsupportedCoordinates", "Raw source does not provide a reliable canvas size.")
        reference_url = version.get("url")
        if not reference_url:
            raise DesignError("ReferenceUnavailable", "No reference image belongs to this version.")
        # Remove only the CDN image transformation, retaining unrelated signed parameters.
        parts = urlsplit(reference_url)
        query_parts = {k: values for k, values in parse_qs(parts.query, keep_blank_values=True).items()
                       if k != "x-oss-process"}
        reference_url = urlunsplit(parts._replace(query=urlencode(query_parts, doseq=True)))
        reference = await self.fetch_bytes(reference_url)
        original_size = _image_size(reference)
        original_hash = hashlib.sha256(reference).hexdigest()
        preview_downsampled = original_size["width"] * original_size["height"] > MAX_IMAGE_PIXELS
        if preview_downsampled:
            reference = await self.fetch_bytes(_processed_image_url(reference_url, "image/resize,l_4096/format,png"))
        stored_size = _image_size(reference, verify=True)
        width, height = stored_size["width"], stored_size["height"]
        if preview_downsampled and max(width, height) > 4096:
            raise DesignError("PreviewUnavailable", "Source provider did not honor the bounded preview request.")
        original_ratio_error = abs((original_size["width"] / original_size["height"]) / (canvas["width"] / canvas["height"]) - 1)
        ratio_error = abs((width / height) / (canvas["width"] / canvas["height"]) - 1)
        if ratio_error > 0.01 or original_ratio_error > 0.01:
            raise DesignError("CoordinateMismatch", "Reference and source canvas aspect ratios do not match.")
        snapshot_id = _digest({"schema": 2, "project": ref["project_id"], "team": ref["team_id"],
                               "design": ref["design_id"], "version": version["id"],
                               "raw_hash": _digest(raw), "normalized_hash": _digest(normalized),
                               "image_hash": hashlib.sha256(reference).hexdigest(), "original_hash": original_hash})[:32]
        async with self._lock:
            directory = self._snapshot_dir(snapshot_id)
            if not (directory / "snapshot.json").is_file():
                dds = None
                dds_gap = None
                try:
                    dds_info = self._api_result(await self.fetch_json(
                        "https://dds.lanhuapp.com/api/dds/image/store_schema_revise?" + urlencode({"version_id": version["id"]})))
                    if dds_info.get("data_resource_url"):
                        dds = await self.fetch_json(dds_info["data_resource_url"])
                    else:
                        dds_gap = "No DDS layout available for this exact version."
                except (DesignError, httpx.HTTPError):
                    dds_gap = "DDS unavailable for this exact version; raw nodes remain available."
                snapshot = {**normalized, "schema_version": "2", "snapshot_id": snapshot_id, "project_id": ref["project_id"],
                            "design_id": ref["design_id"], "design_name": info.get("name", ""),
                            "resolved_version": version["id"], "version_label": version.get("version_info"),
                            "reference_size": {"width": width, "height": height},
                            "original_reference_size": original_size, "original_reference_url": reference_url,
                            "preview_downsampled": preview_downsampled,
                            "dds_layout": dds, "dds_gap": dds_gap}
                directory.mkdir(parents=True, exist_ok=True)
                _atomic_bytes(directory / "reference.bin", reference)
                _atomic_json(directory / "snapshot.json", snapshot)
            else:
                cached = self.load(snapshot_id)
                # The immutable bytes/version are unchanged, but signed transport
                # URLs may be refreshed by Lanhu. Do not retain an expired URL.
                if cached.get("original_reference_url") != reference_url:
                    cached["original_reference_url"] = reference_url
                    _atomic_json(directory / "snapshot.json", cached)
        snapshot = self.load(snapshot_id)
        return {"status": "complete", "snapshot_id": snapshot_id, "design_id": ref["design_id"],
                "design_name": snapshot["design_name"], "requested_version": requested or "latest",
                "resolved_version": snapshot["resolved_version"], "source_type": snapshot["source_type"],
                "canvas": canvas, "coordinate_space": "source_canvas", "reference_size": snapshot["reference_size"],
                "original_reference_size": original_size, "preview_downsampled": preview_downsampled,
                "scale_metadata": snapshot.get("scale_metadata", {}),
                "font_requirements": _font_requirements(snapshot["nodes"]),
                "total_nodes": len(snapshot["nodes"]), "asset_counts": {
                    kind: sum(a["kind"] == kind for a in snapshot["assets"])
                    for kind in sorted({a["kind"] for a in snapshot["assets"]})},
                "capabilities": {"raw_nodes": True, "dds_layout": snapshot["dds_layout"] is not None,
                                 "semantic_components": False},
                "gaps": snapshot["gaps"] + ([snapshot["dds_gap"]] if snapshot["dds_gap"] else [])}

    def query(self, snapshot_id: str, *, region: dict | None = None, node_ids: list[str] | None = None,
              offset: int = 0, limit: int = 30, annotate: bool = True, max_edge: int = 1400,
              include_hidden: bool = False, include_styles: bool = True, _reference: tuple | None = None) -> dict:
        if not 1 <= limit <= 60 or offset < 0:
            raise DesignError("InvalidPagination", "Use offset >= 0 and limit between 1 and 60.")
        snapshot = self.load(snapshot_id)
        all_nodes = {n["node_id"]: n for n in snapshot["nodes"]}
        for node in all_nodes.values():
            visibility = node.get("source_visible")
            parent = node.get("parent_id")
            seen = {node["node_id"]}
            while parent in all_nodes and parent not in seen:
                seen.add(parent)
                ancestor = all_nodes[parent]
                if ancestor.get("source_visible") is False:
                    visibility = False
                    break
                parent = ancestor.get("parent_id")
            node["effective_source_visible"] = visibility
        wanted = set(node_ids or [])
        if wanted - all_nodes.keys():
            raise DesignError("UnknownNode", "Some node IDs do not belong to this snapshot.")
        if region is not None:
            if set(region) != {"x", "y", "width", "height"} or any(
                isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in region.values()
            ) or region["width"] <= 0 or region["height"] <= 0:
                raise DesignError("InvalidRegion", "Region requires finite source-canvas x/y and positive width/height.")
        nodes = [n for n in snapshot["nodes"] if (not wanted or n["node_id"] in wanted)
                 and (include_hidden or n.get("effective_source_visible") is not False)
                 and (region is None or _intersects(n.get("bounds"), region))]
        total = len(nodes)
        selected = nodes[offset:offset + limit]
        if wanted and region is None:
            boxes = [n["bounds"] for n in nodes if n.get("bounds")]
            if boxes:
                x, y = min(b["x"] for b in boxes), min(b["y"] for b in boxes)
                region = {"x": x - 12, "y": y - 12,
                          "width": max(b["x"] + b["width"] for b in boxes) - x + 24,
                          "height": max(b["y"] + b["height"] for b in boxes) - y + 24}
        directory = self._snapshot_dir(snapshot_id)
        drawable = [{**node, "source_visible": node.get("effective_source_visible")} for node in selected]
        reference_bytes, reference_canvas = _reference or ((directory / "reference.bin").read_bytes(), snapshot["canvas"])
        visual_mode = "original_region" if _reference else "bounded_preview" if snapshot.get("preview_downsampled") else "original_reference"
        try:
            visual = render_region(reference_bytes, reference_canvas, drawable,
                                   region=region, max_edge=max_edge, annotate=annotate)
        except _AssetError as exc:
            raise DesignError(exc.code, str(exc)) from exc
        image_bytes = visual.pop("image_bytes")
        render_gaps = visual.pop("gaps", [])
        source_gaps = list(snapshot["gaps"])
        if visual_mode == "bounded_preview":
            source_gaps.append({"code": "bounded_reference_preview", "message": "Overview uses a reduced reference; inspect a region for native-source detail."})
        if snapshot.get("dds_gap"):
            source_gaps.append({"code": "dds_unavailable", "message": snapshot["dds_gap"]})
        preview_id = _digest({"region": region, "ids": [n["node_id"] for n in selected], "edge": max_edge,
                              "annotate": annotate, "visual_mode": visual_mode})[:32]
        _atomic_bytes(directory / f"preview-{preview_id}.png", image_bytes)
        clean_image_bytes = None
        clean_preview_id = preview_id
        if annotate:
            clean_image_bytes = render_region(reference_bytes, reference_canvas, drawable,
                                              region=region, max_edge=max_edge, annotate=False)["image_bytes"]
            clean_preview_id = _digest({"preview": preview_id, "role": "clean_reference"})[:32]
            _atomic_bytes(directory / f"preview-{clean_preview_id}.png", clean_image_bytes)
        ancestors = {}
        for n in selected:
            seen = {n["node_id"]}
            parent = n.get("parent_id")
            while parent in all_nodes and parent not in seen:
                seen.add(parent)
                ancestor = all_nodes[parent]
                ancestors[parent] = {k: ancestor.get(k) for k in ("node_id", "parent_id", "name", "bounds")}
                parent = ancestor.get("parent_id")
        asset_ids = {a for n in selected for a in n.get("asset_ids", [])}
        public_nodes = [{k: v for k, v in n.items() if include_styles or k != "raw_style"} for n in selected]
        if include_styles:
            for node in public_nodes:
                node["text_spec"] = text_spec(node)
        dds_nodes = []
        source_ids = {}
        for node in all_nodes.values():
            source_id = node.get("source_id")
            if source_id is not None:
                source_ids.setdefault(str(source_id), []).append(node["node_id"])
        selected_ids = {n["node_id"] for n in selected}
        def collect_dds(node):
            if not isinstance(node, dict):
                return
            matches = source_ids.get(str(node.get("layerId")), [])
            if len(matches) == 1 and matches[0] in selected_ids:
                dds_nodes.append({"node_id": matches[0], "source": "dds_derived_layout",
                                  "style": (node.get("props") or {}).get("style", {}),
                                  "value": (node.get("data") or {}).get("value")})
            for child in node.get("children") or []:
                collect_dds(child)
        collect_dds(snapshot.get("dds_layout"))
        return {"status": "complete", "snapshot_id": snapshot_id, "resolved_version": snapshot["resolved_version"],
                "coordinate_space": "source_canvas", "canvas": snapshot["canvas"], **visual,
                "visual_source": visual_mode, "original_reference_size": snapshot.get("original_reference_size", snapshot["reference_size"]),
                "font_requirements": _font_requirements(selected),
                "scale_metadata": snapshot.get("scale_metadata", {}),
                "source_gaps": source_gaps, "render_gaps": render_gaps, "gaps": source_gaps + render_gaps,
                "nodes": public_nodes, "ancestors": list(ancestors.values()), "dds_layout_suggestions": dds_nodes,
                "assets": [_public_asset(a) for a in snapshot["assets"] if a["asset_id"] in asset_ids],
                "total": total, "returned": len(selected), "next_offset": offset + limit if offset + limit < total else None,
                "truncated": offset + limit < total, "preview_resource": f"lanhu://design/{snapshot_id}/preview/{preview_id}",
                "reference_crop_resource": f"lanhu://design/{snapshot_id}/preview/{clean_preview_id}",
                "image_bytes": image_bytes, "clean_image_bytes": clean_image_bytes}

    async def inspect(self, snapshot_id: str, **options) -> dict:
        result = self.query(snapshot_id, **options)
        snapshot = self.load(snapshot_id)
        if not snapshot.get("preview_downsampled"):
            return result
        native = snapshot["original_reference_size"]
        canvas = snapshot["canvas"]
        region = result["source_region"]
        sx, sy = native["width"] / canvas["width"], native["height"] / canvas["height"]
        x, y = max(0, math.floor(region["x"] * sx)), max(0, math.floor(region["y"] * sy))
        right = min(native["width"], math.ceil((region["x"] + region["width"]) * sx))
        bottom = min(native["height"], math.ceil((region["y"] + region["height"]) * sy))
        width, height = right - x, bottom - y
        if max(width, height) > 16384:
            result["gaps"].append({"code": "region_provider_limit", "message": "Choose a smaller region for native-source detail."})
            return result
        edge = options.get("max_edge", 1400)
        operation = f"image/crop,x_{x},y_{y},w_{width},h_{height}/resize,l_{edge}/format,png"
        cache_path = self._snapshot_dir(snapshot_id) / f"region-source-{_digest(operation)[:32]}.png"
        try:
            reduction = min(1.0, edge / max(width, height))
            expected = {"width": max(1, round(width * reduction)), "height": max(1, round(height * reduction))}
            def verify_region(data):
                actual = _image_size(data, verify=True)
                for axis in ("width", "height"):
                    tolerance = 1 if reduction < 1 and expected[axis] > 1 else 0
                    if abs(actual[axis] - expected[axis]) > tolerance:
                        raise DesignError("RegionMismatch", "Source provider returned unexpected crop resolution.")
            data = None
            if cache_path.is_file():
                try:
                    data = cache_path.read_bytes()
                    verify_region(data)
                except (DesignError, OSError):
                    data = None
            if data is None:
                data = await self.fetch_bytes(_processed_image_url(snapshot["original_reference_url"], operation))
                verify_region(data)
            _atomic_bytes(cache_path, data)
            image_canvas = {"x": x / sx, "y": y / sy, "width": width / sx, "height": height / sy}
            return self.query(snapshot_id, **options, _reference=(data, image_canvas))
        except (DesignError, httpx.HTTPError, OSError) as exc:
            result["gaps"].append({"code": "native_region_unavailable", "reason": getattr(exc, "code", type(exc).__name__),
                                   "message": "Native detail is unavailable; the returned crop uses the bounded preview."})
            return result

    async def export(self, snapshot_id: str, asset_ids: list[str] | None = None,
                     kind: str = "exported_asset", target_dpr: float = 2, format_preference: str = "original") -> dict:
        snapshot = self.load(snapshot_id)
        assets = snapshot["assets"]
        if kind not in {"exported_asset", "render_fallback", "image_fill", "all"}:
            raise DesignError("InvalidAssetKind", "Select exported_asset, render_fallback, image_fill or all.")
        if asset_ids is not None:
            wanted = set(asset_ids)
            if wanted - {a["asset_id"] for a in assets}:
                raise DesignError("UnknownAsset", "Some asset IDs do not belong to this snapshot.")
            selected = [a for a in assets if a["asset_id"] in wanted]
        else:
            selected = [a for a in assets if kind == "all" or a["kind"] == kind]
        if not selected:
            raise DesignError("NoAssets", "No assets match this selection.")
        try:
            selected = select_variants(selected, format_preference)
        except VariantSelectionError as exc:
            raise DesignError(exc.code, str(exc)) from exc
        bundle_id = _digest({"ids": sorted(a["asset_id"] for a in selected), "dpr": target_dpr,
                             "format_preference": format_preference})[:32]
        directory = self._snapshot_dir(snapshot_id) / "exports" / bundle_id
        async with self._lock:
            manifest = await download_assets(selected, directory, fetch=self.fetch_bytes, target_dpr=target_dpr)
            by_id = {a["asset_id"]: a for a in selected}
            verified = []
            for asset in manifest["assets"]:
                try:
                    validate_downloaded_variant(by_id[asset["asset_id"]], asset)
                    verified.append(asset)
                except VariantSelectionError as exc:
                    manifest["failed"].append({"asset_id": asset["asset_id"], "node_id": asset["node_id"],
                                               "kind": asset["kind"], "error": exc.code, "reason": str(exc),
                                               "actual_format": asset["format"]})
            manifest["assets"] = verified
            manifest["status"] = "complete" if not manifest["failed"] else "partial" if verified else "failed"
            manifest["counts"] = {"requested": len(selected), "succeeded": len(verified), "failed": len(manifest["failed"]),
                                  "cached": sum(bool(asset.get("cached")) for asset in verified)}
            selection_fields = ("base_asset_id", "original_variant_id", "requested_preference", "selected_variant_id",
                                "selected_format_hint", "selected_source_field", "selection_fallback")
            for asset in manifest["assets"] + manifest["failed"]:
                source = by_id[asset["asset_id"]]
                asset.update({key: source.get(key) for key in selection_fields})
            manifest.update({"snapshot_id": snapshot_id, "design_id": snapshot["design_id"],
                             "resolved_version": snapshot["resolved_version"], "bundle_id": bundle_id,
                             "manifest_path": "manifest.json"})
            _atomic_json(directory / "manifest.json", manifest)
            archive = directory / "bundle.zip"
            with tempfile.NamedTemporaryFile(dir=directory, prefix=".bundle-", delete=False) as handle:
                temporary = Path(handle.name)
            try:
                with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as bundle:
                    bundle.write(directory / "manifest.json", "manifest.json")
                    for asset in manifest["assets"]:
                        if asset.get("relative_path"):
                            bundle.write(directory / asset["relative_path"], asset["relative_path"])
                temporary.replace(archive)
            finally:
                temporary.unlink(missing_ok=True)
        return {**manifest, "bundle_resource": f"lanhu://design/{snapshot_id}/bundle/{bundle_id}",
                "delivery": "Read bundle_resource with MCP and install on the client using python -m lanhu_design.install.",
                "bundle_bytes": archive.stat().st_size}

    def artifact(self, snapshot_id: str, kind: str, artifact_id: str) -> bytes:
        directory = self._snapshot_dir(snapshot_id)
        if not re.fullmatch(r"[a-f0-9]{32}", artifact_id):
            raise DesignError("InvalidArtifact", "Invalid artifact identifier.")
        if kind == "preview":
            path = directory / f"preview-{artifact_id}.png"
        elif kind == "bundle":
            path = directory / "exports" / artifact_id / "bundle.zip"
        else:
            raise DesignError("InvalidArtifact", "Unsupported artifact kind.")
        if not path.is_file():
            raise DesignError("ArtifactMissing", "Generate this artifact first.")
        return path.read_bytes()
