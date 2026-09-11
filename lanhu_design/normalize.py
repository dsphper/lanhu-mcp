"""Normalize Lanhu source data without deriving meaning from layer names.

Coordinates remain in the source canvas units. Export density is metadata, not a
coordinate conversion instruction. The output describes evidence; it does not
claim that an exported group should replace its children in an implementation.
"""

from __future__ import annotations

import copy
import hashlib
import math
from collections import Counter, defaultdict
from urllib.parse import quote, urlsplit


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if math.isfinite(value) else None


def _first_number(mapping, *keys):
    for key in keys:
        value = _number(mapping.get(key))
        if value is not None:
            return value
    return None


def _rect(value):
    """Only accept complete source rectangles, never manufacture missing zeroes."""
    if not isinstance(value, dict):
        return None
    x = _first_number(value, "x", "left")
    y = _first_number(value, "y", "top")
    width = _first_number(value, "width")
    height = _first_number(value, "height")
    right, bottom = _number(value.get("right")), _number(value.get("bottom"))
    if width is None and right is not None and x is not None:
        width = right - x
    if height is None and bottom is not None and y is not None:
        height = bottom - y
    if None in (x, y, width, height) or width < 0 or height < 0:
        return None
    return {"x": x, "y": y, "width": width, "height": height}


def _bounds(layer, source_type):
    fields = ("frame", "realFrame", "absoluteBoundingBox", "bounds", "")
    if source_type != "figma":
        fields = ("", "frame", "bounds", "layerOriginFrame", "realFrame", "absoluteBoundingBox")
    for field in fields:
        bounds = _rect(layer.get(field) if field else layer)
        if bounds is not None:
            return bounds, field or "left/top/width/height"
    return None, None


def _source_id(layer):
    for key in ("id", "objectID", "do_objectID"):
        value = layer.get(key)
        if isinstance(value, (str, int)) and not isinstance(value, bool) and str(value):
            return str(value)
    return None


def _flag(value):
    # Avoid truthy strings such as "false" accidentally turning previews into exports.
    return value is True or (isinstance(value, (int, float)) and not isinstance(value, bool) and value == 1)


def _visibility(layer):
    for key in ("isVisible", "visible"):
        value = layer.get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value)
    if isinstance(layer.get("hidden"), bool):
        return not layer["hidden"]
    return None


def _text(layer):
    value = layer.get("text")
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for field in ("value", "characters", "content", "text"):
            if isinstance(value.get(field), str):
                return value[field]
    for field in ("characters", "textContent"):
        if isinstance(layer.get(field), str):
            return layer[field]
    font = layer.get("font")
    if isinstance(font, dict) and isinstance(font.get("content"), str):
        return font["content"]
    return None


