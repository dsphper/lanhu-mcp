"""Asset delivery must use real decoded evidence, not names or file suffixes."""

import asyncio
import hashlib
import io
import json
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lanhu_design.media import download_assets, render_region


def png(size=(80, 40), *, transparent=False):
    image = Image.new("RGBA", size, (0, 0, 0, 0) if transparent else (40, 70, 90, 255))
    if transparent:
        ImageDraw.Draw(image).rectangle((10, 5, 69, 34), fill=(10, 20, 30, 255))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def asset(asset_id="node:version:png", **updates):
    value = {"asset_id": asset_id, "node_id": "node:1", "name": "编组 2/../same name",
             "kind": "explicit", "url": "https://example.test/original.jpg?token=secret",
             "format_hint": "jpg", "render_bounds": {"x": 7, "y": 9, "width": 40, "height": 20}}
    return {**value, **updates}


def node(node_id="n1", x=10, y=5, width=20, height=10, order=8):
    return {"node_id": node_id, "name": "编组123", "bounds": {"x": x, "y": y, "width": width, "height": height},
            "source_order": order, "source_visible": True}


def test_region_maps_design_units_to_crop_pixels_and_clamps():
    result = render_region(png((800, 400)), {"width": 400, "height": 200},
                           [node(x=20, y=40, width=60, height=30)],
                           {"x": -20, "y": 20, "width": 120, "height": 100}, max_edge=100)
    assert result["source_region"] == {"x": 0, "y": 20, "width": 100, "height": 100}
    assert result["image_size"] == {"width": 100, "height": 100}
    assert result["scale"] == {"x": 1, "y": 1}
    assert result["labels"][0]["label"] == "N9"
    assert result["labels"][0]["image_bounds"] == {"x": 20, "y": 20, "width": 60, "height": 30}
    assert Image.open(io.BytesIO(result["image_bytes"])).size == (100, 100)


def test_region_pixels_and_mapping_respect_nonzero_canvas_origin():
    source = Image.new("RGB", (200, 100), "red")
    ImageDraw.Draw(source).rectangle((100, 0, 199, 99), fill="blue")
    buffer = io.BytesIO()
    source.save(buffer, "PNG")
    result = render_region(buffer.getvalue(), {"x": 50, "y": 100, "width": 100, "height": 50},
                           [node(x=100, y=100, width=20, height=20)],
                           {"x": 100, "y": 100, "width": 50, "height": 50}, annotate=False)
    assert result["scale"] == {"x": 2, "y": 2}
    assert result["labels"][0]["image_bounds"]["x"] == 0
    image = Image.open(io.BytesIO(result["image_bytes"]))
    assert image.getpixel((30, 30)) == (0, 0, 255, 255)
    assert Image.open(io.BytesIO(buffer.getvalue())).getpixel((30, 30)) == (255, 0, 0)


def test_labels_are_source_order_stable_and_measurements_are_geometry_only():
    a, b = node("left", x=0, y=0, width=10, height=10, order=99), node("right", x=25, y=0, width=10, height=10, order=1)
    forward = render_region(png(), {"width": 80, "height": 40}, [a, b])
    backward = render_region(png(), {"width": 80, "height": 40}, [b, a])
    assert {v["node_id"]: v["label"] for v in forward["labels"]} == {"left": "N100", "right": "N2"}
    assert {v["node_id"]: v["label"] for v in backward["labels"]} == {"left": "N100", "right": "N2"}
    assert forward["measurements"] == [{"from_node_id": "left", "to_node_id": "right", "axis": "x", "distance": 15,
                                         "overlap_span": {"start": 0, "end": 10}}]
    assert forward["gaps"] == []


def test_missing_hidden_and_outside_nodes_do_not_get_invented_positions():
    result = render_region(png(), {"width": 80, "height": 40},
                           [{**node(), "bounds": None}, {**node("hidden"), "source_visible": False}, node("outside", x=100)])
    assert result["labels"] == []
    assert result["gaps"] == [{"node_id": "n1", "reason": "missing_bounds"}]


