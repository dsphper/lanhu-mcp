"""Team discovery/search contracts, exercised without private fixtures or network."""

import asyncio
import json
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from fastmcp import Client

import lanhu_mcp_server as server

TEAM_URL = "https://lanhuapp.com/dashboard/#/item?tid=team"
Extractor = server.LanhuExtractor


def project(project_id, name):
    return {"sourceType": "dc_prj", "sourceId": project_id, "sourceName": name}


def design(design_id, name):
    return {"id": design_id, "name": name, "url": "https://example.invalid/preview.png", "update_time": "2026-01-01"}


@pytest.fixture
def backend(monkeypatch):
    """Replace the authenticated client, retaining real project/group parsing."""
    state = {
        "projects": [project("a", "Project A"), project("b", "Project B")],
        "designs": {"a": [design("a1", "Unrelated")], "b": [design("b1", "Target")]},
        "sectors": {"a": [], "b": []},
        "fail": {},
        "calls": [],
        "clients": [],
    }

    async def handle(request):
        state["calls"].append(request)
        path = request.url.path
        pid = request.url.params.get("project_id")
        failure = state["fail"].get((path, pid))
        if isinstance(failure, Exception):
            raise failure
        if isinstance(failure, int):
            return httpx.Response(failure, json={"msg": "private response must not leak"})
        if failure is not None:
            return httpx.Response(200, json=failure)
        if path.endswith("abstractfile/list"):
            assert request.method == "POST"
            assert json.loads(request.content) == {"tenantId": "team", "fid": "all"}
            payload = {"code": 0, "data": state["projects"]}
        elif path.endswith("project_sectors"):
            payload = {"code": "00000", "data": {"sectors": state["sectors"][pid]}}
        elif path.endswith("/images"):
            payload = {"code": "00000", "data": {"name": "Project " + pid.upper(), "images": state["designs"][pid]}}
        else:
            raise AssertionError(f"Unexpected request: {path}")
        return httpx.Response(200, json=payload)

    def factory():
        extractor = Extractor.__new__(Extractor)
        extractor.client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        state["clients"].append(extractor.client)
        return extractor

    monkeypatch.setattr(server, "LanhuExtractor", factory)
    return state


async def search(**kwargs):
    """Exercise the registered tool's implementation with normal Python arguments."""
    tool = server.lanhu_search_team_designs
    return await getattr(tool, "fn", tool)(**kwargs)


@pytest.mark.asyncio
async def test_cross_project_search_and_links(backend):
    result = await search(keyword="target", url=TEAM_URL)
    assert result["status"] == "success"
    assert result["complete"] is True
    assert result["total_projects"] == result["searched_projects"] == 2
    assert result["total_matches"] == 1
    match = result["designs"][0]
    assert (match["project_id"], match["design_id"], match["design_name"]) == ("b", "b1", "Target")
    assert match["matched_by"] == ["design_name"]
    assert match["thumbnail_url"].endswith("preview.png")
    assert match["update_time"] == "2026-01-01"
    assert Extractor.parse_url(None, match["project_url"])["project_id"] == "b"
    assert parse_qs(urlsplit(match["design_url"]).fragment.split("?", 1)[1])["image_id"] == ["b1"]
    assert all(client.is_closed for client in backend["clients"])


@pytest.mark.asyncio
async def test_group_ancestor_matches_with_source_names_and_multi_group_paths(backend):
    backend["sectors"]["a"] = [
        {"id": "root", "name": "应用Ａ", "images": [], "parent_id": ""},
        {"id": "child", "name": "启动", "images": ["a1"], "parent_id": "root"},
        {"id": "other", "name": "Other", "images": ["a1"], "parent_id": ""},
    ]
    result = await search(keyword="应用a", team_id="team")
    assert result["total_matches"] == 1
    match = result["designs"][0]
    assert match["design_name"] == "Unrelated"
    assert match["matched_by"] == ["sector_name"]
    assert match["sector_paths"] == ["应用Ａ/启动", "Other"]
    assert match["matched_sector_paths"] == ["应用Ａ/启动"]


@pytest.mark.asyncio
async def test_normalization_duplicate_ids_duplicate_names_and_pagination(backend):
    backend["projects"] += [project("a", "Duplicate"), {"sourceType": "folder", "sourceId": "folder"}]
    backend["designs"]["a"] = [design("x", "ＴＡＲＧＥＴ"), design("x", "ＴＡＲＧＥＴ"), design("z", "Target")]
    backend["designs"]["b"] = [design("x", "Target")]
    first = await search(keyword=" target ", team_id="team", limit=2)
    second = await search(keyword="target", url=TEAM_URL, limit=2, offset=first["next_offset"])
    assert first["total_projects"] == 2
    assert first["total_matches"] == second["total_matches"] == 3
    assert [(m["project_id"], m["design_id"]) for m in first["designs"]] == [("a", "x"), ("a", "z")]
    assert [(m["project_id"], m["design_id"]) for m in second["designs"]] == [("b", "x")]
    assert first["has_more"] is True
    assert second["has_more"] is False and second["next_offset"] is None
    beyond = await search(keyword="target", team_id="team", offset=99)
    assert beyond["designs"] == [] and beyond["has_more"] is False


@pytest.mark.asyncio
async def test_name_and_group_matches_are_both_reported(backend):
    backend["sectors"]["b"] = [{"id": "g", "name": "Target group", "images": ["b1"]}]
    result = await search(keyword="target", team_id="team")
    assert result["designs"][0]["matched_by"] == ["design_name", "sector_name"]


