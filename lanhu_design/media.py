"""Deterministic image evidence and validated, original-resolution asset export.

This module deliberately does not infer component semantics from layer names.
Coordinates are design coordinates; asset names never determine filesystem paths.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import math
import os
import re
import tempfile
import warnings
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Awaitable, Callable

from PIL import Image, ImageDraw, UnidentifiedImageError


MAX_IMAGE_PIXELS = 80_000_000
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_ANNOTATED_NODES = 500
MAX_OUTPUT_EDGE = 4096
_RASTER_EXTENSIONS = {
    "PNG": "png", "JPEG": "jpg", "WEBP": "webp", "GIF": "gif",
    "BMP": "bmp", "TIFF": "tiff", "ICO": "ico", "AVIF": "avif",
    "JPEG2000": "jp2",
}


class _AssetError(ValueError):
    """Only fixed, non-sensitive messages may be returned to callers."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _number(value: Any, field: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    result = float(value)
    if not math.isfinite(result) or (positive and result <= 0):
        raise ValueError(f"{field} must be {'positive and ' if positive else ''}finite")
    return result


def _rect(value: dict, field: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be a bounds object")
    return {
        "x": _number(value.get("x", 0), f"{field}.x"),
        "y": _number(value.get("y", 0), f"{field}.y"),
        "width": _number(value.get("width"), f"{field}.width", positive=True),
        "height": _number(value.get("height"), f"{field}.height", positive=True),
    }


def _intersection(a: dict, b: dict) -> dict | None:
    x, y = max(a["x"], b["x"]), max(a["y"], b["y"])
    right = min(a["x"] + a["width"], b["x"] + b["width"])
    bottom = min(a["y"] + a["height"], b["y"] + b["height"])
    if right <= x or bottom <= y:
        return None
    return {"x": x, "y": y, "width": right - x, "height": bottom - y}


def _open_raster(data: bytes) -> Image.Image:
    if not isinstance(data, bytes) or not data or len(data) > MAX_FILE_BYTES:
        raise _AssetError("invalid_bytes", "Image is empty or exceeds the 64 MiB file limit")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(io.BytesIO(data))
            if image.width * image.height > MAX_IMAGE_PIXELS:
                raise _AssetError("image_too_large", "Image exceeds the 80 million pixel limit")
            image.verify()
            image = Image.open(io.BytesIO(data))
            image.load()
            return image
    except _AssetError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise _AssetError("image_too_large", "Image exceeds the decoder pixel limit") from None
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        raise _AssetError("invalid_image", "Content is not a complete supported image") from None


def _geometric_gaps(labels: list[dict]) -> list[dict]:
    """Nearest disjoint edge on each axis, only with overlap on the other axis."""
    nearest: dict[tuple, dict] = {}
    for i, first in enumerate(labels):
        a = first["bounds"]
        for second in labels[i + 1:]:
            b = second["bounds"]
            for axis, other, size, other_size in (("x", "y", "width", "height"), ("y", "x", "height", "width")):
                low = max(a[other], b[other])
                high = min(a[other] + a[other_size], b[other] + b[other_size])
                if high <= low:
                    continue
                if a[axis] + a[size] <= b[axis]:
                    left, right = first, second
                elif b[axis] + b[size] <= a[axis]:
                    left, right = second, first
                else:
                    continue
                distance = right["bounds"][axis] - left["bounds"][axis] - left["bounds"][size]
                gap = {"from_node_id": left["node_id"], "to_node_id": right["node_id"],
                       "axis": axis, "distance": distance, "overlap_span": {"start": low, "end": high}}
                for key in ((left["node_id"], axis, "+"), (right["node_id"], axis, "-")):
                    if key not in nearest or distance < nearest[key]["distance"]:
                        nearest[key] = gap
    unique = {(g["from_node_id"], g["to_node_id"], g["axis"]): g for g in nearest.values()}
    return [unique[key] for key in sorted(unique)]


def render_region(
    image_bytes: bytes,
    canvas: dict,
    nodes: list,
    region: dict | None = None,
    max_edge: int = 1400,
    annotate: bool = True,
) -> dict:
    """Return a PNG crop with a reversible design-coordinate mapping.

    ``scale`` maps design units to returned image pixels (independently on each
    axis). Labels refer to source IDs and keep original, unclipped bounds;
    ``image_bounds`` is clipped to the crop. Hidden/unpositioned nodes are skipped.
    Measurements are geometry only and make no assertion about component intent.
    """
    if isinstance(max_edge, bool) or not isinstance(max_edge, int) or not 1 <= max_edge <= MAX_OUTPUT_EDGE:
        raise ValueError("max_edge must be an integer between 1 and 4096")
    if not isinstance(annotate, bool):
        raise ValueError("annotate must be a boolean")
    if not isinstance(nodes, list) or len(nodes) > MAX_ANNOTATED_NODES:
        raise ValueError("nodes must be a list with at most 500 selected nodes")
    canvas_bounds = _rect(canvas, "canvas")
    wanted = _rect(region, "region") if region is not None else canvas_bounds
    source_region = _intersection(canvas_bounds, wanted)
    if source_region is None:
        raise ValueError("region does not intersect the design canvas")
    image = _open_raster(image_bytes)
    sx, sy = image.width / canvas_bounds["width"], image.height / canvas_bounds["height"]
    native_w, native_h = source_region["width"] * sx, source_region["height"] * sy
    reduction = min(1.0, max_edge / max(native_w, native_h))
    width, height = max(1, round(native_w * reduction)), max(1, round(native_h * reduction))
    left = (source_region["x"] - canvas_bounds["x"]) * sx
    top = (source_region["y"] - canvas_bounds["y"]) * sy
    rendered = image.convert("RGBA").transform(
        (width, height), Image.Transform.EXTENT,
        (left, top, left + native_w, top + native_h), Image.Resampling.BICUBIC,
    )
    scale = {"x": width / source_region["width"], "y": height / source_region["height"]}
    labels, gaps = [], []
    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise ValueError("Each node must be an object")
        if node.get("source_visible") is False:
            continue
        if node.get("bounds") is None:
            gaps.append({"node_id": node.get("node_id"), "reason": "missing_bounds"})
            continue
        node_id = node.get("node_id")
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("Each positioned node requires a nonempty node_id string")
        try:
            source_bounds = node["bounds"]
            if not isinstance(source_bounds, dict):
                raise ValueError("Node bounds must be an object")
            bounds = {
                "x": _number(source_bounds.get("x", 0), "node.bounds.x"),
                "y": _number(source_bounds.get("y", 0), "node.bounds.y"),
                "width": _number(source_bounds.get("width"), "node.bounds.width"),
                "height": _number(source_bounds.get("height"), "node.bounds.height"),
            }
        except ValueError:
            gaps.append({"node_id": node_id, "reason": "invalid_bounds"})
            continue
        if bounds["width"] <= 0 or bounds["height"] <= 0:
            gaps.append({"node_id": node_id, "reason": "degenerate_bounds"})
            continue
        clipped = _intersection(bounds, source_region)
        if clipped is None:
            continue
        order = node.get("source_order", i)
        if isinstance(order, bool) or not isinstance(order, int) or order < 0:
            raise ValueError("node.source_order must be a nonnegative integer")
        labels.append({
            "label": f"N{order + 1}", "node_id": node_id, "bounds": bounds,
            "image_bounds": {"x": (clipped["x"] - source_region["x"]) * scale["x"],
                             "y": (clipped["y"] - source_region["y"]) * scale["y"],
                             "width": clipped["width"] * scale["x"],
                             "height": clipped["height"] * scale["y"]},
        })
    if len({label["node_id"] for label in labels}) != len(labels):
        raise ValueError("Selected node IDs must be unique")
    if len({label["label"] for label in labels}) != len(labels):
        raise ValueError("Selected node source_order values must be unique")
    if annotate:
        draw = ImageDraw.Draw(rendered)
        for label in labels:
            b = label["image_bounds"]
            x, y = b["x"], b["y"]
            draw.rectangle((x, y, x + b["width"], y + b["height"]), outline="#E22955", width=2)
            text_box = draw.textbbox((0, 0), label["label"])
            label_w, label_h = text_box[2] + 6, text_box[3] + 4
            tx, ty = min(max(0, x), max(0, width - label_w)), min(max(0, y), max(0, height - label_h))
            draw.rectangle((tx, ty, tx + label_w, ty + label_h), fill="#E22955")
            draw.text((tx + 3, ty + 1), label["label"], fill="white")
    stream = io.BytesIO()
    rendered.save(stream, format="PNG")
    return {"image_bytes": stream.getvalue(), "source_region": source_region,
            "image_size": {"width": width, "height": height}, "scale": scale,
            "labels": labels, "gaps": gaps, "measurements": _geometric_gaps(labels), "annotated": annotate}


def _svg_metadata(data: bytes) -> dict:
    # ElementTree does not fetch external entities; reject DTDs and active content
    # as exported SVGs will later be consumed by a browser, not just this parser.
    if re.search(br"<!\s*(?:DOCTYPE|ENTITY)|<\?xml-stylesheet", data, re.I):
        raise _AssetError("unsafe_svg", "SVG DTDs, entities, and external stylesheets are unsupported")
    try:
        root = ET.fromstring(data)
    except (ET.ParseError, ValueError):
        raise _AssetError("invalid_svg", "SVG XML could not be parsed") from None
    if root.tag not in ("svg", "{http://www.w3.org/2000/svg}svg"):
        raise _AssetError("invalid_image", "Content is not an SVG image")
    for element in root.iter():
        local = element.tag.rsplit("}", 1)[-1].lower()
        if local in {"script", "foreignobject", "iframe", "object", "embed", "audio", "video",
                     "animate", "animatemotion", "animatetransform", "set"}:
            raise _AssetError("unsafe_svg", "SVG contains unsupported active elements")
        for attr, value in element.attrib.items():
            local_attr = attr.rsplit("}", 1)[-1].lower()
            if local_attr.startswith("on") or local_attr in {"base", "src"}:
                raise _AssetError("unsafe_svg", "SVG contains active or external references")
            if local_attr == "href" and not value.strip().startswith("#"):
                raise _AssetError("unsafe_svg", "SVG external references are unsupported")
        css = " ".join(element.attrib.values()) + " " + (element.text or "")
        if "\\" in css or re.search(r"@import|expression\s*\(|javascript\s*:", css, re.I):
            raise _AssetError("unsafe_svg", "SVG contains active or external styles")
        for match in re.finditer(r"url\s*\((.*?)\)", css, re.I | re.S):
            if not match.group(1).strip().strip("\"'").startswith("#"):
                raise _AssetError("unsafe_svg", "SVG external paint references are unsupported")
    def length(value: str | None) -> float | None:
        match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)(?:px)?\s*", value or "")
        if not match:
            return None
        number = float(match.group(1))
        return number if math.isfinite(number) and number > 0 else None
    width, height = length(root.get("width")), length(root.get("height"))
    if width is None or height is None:
        viewbox = re.split(r"[\s,]+", root.get("viewBox", "").strip())
        try:
            values = [float(v) for v in viewbox]
            if len(values) == 4 and all(math.isfinite(v) for v in values) and values[2] > 0 and values[3] > 0:
                width, height = width or values[2], height or values[3]
        except ValueError:
            pass
    return {"format": "svg", "actual_pixel_size": None, "intrinsic_size": {"width": width, "height": height},
            "is_vector": True, "has_alpha": None, "content_bbox": None}