def test_degenerate_or_invalid_node_bounds_do_not_break_valid_visual_evidence():
    nodes = [
        node("good", order=0),
        node("horizontal-line", height=0, order=1),
        node("vertical-line", width=0, order=2),
        node("negative-width", width=-10, order=3),
        {**node("unpositioned", order=4), "bounds": None},
        node("invalid-number", x=float("nan"), order=5),
        {**node("invalid-object", order=6), "bounds": "unknown"},
        node("invalid-type", width="20", order=7),
    ]
    result = render_region(png(), {"width": 80, "height": 40}, nodes)
    assert [label["node_id"] for label in result["labels"]] == ["good"]
    assert result["gaps"] == [
        {"node_id": "horizontal-line", "reason": "degenerate_bounds"},
        {"node_id": "vertical-line", "reason": "degenerate_bounds"},
        {"node_id": "negative-width", "reason": "degenerate_bounds"},
        {"node_id": "unpositioned", "reason": "missing_bounds"},
        {"node_id": "invalid-number", "reason": "invalid_bounds"},
        {"node_id": "invalid-object", "reason": "invalid_bounds"},
        {"node_id": "invalid-type", "reason": "invalid_bounds"},
    ]
    assert Image.open(io.BytesIO(result["image_bytes"])).size == (80, 40)


@pytest.mark.parametrize("kwargs, message", [
    ({"max_edge": 4097}, "max_edge"), ({"max_edge": True}, "max_edge"),
    ({"region": {"x": 100, "y": 0, "width": 10, "height": 10}}, "does not intersect"),
    ({"region": {"x": 0, "y": 0, "width": float("nan"), "height": 10}}, "finite"),
    ({"region": {"x": 0, "y": 0, "width": 0, "height": 10}}, "positive"),
])
def test_invalid_crop_arguments_are_clear(kwargs, message):
    with pytest.raises(ValueError, match=message):
        render_region(png(), {"width": 80, "height": 40}, [], **kwargs)


def test_download_preserves_original_bytes_checks_alpha_and_ignores_names(tmp_path):
    original = png(transparent=True)
    async def fetch(url):
        return original
    result = asyncio.run(download_assets([asset("../a"), asset("../b", node_id="node:2")], tmp_path, fetch=fetch))
    assert result["status"] == "complete"
    assert result["counts"] == {"requested": 2, "succeeded": 2, "failed": 0, "cached": 0}
    first, second = result["assets"]
    assert first["relative_path"] != second["relative_path"]
    assert first["relative_path"].endswith(".png")
    assert (tmp_path / first["relative_path"]).read_bytes() == original
    assert first["actual_pixel_size"] == {"width": 80, "height": 40}
    assert first["effective_density"] == {"x": 2, "y": 2}
    assert first["resolution_limited"] is False
    assert first["has_alpha"] is True and first["has_transparency"] is True
    assert first["content_bbox"] == {"x": 10, "y": 5, "width": 60, "height": 30}
    assert first["sha256"] == hashlib.sha256(original).hexdigest()
    assert first["bytes"] == len(original)
    manifest = (tmp_path / "assets/manifest.json").read_text()
    assert "secret" not in manifest and "https://" not in manifest and "编组" not in manifest


def test_real_resolution_is_limited_even_with_misleading_format_hint(tmp_path):
    async def fetch(url):
        return png((40, 20))
    result = asyncio.run(download_assets([asset()], tmp_path, fetch=fetch))
    assert result["assets"][0]["resolution_limited"] is True
    assert result["assets"][0]["effective_density"] == {"x": 1, "y": 1}


def test_failures_are_partial_retried_and_do_not_leak_urls(tmp_path):
    calls = {}
    async def fetch(url):
        calls[url] = calls.get(url, 0) + 1
        if url == "ok":
            return png()
        if url == "html":
            return b"<!doctype html><html>Login expired</html>"
        if url == "damaged":
            return png()[:25]
        raise RuntimeError("Fetch failed https://example.test/?secret=private-token")
    assets = [asset(key, url=key) for key in ("ok", "html", "damaged", "network")]
    result = asyncio.run(download_assets(assets, tmp_path, fetch=fetch))
    assert result["status"] == "partial"
    assert result["counts"]["failed"] == 3
    assert calls == {"ok": 1, "html": 3, "damaged": 3, "network": 3}
    assert "private-token" not in json.dumps(result)
    manifest = json.loads((tmp_path / "assets/manifest.json").read_text())
    assert len(manifest["assets"]) == 1


