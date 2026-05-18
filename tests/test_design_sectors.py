"""Tests for Lanhu design sector mapping."""

from lanhu_mcp_server import _normalize_design_sectors


def test_get_designs_internal_normalizes_sector_paths_and_multi_group_membership():
    sectors = [
        {
            "id": "root",
            "parent_id": "",
            "name": "首页",
            "order": 100,
            "images": ["img-1"],
        },
        {
            "id": "child",
            "parent_id": "root",
            "name": "弹窗",
            "order": 90,
            "images": ["img-1", "img-2"],
        },
        {
            "id": "other",
            "parent_id": "",
            "name": "活动",
            "order": 80,
            "images": ["img-1"],
        },
    ]

    normalized_sectors, image_sector_map = _normalize_design_sectors(sectors)

    assert [sector["path"] for sector in normalized_sectors] == [
        "首页",
        "首页/弹窗",
        "活动",
    ]
    assert [sector["name"] for sector in image_sector_map["img-1"]] == [
        "首页",
        "弹窗",
        "活动",
    ]
    assert [sector["path"] for sector in image_sector_map["img-2"]] == [
        "首页/弹窗",
    ]