def _inspect_asset(data: bytes) -> dict:
    if not isinstance(data, bytes) or not data or len(data) > MAX_FILE_BYTES:
        raise _AssetError("invalid_bytes", "Asset is empty or exceeds the 64 MiB file limit")
    header = data.lstrip()[:1024].lower()
    if header.startswith((b"<!doctype html", b"<html")):
        raise _AssetError("invalid_image", "Server returned an HTML page instead of an image")
    if header.startswith((b"<?xml", b"<svg", b"<!--", b"\xef\xbb\xbf")):
        metadata = _svg_metadata(data)
    else:
        image = _open_raster(data)
        extension = _RASTER_EXTENSIONS.get(image.format)
        if extension is None:
            raise _AssetError("unsupported_format", "Decoded image format is unsupported for export")
        has_alpha = "A" in image.getbands() or "transparency" in image.info
        alpha = image.convert("RGBA").getchannel("A")
        box = alpha.getbbox()
        metadata = {"format": extension, "is_vector": False,
                    "actual_pixel_size": {"width": image.width, "height": image.height},
                    "has_alpha": has_alpha, "has_transparency": alpha.getextrema()[0] < 255,
                    "content_bbox": None if box is None else {"x": box[0], "y": box[1], "width": box[2] - box[0], "height": box[3] - box[1]},
                    "frame_count": getattr(image, "n_frames", 1)}
    return {**metadata, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def _atomic_write(path: Path, data: bytes) -> None:
    fd, name = tempfile.mkstemp(prefix=".lanhu-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _density(metadata: dict, bounds: Any, target_dpr: float) -> dict:
    if metadata["is_vector"]:
        return {"effective_density": None, "resolution_limited": False}
    try:
        rect = _rect(bounds, "asset.render_bounds")
    except ValueError:
        return {"effective_density": None, "resolution_limited": None}
    pixels = metadata["actual_pixel_size"]
    density = {"x": pixels["width"] / rect["width"], "y": pixels["height"] / rect["height"]}
    return {"effective_density": density, "resolution_limited": min(density.values()) + 1e-6 < target_dpr}


async def download_assets(
    assets: list,
    output_dir: Path,
    *,
    fetch: Callable[[str], Awaitable[bytes]],
    target_dpr: float = 2,
    concurrency: int = 4,
) -> dict:
    """Download original bytes and atomically publish a verifiable local manifest.

    ``fetch`` owns HTTP/auth/redirect policy. No URL, exception text, or supplied
    name is persisted. Asset IDs must identify the version and resource variant.
    A corrupt response is retried twice; individual failures cannot be complete.
    """
    if not isinstance(assets, list) or len(assets) > 2000:
        raise ValueError("assets must be a list containing at most 2000 items")
    target_dpr = _number(target_dpr, "target_dpr", positive=True)
    if isinstance(concurrency, bool) or not isinstance(concurrency, int) or not 1 <= concurrency <= 16:
        raise ValueError("concurrency must be an integer between 1 and 16")
    ids = []
    for asset in assets:
        if not isinstance(asset, dict) or not isinstance(asset.get("asset_id"), str) or not asset["asset_id"]:
            raise ValueError("Each asset must have a nonempty asset_id string")
        ids.append(asset["asset_id"])
    if len(set(ids)) != len(ids):
        raise ValueError("asset_id values must be unique, including resource variants")
    output_dir = Path(output_dir)
    asset_dir = output_dir / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = asset_dir / "manifest.json"
    old_entries = {}
    try:
        manifest = json.loads(manifest_path.read_text("utf-8"))
        if manifest.get("schema_version") == 1 and isinstance(manifest.get("assets"), list):
            old_entries = {item["asset_id"]: item for item in manifest["assets"]
                           if isinstance(item, dict) and isinstance(item.get("asset_id"), str)}
    except (OSError, ValueError, AttributeError, TypeError):
        pass
    semaphore = asyncio.Semaphore(concurrency)

    async def one(asset: dict) -> tuple[bool, dict]:
        async with semaphore:
            asset_id = asset["asset_id"]
            digest = hashlib.sha256(asset_id.encode("utf-8")).hexdigest()
            base = {"asset_id": asset_id, "node_id": asset.get("node_id"), "kind": asset.get("kind")}
            metadata, cached = None, False
            previous = old_entries.get(asset_id)
            if previous:
                extension = previous.get("format")
                expected = f"assets/{digest}.{extension}"
                if extension in {*_RASTER_EXTENSIONS.values(), "svg"} and previous.get("relative_path") == expected:
                    try:
                        local = output_dir / expected
                        if local.stat().st_size <= MAX_FILE_BYTES:
                            inspected = await asyncio.to_thread(_inspect_asset, local.read_bytes())
                            if (inspected["sha256"] == previous.get("sha256")
                                    and inspected["actual_pixel_size"] == previous.get("actual_pixel_size")
                                    and inspected["format"] == extension):
                                metadata, cached = inspected, True
                    except (OSError, ValueError):
                        pass
            last_error = _AssetError("download_failed", "Asset download failed")
            if metadata is None:
                url = asset.get("url")
                if not isinstance(url, str) or not url:
                    return False, {**base, "error": "missing_url", "reason": "Asset has no download URL"}
                for attempt in range(3):
                    try:
                        data = await fetch(url)
                        inspected = await asyncio.to_thread(_inspect_asset, data)
                        relative_path = f"assets/{digest}.{inspected['format']}"
                        await asyncio.to_thread(_atomic_write, output_dir / relative_path, data)
                        metadata = inspected
                        break
                    except _AssetError as exc:
                        last_error = exc
                    except Exception:
                        last_error = _AssetError("download_failed", "Download or local file write failed")
                    if attempt < 2:
                        await asyncio.sleep(0.1 * (attempt + 1))
            if metadata is None:
                return False, {**base, "error": last_error.code, "reason": str(last_error)}
            return True, {**base, **metadata, "relative_path": f"assets/{digest}.{metadata['format']}",
                          **_density(metadata, asset.get("render_bounds"), target_dpr),
                          "target_dpr": target_dpr, "cached": cached}

    results = await asyncio.gather(*(one(asset) for asset in assets))
    successful = [result for ok, result in results if ok]
    failed = [result for ok, result in results if not ok]
    status = "complete" if not failed else "partial" if successful else "failed"
    counts = {"requested": len(assets), "succeeded": len(successful), "failed": len(failed),
              "cached": sum(result["cached"] for result in successful)}
    # A manifest describes this requested package; a failure removes any stale
    # record for the same request rather than making old bytes look successful.
    manifest = {"schema_version": 1, "status": status, "assets": successful, "failed": failed, "counts": counts}
    await asyncio.to_thread(_atomic_write, manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))
    return {"status": status, "assets": successful, "failed": failed, "counts": counts,
            "manifest_path": "assets/manifest.json"}
