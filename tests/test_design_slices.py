"""Tests for design slice extraction behavior."""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lanhu_mcp_server import BASE_URL, LanhuExtractor  # noqa: E402


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class _RoutingClient:
    def __init__(self, image_payload, json_payload):
        self.image_payload = image_payload
        self.json_payload = json_payload
        self.calls = []

    async def get(self, url, params=None, **kwargs):
        self.calls.append((url, params, kwargs))
        if url == f"{BASE_URL}/api/project/image":
            return _FakeResponse(self.image_payload)
        if url == "https://example.com/design.json":
            return _FakeResponse(self.json_payload)
        raise AssertionError(f"Unexpected URL: {url}")

    async def aclose(self):
        return None


def test_get_design_slices_info_includes_photoshop_assets_marked_only_as_isasset():
    image_payload = {
        "code": "00000",
        "result": {
            "name": "7日弹窗切图",
            "width": 1170,
            "height": 2532,
            "versions": [
                {
                    "version_info": "版本2",
                    "json_url": "https://example.com/design.json",
                }
            ],
        },
    }
    json_payload = {
        "type": "ps",
        "sliceScale": 2,
        "board": {
            "id": 1,
            "type": "artboardSection",
            "layers": [
                {
                    "id": 7423,
                    "name": "example_img__01",
                    "type": "layer",
                    "isAsset": True,
                    "isSlice": False,
                    "left": 428,
                    "top": 978,
                    "width": 196,
                    "height": 57,
                    "images": {
                        "png_xxxhd": "https://cdn.example.com/example_img__01.png",
                    },
                }
            ],
        },
        "info": [],
        "assets": [
            {
                "id": 7423,
                "name": "example_img__01",
                "isAsset": True,
                "isSlice": False,
                "scaleType": 1,
                "bounds": {
                    "left": 4089,
                    "top": 2971,
                    "right": 4285,
                    "bottom": 3028,
                },
            }
        ],
    }

    extractor = LanhuExtractor()
    extractor.client = _RoutingClient(image_payload, json_payload)  # type: ignore[assignment]
    try:
        result = asyncio.run(
            extractor.get_design_slices_info(
                image_id="af8296a4-d3a8-4280-9ecf-170533cc3200",
                project_id="626a5489-5570-4386-803f-811c70ee9428",
                include_metadata=False,
            )
        )
    finally:
        asyncio.run(extractor.close())

    assert result["design_name"] == "7日弹窗切图"
    assert result["total_slices"] == 1

    first = result["slices"][0]
    assert first["id"] == 7423
    assert first["name"] == "example_img__01"
    assert first["download_url"] == "https://cdn.example.com/example_img__01.png"
    assert first["format"] == "png"
    assert first["size"] == "196x57"
    assert first["position"] == {"x": 428, "y": 978}
