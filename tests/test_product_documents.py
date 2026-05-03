"""Tests for lanhu_list_product_documents / LanhuExtractor.list_product_documents.

Focused on URL construction, query param plumbing, response simplification,
RFC 2822 → CN TZ time formatting, and failure-path error surfacing.
"""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lanhu_mcp_server import (  # noqa: E402
    BASE_URL,
    LanhuExtractor,
    _format_lanhu_rfc2822,
)


# ---------------------------------------------------------------------------
# Time formatting
# ---------------------------------------------------------------------------

def test_format_lanhu_rfc2822_converts_gmt_to_cn_tz():
    # 09 Jan 2026 10:07:29 GMT == 18:07:29 Asia/Shanghai (UTC+8)
    assert _format_lanhu_rfc2822(
        "Fri, 09 Jan 2026 10:07:29 GMT"
    ) == "2026-01-09 18:07:29"


def test_format_lanhu_rfc2822_none_stays_none():
    assert _format_lanhu_rfc2822(None) is None
    assert _format_lanhu_rfc2822("") is None


def test_format_lanhu_rfc2822_bad_input_passthrough():
    assert _format_lanhu_rfc2822("not-a-date") == "not-a-date"


# ---------------------------------------------------------------------------
# URL parsing wired into the tool
# ---------------------------------------------------------------------------

def test_parse_url_extracts_tid_and_pid_for_product_documents_call():
    extractor = LanhuExtractor()
    try:
        params = extractor.parse_url(
            "https://lanhuapp.com/web/#/item/project/product"
            "?tid=7056ff9d-e769-4d67-9e2a-a6e8fed2d04f"
            "&pid=dff90e32-c416-4a72-92a5-ca60946fdccc"
        )
    finally:
        asyncio.run(extractor.close())

    assert params["team_id"] == "7056ff9d-e769-4d67-9e2a-a6e8fed2d04f"
    assert params["project_id"] == "dff90e32-c416-4a72-92a5-ca60946fdccc"


# ---------------------------------------------------------------------------
# list_product_documents: API plumbing + response simplification
# ---------------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _RecordingClient:
    """Drop-in replacement for httpx.AsyncClient.get capturing one call."""

    def __init__(self, payload):
        self._payload = payload
        self.calls = []

    async def get(self, url, params=None, **kwargs):
        self.calls.append(SimpleNamespace(url=url, params=params, kwargs=kwargs))
        return _FakeResponse(self._payload)

    async def aclose(self):
        return None


_SAMPLE_PAYLOAD = {
    "code": "00000",
    "msg": "Success",
    "result": {
        "default_group_id": "a508aa77-5253-42a1-a63c-8064dcc46466",
        "doc_can_download": True,
        "need_group": True,
        "resources": [
            {
                "batch": "2019",
                "create_time": "Fri, 09 Jan 2026 10:07:29 GMT",
                "group": None,
                "group_to_source_id": "",
                "height": 0.0,
                "home": False,
                "id": "474bb48d-9783-45da-9b2f-b4c3d38afc23",
                "is_replaced": False,
                "last_version_num": 1,
                "latest_version": "a1cefeb2-a881-42f5-96b6-dae35878cfea",
                "layout_data": "b629b57b-1417-4ae5-9db8-b7be47e06483",
                "name": "在售列表商品锁单展示",
                "order": 138,
                "pinyinname": "z",
                "position_x": 0.0,
                "position_y": 0.0,
                "share_id": "474bb48d-9783-45da-9b2f-b4c3d38afc23",
                "sketch_id": "3300dc4c-af2f-c475-992e-5339a6261831",
                "source": False,
                "text_scale": None,
                "trash_recovery": False,
                "type": "axure",
                "update_time": "Fri, 09 Jan 2026 10:07:29 GMT",
                "url": "",
                "user_id": "b629b57b-1417-4ae5-9db8-b7be47e06483",
                "width": 0.0,
            },
            {
                "id": "f4708e8b-8b10-40be-bdbe-cc1bcb6e5d99",
                "name": "支付宝实人认证",
                "type": "axure",
                "last_version_num": 3,
                "latest_version": "a08b4dab-9ae7-47ac-b7cc-b47278243a29",
                "create_time": "Mon, 29 Dec 2025 17:27:53 GMT",
                "update_time": "Mon, 05 Jan 2026 17:21:29 GMT",
            },
            # An entry without id must be skipped.
            {"name": "ghost", "id": None},
        ],
    },
}


