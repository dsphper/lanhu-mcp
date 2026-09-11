"""End-to-end contracts: exact versions, visual IDs, MCP resources and client installation."""

import base64
import io
import json
from urllib.parse import parse_qs, urlsplit

import httpx
from PIL import Image
import pytest
from fastmcp import Client

from lanhu_design.install import install_bundle
from lanhu_design.service import DesignError, DesignService, parse_design_reference


URL = "https://lanhuapp.com/web/#/item/project/detailDetach?pid=project&tid=team&image_id=design"


def png(width=200, height=200):
    buffer = io.BytesIO()
    Image.new("RGBA", (width, height), (200, 100, 20, 255)).save(buffer, "PNG")
    return buffer.getvalue()


class FakeDesignService(DesignService):
    def __init__(self, root):
        super().__init__(root)
        self.calls = []
        self.latest = "v2"
        self.fail_asset = False
        self.fail_dds = False

    async def fetch_json(self, url):
        self.calls.append(url)
        if "/api/project/image?" in url:
            return {"code": "00000", "result": {
                "id": "design", "name": "任意名字", "type": "image", "latest_version": self.latest,
                "versions": [{"id": v, "json_url": f"https://source/{v}.json",
                              "url": f"https://source/{v}.png", "version_info": v} for v in ("v2", "v1")]}}
        if "/api/dds/" in url:
            if self.fail_dds:
                raise DesignError("Unavailable", "DDS absent")
            return {"code": "00000", "data": {"data_resource_url": "https://source/dds.json"}}
        if url.endswith("dds.json"):
            return {"layerId": "button", "props": {"style": {"display": "flex"}}, "children": []}
        return {"ArtboardID": "board", "sliceScale": 4, "info": [
            {"id": "board", "ddsType": "artboard-group", "left": 0, "top": 0, "width": 100, "height": 100},
            {"id": "button", "name": "编组123", "parentID": "board", "left": 10,
             "top": 20 if url.endswith("v1.json") else 40, "width": 40, "height": 30,
             "exportable": True, "image": {"imageUrl": "https://source/asset.png"}},
            {"id": "label", "name": "编组123", "parentID": "button", "left": 15, "top": 42,
             "width": 20, "height": 10, "font": {"content": "领取"}},
        ]}

    async def fetch_bytes(self, url):
        self.calls.append(url)
        if url.endswith("asset.png"):
            if self.fail_asset:
                return b"<html>not an image</html>"
            return png(80, 60)
        return png()


@pytest.mark.asyncio
async def test_exact_versions_and_snapshot_queries_never_switch_to_latest(tmp_path):
    service = FakeDesignService(tmp_path)
    old = await service.prepare(URL + "&versionId=v1")
    new = await service.prepare(URL, version_id="latest")
    assert old["resolved_version"] == "v1"
    assert new["resolved_version"] == "v2"
    assert old["snapshot_id"] != new["snapshot_id"]
    assert any("version_id=v1" in url for url in service.calls if "/api/dds/" in url)
    old_region = service.query(old["snapshot_id"], node_ids=["button"])
    new_region = service.query(new["snapshot_id"], node_ids=["button"])
    assert old_region["nodes"][0]["bounds"]["y"] == 20
    assert new_region["nodes"][0]["bounds"]["y"] == 40
    assert old_region["labels"][0]["node_id"] == "button"
    assert new_region["labels"][0]["label"] == old_region["labels"][0]["label"]
    assert old_region["ancestors"][0]["node_id"] == "board"
    assert old_region["dds_layout_suggestions"][0]["source"] == "dds_derived_layout"
    with pytest.raises(DesignError, match="does not belong"):
        await service.prepare(URL, version_id="missing")


@pytest.mark.asyncio
async def test_region_crop_pagination_validation_and_unknown_ids(tmp_path):
    service = FakeDesignService(tmp_path)
    snapshot = await service.prepare(URL)
    sid = snapshot["snapshot_id"]
    first = service.query(sid, region={"x": 0, "y": 0, "width": 60, "height": 80}, limit=1)
    assert first["total"] == 3 and first["truncated"] and first["next_offset"] == 1
    assert len(first["nodes"]) == 1
    second = service.query(sid, offset=1, limit=1)
    assert second["nodes"][0]["node_id"] == "button"
    assert second["assets"][0]["node_id"] == "button"
    assert "url" not in second["assets"][0]
    for invalid in ({"x": 0, "y": 0, "width": -1, "height": 10},
                    {"x": float("nan"), "y": 0, "width": 10, "height": 10}, {},
                    {"x": True, "y": 0, "width": 10, "height": 10}):
        with pytest.raises(DesignError):
            service.query(sid, region=invalid)
    with pytest.raises(DesignError):
        service.query(sid, node_ids=["not-here"])
    with pytest.raises(DesignError):
        service.artifact("../escape", "bundle", "a" * 32)