def _url(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    return value if parsed.scheme.lower() in ("http", "https") and parsed.netloc else None


def _format_hint(url, field):
    field_lower = field.lower()
    for fmt in ("svg", "png", "webp", "jpeg", "jpg", "gif", "avif"):
        if fmt in field_lower or urlsplit(url).path.lower().endswith("." + fmt):
            return "jpeg" if fmt == "jpg" else fmt
    # imageUrl commonly uses extensionless object URLs; downloading must inspect bytes.
    return None


def _variants(image, prefix):
    if isinstance(image, str):
        url = _url(image)
        return [{"url": url, "format_hint": _format_hint(url, prefix), "source_field": prefix}] if url else []
    if not isinstance(image, dict):
        return []
    ordered_keys = ["imageUrl", "png_xxxhd", "png", "url", "svgUrl", "svg"]
    ordered_keys += sorted(key for key in image if key not in ordered_keys)
    result = []
    seen = set()
    for key in ordered_keys:
        url = _url(image.get(key))
        if url and url not in seen:
            result.append({"url": url, "format_hint": _format_hint(url, key), "source_field": f"{prefix}.{key}"})
            seen.add(url)
    return result


def normalize_design(raw: dict) -> dict:
    """Return source nodes and asset references for Sketch, Figma, or Photoshop.

    ``nodes`` includes the canvas when it exists in the source. ``parent_id`` is
    navigable and acyclic; original, ambiguous, missing, or cyclic parent links
    remain available as ``source_parent_id`` and in ``gaps``. Asset variants are
    grouped by source field so one PNG/SVG export counts as one exported asset.
    """
    if not isinstance(raw, dict):
        raise TypeError("Lanhu design data must be a dictionary")
    meta = raw.get("meta") if isinstance(raw.get("meta"), dict) else {}
    host = meta.get("host") if isinstance(meta.get("host"), dict) else {}
    if str(raw.get("type", "")).lower() in ("ps", "photoshop"):
        source_type = "photoshop"
    elif str(host.get("name", "")).lower() == "figma" or isinstance(raw.get("artboard"), dict):
        source_type = "figma"
    elif isinstance(raw.get("info"), list):
        source_type = "sketch"
    elif isinstance(raw.get("board"), dict):
        source_type = "photoshop"
    else:
        source_type = "unknown"

    gaps = []
    records = []

    def gap(code, **evidence):
        gaps.append({"code": code, **evidence})

    def walk(layer, pointer, parent_pointer=None):
        if not isinstance(layer, dict):
            gap("invalid_layer", source_pointer=pointer)
            return
        records.append({"raw": layer, "pointer": pointer, "parent_pointer": parent_pointer})
        for field in ("layers", "children"):
            children = layer.get(field)
            if isinstance(children, list):
                for index, child in enumerate(children):
                    walk(child, f"{pointer}/{field}/{index}", pointer)

    canvas_layer = None
    if source_type == "figma" and isinstance(raw.get("artboard"), dict):
        canvas_layer = raw["artboard"]
        walk(canvas_layer, "/artboard")
    elif source_type == "photoshop" and isinstance(raw.get("board"), dict):
        canvas_layer = raw["board"]
        walk(canvas_layer, "/board")
    elif isinstance(raw.get("info"), list):
        for index, layer in enumerate(raw["info"]):
            walk(layer, f"/info/{index}")
        artboard_id = raw.get("ArtboardID")
        for record in records:
            layer = record["raw"]
            if artboard_id is not None and _source_id(layer) == str(artboard_id):
                canvas_layer = layer
                break
        if canvas_layer is None:
            candidates = [r["raw"] for r in records if
                          (r["raw"].get("ddsType") or r["raw"].get("type")) in
                          ("artboard-group", "artboard", "artboardSection")]
            if len(candidates) == 1:
                canvas_layer = candidates[0]
    else:
        gap("unsupported_source_structure")

    width = height = None
    canvas_origin = None
    if canvas_layer is not None:
        canvas_bounds, _ = _bounds(canvas_layer, source_type)
        if canvas_bounds:
            width, height = canvas_bounds["width"], canvas_bounds["height"]
            canvas_origin = {"x": canvas_bounds["x"], "y": canvas_bounds["y"]}
            if canvas_origin["x"] != 0 or canvas_origin["y"] != 0:
                gap("nonzero_canvas_origin_unverified", canvas_origin=canvas_origin.copy(),
                    message="Nonzero source canvas origin requires verified image mapping; no translation was applied.")
        else:
            for value in (canvas_layer.get("frame"), canvas_layer.get("realFrame"), canvas_layer):
                if isinstance(value, dict):
                    w, h = _number(value.get("width")), _number(value.get("height"))
                    if w is not None and h is not None and w >= 0 and h >= 0:
                        width, height = w, h
                        break
    if width is None or height is None:
        gap("missing_canvas_dimensions")

    source_ids = Counter(_source_id(r["raw"]) for r in records if _source_id(r["raw"]) is not None)
    ids_by_pointer = {}
    unique_source_ids = {}
    allocated_ids = set()
    nodes = []
    raw_by_node = {}
    for order, record in enumerate(records):
        layer, pointer = record["raw"], record["pointer"]
        sid = _source_id(layer)
        digest = hashlib.sha256(pointer.encode()).hexdigest()[:16]
        identity_source = "source_id"
        if sid is None:
            node_id = f"source-path:{digest}"
            identity_source = "source_pointer"
        elif source_ids[sid] > 1:
            node_id = f"{sid}:source-path:{digest}"
            identity_source = "duplicate_source_id_and_pointer"
        else:
            node_id = sid
            unique_source_ids[sid] = node_id
        if identity_source != "source_id":
            # Source IDs win even when one happens to look like our fallback ID.
            while node_id in source_ids or node_id in allocated_ids:
                node_id += ":generated"
        allocated_ids.add(node_id)
        if sid is None:
            gap("missing_node_id", node_id=node_id, source_pointer=pointer)
        elif source_ids[sid] > 1:
            gap("duplicate_node_id", node_id=node_id, source_id=sid, source_pointer=pointer)
        ids_by_pointer[pointer] = node_id
        bounds, bounds_field = _bounds(layer, source_type)
        if bounds is None:
            gap("missing_node_bounds", node_id=node_id, source_pointer=pointer)
        structural = {"id", "objectID", "do_objectID", "name", "type", "ddsType", "layerType", "layers",
                      "children", "parentID", "parentId", "parent_id", "image", "ddsImage", "images"}
        node = {
            "node_id": node_id,
            "source_id": sid,
            "identity_source": identity_source,
            "parent_id": None,
            "source_parent_id": None,
            "source_order": order,
            "name": layer.get("name") if isinstance(layer.get("name"), str) else "",
            "node_type": layer.get("type") or layer.get("ddsType") or layer.get("layerType") or "unknown",
            "bounds": bounds,
            "bounds_source_field": bounds_field,
            "source_visible": _visibility(layer),
            "text": _text(layer),
            "raw_style": copy.deepcopy({key: value for key, value in layer.items() if key not in structural}),
            "asset_ids": [],
            "source_pointer": pointer,
        }
        if layer.get("transform") is not None or layer.get("relativeTransform") is not None:
            gap("transform_preserved_not_applied", node_id=node_id,
                message="Source bounds are retained; transforms are not composed or applied again.")
        nodes.append(node)
        raw_by_node[node_id] = layer

    # Build parent links after indexing: legacy Sketch info[] is flat and children
    # often occur before their parents. No spatial or name heuristic is used.
    for record, node in zip(records, nodes):
        layer = record["raw"]
        explicit_parent = None
        for field in ("parentID", "parentId", "parent_id"):
            if layer.get(field) is not None:
                explicit_parent = str(layer[field])
                break
        nested_parent = ids_by_pointer.get(record["parent_pointer"])
        node["source_parent_id"] = explicit_parent if explicit_parent is not None else nested_parent
        if explicit_parent is not None:
            if explicit_parent in unique_source_ids:
                node["parent_id"] = unique_source_ids[explicit_parent]
                if nested_parent is not None and nested_parent != node["parent_id"]:
                    gap("conflicting_parent_sources", node_id=node["node_id"], nested_parent_id=nested_parent,
                        source_parent_id=explicit_parent)
            else:
                gap("ambiguous_parent_id" if explicit_parent in source_ids else "missing_parent_id",
                    node_id=node["node_id"], source_parent_id=explicit_parent)
        else:
            node["parent_id"] = nested_parent

    by_id = {node["node_id"]: node for node in nodes}
    visited = set()
    for node in nodes:
        chain = []
        positions = {}
        current = node["node_id"]
        while current is not None and current not in visited:
            if current in positions:
                cycle = chain[positions[current]:]
                for cycle_id in cycle:
                    by_id[cycle_id]["parent_id"] = None
                gap("parent_cycle", node_ids=cycle)
                break
            positions[current] = len(chain)
            chain.append(current)
            current = by_id[current]["parent_id"]
        visited.update(chain)

    ps_assets = defaultdict(list)
    for index, asset in enumerate(raw.get("assets") or []):
        if isinstance(asset, dict) and _source_id(asset) is not None:
            ps_assets[_source_id(asset)].append((index, asset))

    assets = []
    assets_by_id = {}

    def add_asset(node, layer, field, value, kind, source_evidence=None):
        variants = _variants(value, field)
        if not variants:
            if value:
                gap("asset_without_download_url", node_id=node["node_id"], source_field=field)
            return
        asset_id = f"{quote(node['node_id'], safe='')}:{field}"
        # ddsOriginFrame describes the render rectangle; image.point may use the
        # document origin and is deliberately not combined with canvas positions.
        render_bounds = _rect(layer.get("ddsOriginFrame")) if field == "ddsImage" else None
        render_bounds_source = "ddsOriginFrame" if render_bounds is not None else "node.bounds"
        render_bounds = render_bounds if render_bounds is not None else copy.deepcopy(node["bounds"])
        asset = {
            "asset_id": asset_id,
            "node_id": node["node_id"],
            "kind": kind,
            "url": variants[0]["url"],
            "format_hint": variants[0]["format_hint"],
            "render_bounds": render_bounds,
            "render_bounds_source_field": render_bounds_source if render_bounds is not None else None,
            "source_field": field,
            "source_pointer": f"{node['source_pointer']}/{field.replace('.', '/')}",
            "variants": variants,
            "source_size": copy.deepcopy(value.get("size")) if isinstance(value, dict) else None,
            "source_point": copy.deepcopy(value.get("point")) if isinstance(value, dict) else None,
            "pixel_dimensions": None,
            "pixel_dimensions_status": "requires_download",
        }
        if source_evidence:
            asset["source_evidence"] = source_evidence
        assets.append(asset)
        assets_by_id[asset_id] = asset
        node["asset_ids"].append(asset_id)

    for node in nodes:
        layer = raw_by_node[node["node_id"]]
        indexed = ps_assets.get(node["source_id"], []) if source_type == "photoshop" else []
        ps_exported = any(_flag(layer.get(key)) for key in ("isAsset", "isSlice")) or any(
            _flag(asset.get(key)) for _, asset in indexed for key in ("isAsset", "isSlice"))
        if layer.get("image"):
            exported = _flag(layer.get("hasExportImage")) if source_type == "figma" else _flag(layer.get("exportable"))
            if source_type == "photoshop":
                exported = ps_exported
            add_asset(node, layer, "image", layer["image"], "exported_asset" if exported else "render_fallback")
        if layer.get("ddsImage"):
            add_asset(node, layer, "ddsImage", layer["ddsImage"], "render_fallback")
        if source_type == "photoshop" and layer.get("images"):
            add_asset(node, layer, "images", layer["images"], "exported_asset" if ps_exported else "render_fallback",
                      source_evidence=[f"/assets/{index}" for index, _ in indexed])
        for field, fills in (("fills", layer.get("fills")),
                             ("style.fills", (layer.get("style") or {}).get("fills")
                              if isinstance(layer.get("style"), dict) else None)):
            if not isinstance(fills, list):
                continue
            for index, fill in enumerate(fills):
                if not isinstance(fill, dict):
                    continue
                # Explicit image-bearing fields only; color/gradient stops never become nodes.
                for image_field in ("image", "imageUrl", "imageURL"):
                    if fill.get(image_field):
                        prefix = f"{field}.{index}.{image_field}"
                        add_asset(node, layer, prefix, fill[image_field], "image_fill")
        if ((_flag(layer.get("exportable")) or _flag(layer.get("hasExportImage")) or
             ps_exported) and
                not any(assets_by_id[asset_id]["kind"] == "exported_asset" for asset_id in node["asset_ids"])):
            gap("export_marked_without_download_url", node_id=node["node_id"])

    if source_type == "photoshop":
        gap("photoshop_coordinates_unconverted",
            message="Board coordinates are retained as supplied; source asset bounds may use a document origin.")
        for sid, indexed in ps_assets.items():
            if sid not in unique_source_ids:
                gap("unresolved_asset_node", source_id=sid,
                    source_pointers=[f"/assets/{index}" for index, _ in indexed])
    scale_metadata = {key: copy.deepcopy(raw[key]) for key in ("device", "ArtboardScale", "sliceScale", "exportScale")
                      if key in raw}
    for key in ("device", "sliceScale", "exportScale"):
        if key in meta:
            scale_metadata[f"meta.{key}"] = copy.deepcopy(meta[key])
    gap("logical_coordinate_conversion_unknown",
        message="Source canvas units are preserved. Export density does not establish CSS pixel scale.")
    return {
        "schema_version": 1,
        "source_type": source_type,
        "coordinate_space": "source_canvas",
        "canvas": {"width": width, "height": height},
        "canvas_origin": canvas_origin,
        "scale_metadata": scale_metadata,
        "nodes": nodes,
        "assets": assets,
        "gaps": gaps,
    }