def _run_list(payload, team_id, project_id):
    extractor = LanhuExtractor()
    fake = _RecordingClient(payload)
    extractor.client = fake  # type: ignore[assignment]
    try:
        result = asyncio.run(
            extractor.list_product_documents(team_id, project_id)
        )
    finally:
        # aclose is called by extractor.close(); swap our fake already provides it.
        asyncio.run(extractor.close())
    return result, fake


def test_list_product_documents_hits_correct_endpoint_with_query_params():
    _, fake = _run_list(
        _SAMPLE_PAYLOAD,
        team_id="TEAM-123",
        project_id="PROJ-456",
    )

    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call.url == f"{BASE_URL}/api/project/product_documents"
    assert call.params == {"team_id": "TEAM-123", "project_id": "PROJ-456"}


def test_list_product_documents_simplifies_shape_and_preserves_order():
    result, _ = _run_list(
        _SAMPLE_PAYLOAD,
        team_id="TEAM-123",
        project_id="PROJ-456",
    )

    assert result["default_group_id"] == (
        "a508aa77-5253-42a1-a63c-8064dcc46466"
    )
    assert result["doc_can_download"] is True
    assert result["need_group"] is True
    # ghost entry with id=None must be filtered out
    assert result["total"] == 2
    assert [d["doc_id"] for d in result["documents"]] == [
        "474bb48d-9783-45da-9b2f-b4c3d38afc23",
        "f4708e8b-8b10-40be-bdbe-cc1bcb6e5d99",
    ]


def test_list_product_documents_per_item_fields_are_minimal_and_normalized():
    result, _ = _run_list(
        _SAMPLE_PAYLOAD,
        team_id="TEAM-123",
        project_id="PROJ-456",
    )
    first = result["documents"][0]

    # Renamed id -> doc_id; time normalized to CN TZ; doc_url pre-built.
    assert first == {
        "doc_id": "474bb48d-9783-45da-9b2f-b4c3d38afc23",
        "name": "在售列表商品锁单展示",
        "type": "axure",
        "last_version_num": 1,
        "latest_version": "a1cefeb2-a881-42f5-96b6-dae35878cfea",
        "create_time": "2026-01-09 18:07:29",
        "update_time": "2026-01-09 18:07:29",
        "doc_url": (
            f"{BASE_URL}/web/#/item/project/product"
            "?tid=TEAM-123&pid=PROJ-456"
            "&docId=474bb48d-9783-45da-9b2f-b4c3d38afc23"
        ),
    }

    # Dropped raw/noise fields must not leak.
    noisy = {
        "batch", "group", "group_to_source_id", "height", "home",
        "is_replaced", "layout_data", "order", "pinyinname",
        "position_x", "position_y", "share_id", "sketch_id", "source",
        "text_scale", "trash_recovery", "url", "user_id", "width", "id",
    }
    assert noisy.isdisjoint(first.keys())


def test_list_product_documents_propagates_api_error():
    payload = {"code": "10001", "msg": "permission denied", "result": {}}
    extractor = LanhuExtractor()
    extractor.client = _RecordingClient(payload)  # type: ignore[assignment]
    try:
        raised = None
        try:
            asyncio.run(extractor.list_product_documents("T", "P"))
        except Exception as e:
            raised = e
    finally:
        asyncio.run(extractor.close())

    assert raised is not None
    assert "permission denied" in str(raised)
    assert "10001" in str(raised)


def test_list_product_documents_handles_empty_resources():
    payload = {
        "code": "00000",
        "msg": "Success",
        "result": {
            "default_group_id": "g",
            "doc_can_download": False,
            "need_group": False,
            "resources": [],
        },
    }
    result, _ = _run_list(payload, team_id="T", project_id="P")

    assert result["total"] == 0
    assert result["documents"] == []
    assert result["doc_can_download"] is False
