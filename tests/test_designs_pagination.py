"""Tests for lanhu_get_designs pagination / search / sector filtering.

Focus: legacy full-list behavior when limit is omitted, page slicing metadata,
global index stability across filters and pages, and the analyze fallback
name-list cap.
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import lanhu_mcp_server as server  # noqa: E402
from lanhu_mcp_server import (  # noqa: E402
    ANALYZE_AVAILABLE_NAMES_LIMIT,
    DESIGNS_PAGE_LIMIT_MAX,
    _filter_designs,
    _format_available_designs,
    _paginate_designs,
)


def _design(idx, name, sectors=()):
    return {
        "index": idx,
        "id": f"id-{idx}",
        "name": name,
        "width": 720.0,
        "height": 450.0,
        "url": f"https://example.com/{idx}.png",
        "has_comment": False,
        "update_time": "2026-11-01T00:00:00Z",
        "sectors": list(sectors),
    }


def _full_list():
    return [
        _design(1, "登录页", ("院级理论考试",)),
        _design(2, "预约界面", ("面授学习",)),
        _design(3, "考试提交", ("院级理论考试",)),
        _design(4, "我的预约", ("在线学习",)),
        _design(5, "成绩统计", ()),
    ]


# ---------------------------------------------------------------------------
# _filter_designs
# ---------------------------------------------------------------------------

def test_filter_by_search_is_case_insensitive_substring():
    got = _filter_designs(_full_list(), search="预约")
    assert [d["index"] for d in got] == [2, 4]

    got = _filter_designs(_full_list(), search="LOGIN")  # no match, ASCII case
    assert got == []


def test_filter_by_sector_matches_group_name_substring():
    got = _filter_designs(_full_list(), sector="院级理论考试")
    assert [d["index"] for d in got] == [1, 3]

    got = _filter_designs(_full_list(), sector="考试")  # substring across groups
    assert [d["index"] for d in got] == [1, 3]


def test_filter_combines_sector_and_search():
    got = _filter_designs(_full_list(), sector="面授学习", search="预约")
    assert [d["index"] for d in got] == [2]


def test_filter_without_criteria_returns_all_in_order():
    designs = _full_list()
    assert _filter_designs(designs) == designs


# ---------------------------------------------------------------------------
# _paginate_designs
# ---------------------------------------------------------------------------

def test_paginate_without_limit_returns_everything():
    page, meta = _paginate_designs(_full_list())
    assert len(page) == 5
    assert meta == {
        "matched": 5,
        "offset": 0,
        "limit": None,
        "returned": 5,
        "next_offset": None,
        "truncated": False,
    }


def test_paginate_exact_page_has_no_next_offset():
    page, meta = _paginate_designs(_full_list(), offset=0, limit=5)
    assert len(page) == 5
    assert meta["truncated"] is False
    assert meta["next_offset"] is None


def test_paginate_last_partial_page():
    page, meta = _paginate_designs(_full_list(), offset=3, limit=2)
    assert [d["index"] for d in page] == [4, 5]
    assert meta == {
        "matched": 5, "offset": 3, "limit": 2, "returned": 2,
        "next_offset": None, "truncated": False,
    }


def test_paginate_reports_next_offset_when_truncated():
    page, meta = _paginate_designs(_full_list(), offset=0, limit=2)
    assert [d["index"] for d in page] == [1, 2]
    assert meta["truncated"] is True
    assert meta["next_offset"] == 2
    assert meta["returned"] == 2


def test_paginate_offset_beyond_end_returns_empty():
    page, meta = _paginate_designs(_full_list(), offset=99, limit=10)
    assert page == []
    assert meta["returned"] == 0
    assert meta["truncated"] is False
    assert meta["next_offset"] is None


def test_paginate_clamps_limit_and_offset():
    page, meta = _paginate_designs(_full_list(), offset=-5, limit=0)
    assert meta["offset"] == 0
    assert meta["limit"] == 1
    assert len(page) == 1

    page, meta = _paginate_designs(_full_list(), limit=DESIGNS_PAGE_LIMIT_MAX + 50)
    assert meta["limit"] == DESIGNS_PAGE_LIMIT_MAX


# ---------------------------------------------------------------------------
# lanhu_get_designs tool (with network layer faked)
# ---------------------------------------------------------------------------

async def _call_tool(monkeypatch, **kwargs):
    async def fake_internal(extractor, url):
        return {
            "status": "success",
            "project_name": "demo",
            "total_sectors": 2,
            "ungrouped_design_count": 1,
            "sectors": [
                {"id": "s1", "parent_id": None, "name": "院级理论考试",
                 "path": "院级理论考试", "order": 1, "image_count": 2},
            ],
            "total_designs": 5,
            "designs": _full_list(),
        }

    class DummyStore:
        def __init__(self, project_id):
            pass

        def record_collaborator(self, *args, **kwargs):
            return None

    monkeypatch.setattr(server, "_get_designs_internal", fake_internal)
    monkeypatch.setattr(server, "MessageStore", DummyStore)
    return await server.lanhu_get_designs(
        url="https://lanhuapp.com/web/#/item/project/stage?pid=p1", **kwargs)


def test_tool_without_limit_returns_full_list_with_legacy_shape(monkeypatch):
    result = asyncio.run(_call_tool(monkeypatch))
    assert result["status"] == "success"
    assert result["total_designs"] == 5
    assert len(result["designs"]) == 5
    # 新增分页元数据
    assert result["matched"] == 5
    assert result["truncated"] is False
    assert result["limit"] is None


def test_tool_pagination_keeps_global_index(monkeypatch):
    result = asyncio.run(_call_tool(monkeypatch, offset=3, limit=2))
    assert [d["index"] for d in result["designs"]] == [4, 5]
    assert result["matched"] == 5
    assert result["next_offset"] is None
    assert result["truncated"] is False


def test_tool_search_and_pagination(monkeypatch):
    result = asyncio.run(_call_tool(monkeypatch, search="预约", limit=1))
    assert [d["index"] for d in result["designs"]] == [2]
    assert result["matched"] == 2
    assert result["search"] == "预约"
    assert result["next_offset"] == 1
    assert "offset=1" in result["ai_suggestion"]["pagination"]


def test_tool_sector_filter_echoes_criteria(monkeypatch):
    result = asyncio.run(_call_tool(monkeypatch, sector="院级理论考试"))
    assert [d["index"] for d in result["designs"]] == [1, 3]
    assert result["sector"] == "院级理论考试"
    assert result["total_designs"] == 5  # 全量语义保持


def test_tool_no_match_suggests_relaxing_filters(monkeypatch):
    result = asyncio.run(_call_tool(monkeypatch, search="不存在的关键词"))
    assert result["designs"] == []
    assert result["matched"] == 0
    assert "No designs matched" in result["ai_suggestion"]["notice"]


def test_tool_large_unpaged_list_warns_about_client_truncation(monkeypatch):
    big = [_design(i, f"设计-{i}", ("组A",)) for i in range(1, 151)]

    async def fake_internal(extractor, url):
        return {"status": "success", "project_name": "big", "total_sectors": 1,
                "ungrouped_design_count": 0, "sectors": [], "total_designs": 150,
                "designs": big}

    class DummyStore:
        def __init__(self, project_id):
            pass

        def record_collaborator(self, *a, **k):
            return None

    monkeypatch.setattr(server, "_get_designs_internal", fake_internal)
    monkeypatch.setattr(server, "MessageStore", DummyStore)
    result = asyncio.run(server.lanhu_get_designs(
        url="https://lanhuapp.com/web/#/item/project/stage?pid=p1"))

    assert "client_truncation_risk" in result["ai_suggestion"]
    # 分页后不再出现截断预警
    result = asyncio.run(server.lanhu_get_designs(
        url="https://lanhuapp.com/web/#/item/project/stage?pid=p1", limit=50))
    assert "client_truncation_risk" not in result["ai_suggestion"]
    assert "pagination" in result["ai_suggestion"]


def test_tool_metadata_precedes_designs_for_truncation_survival(monkeypatch):
    result = asyncio.run(_call_tool(monkeypatch, limit=2))
    keys = list(result.keys())
    assert keys.index("matched") < keys.index("designs")
    assert keys.index("ai_suggestion") < keys.index("designs")


# ---------------------------------------------------------------------------
# analyze fallback name list
# ---------------------------------------------------------------------------

def test_format_available_designs_caps_and_hints():
    designs = [_design(i, f"页面{i}") for i in range(1, ANALYZE_AVAILABLE_NAMES_LIMIT + 10)]
    lines = _format_available_designs(designs)
    assert len(lines) == ANALYZE_AVAILABLE_NAMES_LIMIT + 1
    assert "lanhu_get_designs" in lines[-1]
    assert f"{9} more" in lines[-1]


def test_format_available_designs_small_list_kept_intact():
    lines = _format_available_designs(_full_list())
    assert len(lines) == 5
    assert lines[0] == "  • 登录页 [院级理论考试]"
    assert lines[4] == "  • 成绩统计"