@pytest.mark.asyncio
async def test_dds_failure_is_explicit_and_does_not_mix_newer_layout(tmp_path):
    service = FakeDesignService(tmp_path)
    service.fail_dds = True
    prepared = await service.prepare(URL, version_id="v1")
    assert prepared["resolved_version"] == "v1"
    assert not prepared["capabilities"]["dds_layout"]
    assert any("DDS unavailable" in str(g) for g in prepared["gaps"])
    assert service.query(prepared["snapshot_id"], node_ids=["button"])["dds_layout_suggestions"] == []


@pytest.mark.asyncio
async def test_mcp_image_and_bundle_can_be_installed_on_a_separate_client_path(tmp_path, monkeypatch):
    import lanhu_mcp_server as server
    service = FakeDesignService(tmp_path / "server-cache")
    monkeypatch.setattr(server, "_design_service", service)
    async with Client(server.mcp) as client:
        overview = await client.call_tool("lanhu_get_design_overview", {"url": URL, "version_id": "v1"})
        metadata = json.loads(next(c.text for c in overview.content if c.type == "text"))
        assert any(c.type == "image" for c in overview.content)
        assert any(g.get("code") == "logical_coordinate_conversion_unknown" for g in metadata["gaps"])
        sid = metadata["snapshot_id"]
        region = await client.call_tool("lanhu_inspect_design_region", {"snapshot_id": sid, "node_ids": ["button"]})
        context = json.loads(next(c.text for c in region.content if c.type == "text"))
        assert context["image_order"] == ["clean_reference", "node_overlay"]
        assert len([c for c in region.content if c.type == "image"]) == 2
        assert context["nodes"][0]["bounds"]["y"] == 20
        result = await client.call_tool("lanhu_export_design_assets", {"snapshot_id": sid})
        manifest = result.data
        assert manifest["status"] == "complete"
        assert manifest["manifest_path"] == "manifest.json"
        assert manifest["assets"][0]["actual_pixel_size"] == {"width": 80, "height": 60}
        resource = await client.read_resource(manifest["bundle_resource"])
        payload = b"".join(base64.b64decode(item.blob) for item in resource)
        installed = install_bundle(payload, tmp_path / "client-project")
        assert len(installed["installed"]) == 1
        assert installed["resolved_version"] == "v1"
        assert installed["design_id"] == "design"
        assert (tmp_path / "client-project" / installed["assets"][0]["relative_path"]).is_file()
        again = install_bundle(payload, tmp_path / "client-project")
        assert len(again["skipped"]) == 1
        preview = await client.read_resource(context["preview_resource"])
        assert base64.b64decode(preview[0].blob).startswith(b"\x89PNG")
        clean = await client.read_resource(context["reference_crop_resource"])
        assert clean[0].blob != preview[0].blob


@pytest.mark.asyncio
async def test_partial_exports_and_unknown_assets_are_not_false_success(tmp_path):
    service = FakeDesignService(tmp_path)
    sid = (await service.prepare(URL))["snapshot_id"]
    service.fail_asset = True
    result = await service.export(sid)
    assert result["status"] == "failed" and result["failed"]
    assert not result["assets"]
    with pytest.raises(DesignError):
        await service.export(sid, asset_ids=["wrong-version-asset"])


def test_mixed_design_url_preserves_design_identity_and_requires_exact_version():
    result = parse_design_reference(URL + "&docId=prototype&docType=axure&type=image&versionId=prototype-version")
    assert result["design_id"] == "design" and result["mixed_document_query"]
    assert result["url_version"] == "prototype-version"
    with pytest.raises(DesignError):
        parse_design_reference(URL.replace("detailDetach", "product") + "&docType=axure")