def test_all_bad_assets_are_failed(tmp_path):
    async def fetch(url):
        return b"not an image"
    result = asyncio.run(download_assets([asset()], tmp_path, fetch=fetch))
    assert result["status"] == "failed"
    assert result["assets"] == []


def test_cache_requires_matching_hash_and_decoded_dimensions(tmp_path):
    calls = 0
    async def fetch(url):
        nonlocal calls
        calls += 1
        return png()
    first = asyncio.run(download_assets([asset()], tmp_path, fetch=fetch))
    second = asyncio.run(download_assets([asset()], tmp_path, fetch=fetch, target_dpr=3))
    assert second["assets"][0]["cached"] is True and calls == 1
    assert second["assets"][0]["resolution_limited"] is True
    (tmp_path / first["assets"][0]["relative_path"]).write_bytes(png((10, 10)))
    third = asyncio.run(download_assets([asset()], tmp_path, fetch=fetch))
    assert third["assets"][0]["cached"] is False and calls == 2
    assert third["assets"][0]["actual_pixel_size"] == {"width": 80, "height": 40}


def test_cache_metadata_dimension_tampering_forces_redownload(tmp_path):
    calls = 0
    async def fetch(url):
        nonlocal calls
        calls += 1
        return png()
    asyncio.run(download_assets([asset()], tmp_path, fetch=fetch))
    path = tmp_path / "assets/manifest.json"
    manifest = json.loads(path.read_text())
    manifest["assets"][0]["actual_pixel_size"]["width"] = 999
    path.write_text(json.dumps(manifest))
    result = asyncio.run(download_assets([asset()], tmp_path, fetch=fetch))
    assert calls == 2 and result["assets"][0]["cached"] is False


def test_svg_is_vector_without_fictional_pixel_density(tmp_path):
    data = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 20"><rect width="32" height="20" fill="red"/></svg>'
    async def fetch(url):
        return data
    result = asyncio.run(download_assets([asset()], tmp_path, fetch=fetch))
    item = result["assets"][0]
    assert item["format"] == "svg" and item["is_vector"] is True
    assert item["actual_pixel_size"] is None and item["effective_density"] is None
    assert item["intrinsic_size"] == {"width": 32, "height": 20}
    assert item["resolution_limited"] is False


@pytest.mark.parametrize("data", [
    b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
    b'<svg xmlns="http://www.w3.org/2000/svg"><image href="https://private.test/a"/></svg>',
    b'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY x "test">]><svg>&x;</svg>',
    b'<svg xmlns="http://www.w3.org/2000/svg"><style>@import "https://private.test/a";</style></svg>',
    b'<?xml-stylesheet href="https://private.test/style.css"?><svg xmlns="http://www.w3.org/2000/svg"/>',
    b'<svg xmlns="http://www.w3.org/2000/svg"><set attributeName="href" to="https://private.test/a"/></svg>',
    b'<svg xmlns="http://www.w3.org/2000/svg"><style>rect {fill:u\\72l(https://private.test/a)}</style></svg>',
])
def test_svg_active_and_external_content_is_rejected(tmp_path, data):
    async def fetch(url):
        return data
    result = asyncio.run(download_assets([asset()], tmp_path, fetch=fetch))
    assert result["status"] == "failed"
    assert result["failed"][0]["error"] == "unsafe_svg"


def test_download_concurrency_is_bounded(tmp_path):
    active = 0
    peak = 0
    async def fetch(url):
        nonlocal active, peak
        active += 1
        peak = max(active, peak)
        await asyncio.sleep(0.01)
        active -= 1
        return png()
    result = asyncio.run(download_assets([asset(str(i)) for i in range(7)], tmp_path, fetch=fetch, concurrency=2))
    assert result["status"] == "complete" and peak == 2


def test_duplicate_asset_ids_are_explicit_error(tmp_path):
    async def fetch(url):
        pytest.fail("Invalid request must be rejected before fetch")
    with pytest.raises(ValueError, match="unique"):
        asyncio.run(download_assets([asset(), asset()], tmp_path, fetch=fetch))