@pytest.mark.asyncio
@pytest.mark.parametrize("projects", [[], [project("a", "Project A")]])
async def test_no_match_is_complete_only_after_successful_search(backend, projects):
    backend["projects"] = projects
    result = await search(keyword="Absent", team_id="team")
    assert result["status"] == "success" and result["complete"] is True
    assert result["total_matches"] == 0 and result["designs"] == []
    assert result["failed_projects"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "arguments",
    [
        {"keyword": "target"},
        {"keyword": " ", "team_id": "team"},
        {"keyword": "\u3000", "team_id": "team"},
        {"keyword": "target", "url": TEAM_URL, "team_id": "other"},
        {"keyword": "target", "url": "https://lanhuapp.com/dashboard/#/item"},
        {"keyword": "target", "url": TEAM_URL + "&tid=team"},
        {"keyword": "target", "url": "https://example.invalid/#/?tid=team"},
        {"keyword": "target", "team_id": "team", "limit": 0},
        {"keyword": "target", "team_id": "team", "limit": 201},
        {"keyword": "target", "team_id": "team", "offset": -1},
        {"keyword": "target", "team_id": "team", "limit": True},
    ],
)
async def test_invalid_arguments_make_no_requests(backend, arguments):
    result = await search(**arguments)
    assert result["error_code"] == "InvalidArguments"
    assert result["complete"] is False
    assert backend["calls"] == [] and backend["clients"] == []


@pytest.mark.asyncio
async def test_team_url_and_matching_explicit_id(backend):
    result = await search(keyword="target", url=TEAM_URL, team_id=" team ")
    assert result["status"] == "success"
    with pytest.raises(ValueError, match="pid"):
        Extractor.parse_url(None, TEAM_URL)


@pytest.mark.asyncio
async def test_network_failures_are_bounded_and_do_not_expose_diagnostics(backend):
    backend["fail"][("/api/project/images", "a")] = httpx.ConnectError("private authenticated URL")
    result = await search(keyword="target", team_id="team")
    assert result["status"] == "partial"
    assert result["failed_projects"][0]["error_code"] == "NetworkError"
    assert "private" not in json.dumps(result)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    [
        403,
        418,
        {"code": "401", "msg": "private"},
        {"code": 0},
        {"code": 0, "data": {"items": []}},
        {"code": 0, "data": [project("", "Invalid")]},
    ],
)
async def test_team_discovery_failure_never_reports_empty_success(backend, failure):
    backend["fail"][("/workbench/api/workbench/abstractfile/list", None)] = failure
    result = await search(keyword="target", team_id="team")
    assert result["status"] == "error" and result["complete"] is False
    assert "total_matches" not in result
    assert "private" not in json.dumps(result)
    assert all(client.is_closed for client in backend["clients"])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    [
        418,
        {"code": "failed", "msg": "private"},
        {"code": "00000", "data": {}},
        {"code": "00000", "data": {"images": [None]}},
        {"code": "00000", "data": {"images": [{"name": "Target"}]}},
    ],
)
async def test_project_failures_keep_other_matches_and_report_incomplete(backend, failure):
    backend["fail"][("/api/project/images", "a")] = failure
    result = await search(keyword="target", team_id="team")
    assert result["status"] == "partial" and result["complete"] is False
    assert result["searched_projects"] == 1
    assert result["designs"][0]["project_id"] == "b"
    assert result["failed_projects"][0]["stage"] == "designs"
    assert "private" not in json.dumps(result)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    [
        403,
        {"code": "failed", "msg": "private"},
        {"code": "00000", "data": {}},
        {"code": "00000", "data": {"sectors": [None]}},
    ],
)
async def test_group_failures_preserve_name_matches_but_mark_incomplete(backend, failure):
    backend["fail"][("/api/project/project_sectors", "b")] = failure
    result = await search(keyword="target", team_id="team")
    assert result["status"] == "partial" and result["complete"] is False
    assert result["searched_projects"] == 2 and result["total_matches"] == 1
    assert result["designs"][0]["matched_by"] == ["design_name"]
    assert result["failed_projects"] == [
        {"project_id": "b", "project_name": "Project B", "stage": "sectors", "error_code": "GroupListUnavailable"}
    ]


@pytest.mark.asyncio
async def test_project_concurrency_is_bounded_and_cancel_closes_client(backend, monkeypatch):
    backend["projects"] = [project(str(i), str(i)) for i in range(9)]
    active = peak = 0
    gate = asyncio.Event()
    entered = asyncio.Event()

    async def blocked(extractor, url, include_sector_paths=False):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        if active == 4:
            entered.set()
        try:
            await gate.wait()
            return {"status": "success", "designs": []}
        finally:
            active -= 1

    monkeypatch.setattr(server, "_get_designs_internal", blocked)
    task = asyncio.create_task(search(keyword="target", team_id="team"))
    await asyncio.wait_for(entered.wait(), 5)
    assert peak == active == 4
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert active == 0
    assert all(client.is_closed for client in backend["clients"])


@pytest.mark.asyncio
async def test_existing_design_listing_shape_is_unchanged(backend):
    extractor = server.LanhuExtractor()
    try:
        result = await server._get_designs_internal(extractor, "https://lanhuapp.com/web/#/item/project/stage?pid=a")
        assert "sector_paths" not in result["designs"][0]
    finally:
        await extractor.close()


@pytest.mark.asyncio
async def test_registered_mcp_schema_and_tool_call(backend):
    async with Client(server.mcp) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}
        schema = tools["lanhu_search_team_designs"].inputSchema
        assert set(schema["properties"]) == {"keyword", "url", "team_id", "limit", "offset"}
        assert schema["required"] == ["keyword"]
        result = await client.call_tool("lanhu_search_team_designs", {"url": TEAM_URL, "keyword": "target"})
        assert result.data["complete"] is True
        assert result.data["designs"][0]["design_id"] == "b1"