@pytest.mark.asyncio
async def test_credentials_do_not_follow_cdn_redirects(tmp_path, monkeypatch):
    requests = []
    def handle(request):
        requests.append(request)
        if request.url.host == "lanhuapp.com":
            return httpx.Response(302, headers={"Location": "https://lanhu.oss-cn-beijing.aliyuncs.com/asset"})
        return httpx.Response(200, content=b"image-bytes")
    original_client = httpx.AsyncClient
    def factory(**kwargs):
        return original_client(transport=httpx.MockTransport(handle), **kwargs)
    monkeypatch.setattr("lanhu_design.service.httpx.AsyncClient", factory)
    service = DesignService(tmp_path, cookie="private-cookie")
    assert await service.fetch_bytes("https://lanhuapp.com/asset") == b"image-bytes"
    assert requests[0].headers["cookie"] == "private-cookie"
    assert "cookie" not in requests[1].headers
    with pytest.raises(DesignError):
        await service.fetch_bytes("https://unrelated.example/asset")


@pytest.mark.asyncio
async def test_a_different_credential_namespace_cannot_read_cached_resources(tmp_path):
    service = FakeDesignService(tmp_path)
    sid = (await service.prepare(URL))["snapshot_id"]
    service.query(sid)
    another_account = DesignService(tmp_path, cookie="another-account")
    with pytest.raises(DesignError, match="not cached"):
        another_account.load(sid)


@pytest.mark.asyncio
async def test_hidden_ancestor_and_numeric_dds_ids_are_respected(tmp_path):
    service = FakeDesignService(tmp_path)
    sid = (await service.prepare(URL))["snapshot_id"]
    data = service.load(sid)
    data["nodes"][1]["source_visible"] = False
    data["nodes"][2]["source_visible"] = True
    data["nodes"][2]["source_id"] = "7423"
    data["dds_layout"] = {"layerId": 7423, "props": {"style": {"fontSize": 12}}}
    (service._snapshot_dir(sid) / "snapshot.json").write_text(json.dumps(data))
    hidden = service.query(sid, node_ids=["label"])
    assert hidden["returned"] == 0 and hidden["labels"] == []
    explicit = service.query(sid, node_ids=["label"], include_hidden=True)
    assert explicit["nodes"][0]["source_visible"] is True
    assert explicit["nodes"][0]["effective_source_visible"] is False
    assert explicit["labels"] == []
    assert explicit["dds_layout_suggestions"][0]["node_id"] == "label"


@pytest.mark.asyncio
async def test_nonzero_canvas_origin_fails_explicitly_instead_of_wrong_crop(tmp_path):
    service = FakeDesignService(tmp_path)
    original = service.fetch_json
    async def fetch(url):
        value = await original(url)
        if "info" in value:
            value["info"][0]["left"] = 1000
        return value
    service.fetch_json = fetch
    with pytest.raises(DesignError) as error:
        await service.prepare(URL)
    assert error.value.code == "UnsupportedCoordinates"


@pytest.mark.asyncio
async def test_changed_normalizer_output_does_not_reuse_old_derived_snapshot(tmp_path, monkeypatch):
    import lanhu_design.service as module
    service = FakeDesignService(tmp_path)
    first = await service.prepare(URL)
    normalize = module.normalize_design
    def improved(raw):
        result = normalize(raw)
        result["schema_version"] = 2
        return result
    monkeypatch.setattr(module, "normalize_design", improved)
    second = await service.prepare(URL)
    assert first["snapshot_id"] != second["snapshot_id"]
    assert first["resolved_version"] == second["resolved_version"]


@pytest.mark.asyncio
async def test_mcp_visual_failures_are_json_objects_and_preserve_decoder_reason(tmp_path, monkeypatch):
    import lanhu_mcp_server as server
    import lanhu_design.service as module
    from lanhu_design.media import _AssetError
    service = FakeDesignService(tmp_path)
    monkeypatch.setattr(server, "_design_service", service)
    async with Client(server.mcp) as client:
        result = await client.call_tool("lanhu_get_design_overview", {"url": URL, "version_id": "missing"})
        error = json.loads(result.content[0].text)
        assert error["status"] == "error" and error["code"] == "VersionUnavailable"
        prepared = await service.prepare(URL)
        def too_large(*args, **kwargs):
            raise _AssetError("image_too_large", "Image exceeds the decoder pixel limit")
        monkeypatch.setattr(module, "render_region", too_large)
        result = await client.call_tool("lanhu_inspect_design_region", {
            "snapshot_id": prepared["snapshot_id"], "node_ids": ["button"]})
        error = json.loads(result.content[0].text)
        assert error["code"] == "image_too_large"
        assert "pixel limit" in error["message"]


@pytest.mark.asyncio
async def test_large_reference_uses_bounded_overview_and_native_region(tmp_path, monkeypatch):
    import lanhu_design.service as module
    service = FakeDesignService(tmp_path)
    original_json = service.fetch_json
    async def fetch_json(url):
        data = await original_json(url)
        if "info" in data:
            data["info"][0].update(width=500, height=200)
        return data
    calls = []
    async def fetch_bytes(url):
        calls.append(url)
        process = parse_qs(urlsplit(url).query).get("x-oss-process", [""])[0]
        if "crop," in process:
            return png(1000, 800)
        if "resize," in process:
            return png(500, 200)
        return png(5000, 2000)
    service.fetch_json, service.fetch_bytes = fetch_json, fetch_bytes
    monkeypatch.setattr(module, "MAX_IMAGE_PIXELS", 8_000_000)
    prepared = await service.prepare(URL)
    assert prepared["original_reference_size"] == {"width": 5000, "height": 2000}
    assert prepared["reference_size"] == {"width": 500, "height": 200}
    assert prepared["preview_downsampled"] is True
    overview = service.query(prepared["snapshot_id"], annotate=False)
    assert overview["visual_source"] == "bounded_preview"
    region = await service.inspect(prepared["snapshot_id"], region={"x": 100, "y": 50, "width": 100, "height": 80})
    assert region["visual_source"] == "original_region"
    assert region["source_region"] == {"x": 100, "y": 50, "width": 100, "height": 80}
    assert region["image_size"] == {"width": 1000, "height": 800}
    assert any("crop,x_1000,y_500,w_1000,h_800" in urlsplit(url).query.replace("%2C", ",") for url in calls)
    crop_count = len(calls)
    await service.inspect(prepared["snapshot_id"], region={"x": 100, "y": 50, "width": 100, "height": 80})
    assert len(calls) == crop_count


@pytest.mark.asyncio
async def test_region_fetch_failure_returns_labeled_lower_resolution_evidence(tmp_path):
    service = FakeDesignService(tmp_path)
    sid = (await service.prepare(URL))["snapshot_id"]
    cached = service.load(sid)
    cached["preview_downsampled"] = True
    (service._snapshot_dir(sid) / "snapshot.json").write_text(json.dumps(cached))
    async def fail(url):
        raise DesignError("AccessDenied", "provider rejected processing")
    service.fetch_bytes = fail
    result = await service.inspect(sid, node_ids=["button"])
    assert result["visual_source"] == "bounded_preview"
    assert any(g["code"] == "native_region_unavailable" for g in result["gaps"])
    assert result["nodes"][0]["node_id"] == "button"


@pytest.mark.asyncio
async def test_svg_selection_is_public_and_has_separate_verifiable_bundle(tmp_path):
    service = FakeDesignService(tmp_path)
    sid = (await service.prepare(URL))["snapshot_id"]
    data = service.load(sid)
    asset = data["assets"][0]
    asset["variants"].append({"url": "https://source/asset.svg?signature=hidden", "format_hint": "svg", "source_field": "image.svgUrl"})
    data["nodes"][1]["raw_style"]["font"] = {
        "content": "字体", "styles": [{"location": "0", "length": "2", "size": "12", "font": "ExampleFont", "fontWeight": 600}]}
    data["nodes"][1]["text"] = "字体"
    (service._snapshot_dir(sid) / "snapshot.json").write_text(json.dumps(data))
    original_fetch = service.fetch_bytes
    async def fetch(url):
        if ".svg" in url:
            return b'<svg xmlns="http://www.w3.org/2000/svg" width="40" height="30"><rect width="40" height="30" fill="red"/></svg>'
        return await original_fetch(url)
    service.fetch_bytes = fetch
    context = service.query(sid, node_ids=["button"])
    assert any(v["format_hint"] == "svg" for v in context["assets"][0]["variants"])
    assert "hidden" not in json.dumps(context["assets"])
    assert context["nodes"][0]["text_spec"]["text_runs"][0]["text"] == "字体"
    assert context["font_requirements"][0]["availability"] == "not_checked"
    png_bundle = await service.export(sid)
    svg_bundle = await service.export(sid, format_preference="prefer_svg")
    assert svg_bundle["bundle_resource"] != png_bundle["bundle_resource"]
    assert svg_bundle["assets"][0]["format"] == "svg"
    assert svg_bundle["assets"][0]["base_asset_id"] == asset["asset_id"]
    assert svg_bundle["assets"][0]["requested_preference"] == "prefer_svg"
    blob = service.artifact(sid, "bundle", svg_bundle["bundle_id"])
    receipt = install_bundle(blob, tmp_path / "svg-client")
    assert receipt["assets"][0]["relative_path"].endswith(".svg")


def test_font_requirements_keep_mixed_numeric_and_named_weights():
    from lanhu_design.service import _font_requirements
    result = _font_requirements([{
        "node_id": "mixed", "text": "ab", "raw_style": {"font": {
            "font": "Example", "fontWeight": 400,
            "styles": [{"font": "Example", "fontWeight": "bold", "location": 0, "length": 2}]}}}])
    assert result[0]["weights"] == [400, "bold"]
    assert result[0]["availability"] == "not_checked"


@pytest.mark.asyncio
async def test_overview_font_inventory_is_not_limited_by_node_pagination(tmp_path, monkeypatch):
    import lanhu_mcp_server as server
    service = FakeDesignService(tmp_path)
    original = service.fetch_json
    async def fetch(url):
        data = await original(url)
        if "info" in data:
            data["info"][2]["font"]["font"] = "OnlyLabelFont"
        return data
    service.fetch_json = fetch
    monkeypatch.setattr(server, "_design_service", service)
    async with Client(server.mcp) as client:
        result = await client.call_tool("lanhu_get_design_overview", {"url": URL, "limit": 1})
        data = json.loads(result.content[0].text)
        assert data["nodes"][0]["node_id"] == "board"
        assert data["font_requirements"][0]["family"] == "OnlyLabelFont"
        assert data["selected_font_requirements"] == []


@pytest.mark.asyncio
async def test_refreshed_signed_url_updates_transport_without_changing_snapshot_identity(tmp_path):
    service = FakeDesignService(tmp_path)
    original = service.fetch_json
    signature = "old"
    async def fetch(url):
        data = await original(url)
        if "/api/project/image?" in url:
            for version in data["result"]["versions"]:
                version["url"] += "?signature=" + signature
        return data
    service.fetch_json = fetch
    first = await service.prepare(URL)
    signature = "new"
    second = await service.prepare(URL)
    assert first["snapshot_id"] == second["snapshot_id"]
    assert service.load(second["snapshot_id"])["original_reference_url"].endswith("signature=new")


@pytest.mark.asyncio
async def test_tiny_provider_image_is_not_reported_as_native_detail(tmp_path):
    service = FakeDesignService(tmp_path)
    sid = (await service.prepare(URL))["snapshot_id"]
    data = service.load(sid)
    data["preview_downsampled"] = True
    (service._snapshot_dir(sid) / "snapshot.json").write_text(json.dumps(data))
    async def undersized(url):
        return png(10, 10)
    service.fetch_bytes = undersized
    query = {"region": {"x": 10, "y": 10, "width": 40, "height": 40}}
    result = await service.inspect(sid, **query)
    assert result["visual_source"] == "bounded_preview"
    assert any(g.get("reason") == "RegionMismatch" for g in result["gaps"])
    async def correct(url):
        return png(80, 80)
    service.fetch_bytes = correct
    assert (await service.inspect(sid, **query))["visual_source"] == "original_region"


@pytest.mark.asyncio
async def test_raster_request_cannot_succeed_with_hidden_svg_and_failure_is_retryable(tmp_path):
    service = FakeDesignService(tmp_path)
    sid = (await service.prepare(URL))["snapshot_id"]
    data = service.load(sid)
    asset = data["assets"][0]
    asset["url"] = "https://source/opaque"
    asset["format_hint"] = None
    asset["variants"] = [{"url": asset["url"], "format_hint": None, "source_field": "image.imageUrl"}]
    (service._snapshot_dir(sid) / "snapshot.json").write_text(json.dumps(data))
    async def svg(url):
        return b'<svg xmlns="http://www.w3.org/2000/svg" width="40" height="30"><rect width="40" height="30"/></svg>'
    service.fetch_bytes = svg
    result = await service.export(sid, format_preference="raster")
    assert result["status"] == "failed" and result["counts"]["succeeded"] == 0
    assert result["assets"] == []
    failed = result["failed"][0]
    assert failed["error"] == "DownloadedVariantMismatch"
    assert failed["base_asset_id"] == asset["asset_id"]
    assert failed["requested_preference"] == "raster"
    assert failed["selected_source_field"] == "image.imageUrl"
