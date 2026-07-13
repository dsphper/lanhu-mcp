"""Tests for Axure annotation extraction formatting."""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lanhu_mcp_server import _format_axure_annotations_for_text  # noqa: E402


def test_format_axure_annotations_includes_native_note_position_and_content():
    annotations = {
        "total": 2,
        "located": [
            {
                "fn": 12,
                "ownerId": "owner-1",
                "label": "包装条码",
                "noteText": "打包生成包裹码后回显",
                "scriptId": "u23",
                "annId": "u23_ann",
                "position": {"pageX": 101.4, "pageY": 205.6, "width": 16, "height": 16},
                "targetRect": {"pageX": 80, "pageY": 190, "width": 180, "height": 36},
            }
        ],
        "unlocated": [
            {
                "fn": 2,
                "ownerId": "owner-2",
                "label": "缺失映射",
                "noteText": "没有 scriptId",
                "reason": "missing_script_id",
            }
        ],
    }

    text = _format_axure_annotations_for_text(annotations)

    assert "Axure 标注信息" in text
    assert "总数 2，已定位 1，未定位 1" in text
    assert "[12] 包装条码" in text
    assert "ownerId=owner-1 scriptId=u23 annId=u23_ann" in text
    assert "标注位置: x=101.4 y=205.6 w=16 h=16" in text
    assert "目标位置: x=80 y=190 w=180 h=36" in text
    assert "打包生成包裹码后回显" in text
    assert "[2] 缺失映射 reason=missing_script_id ownerId=owner-2" in text


def test_format_axure_annotations_returns_empty_text_without_annotations():
    assert _format_axure_annotations_for_text({"total": 0, "located": [], "unlocated": []}) == ""
    assert _format_axure_annotations_for_text(None) == ""
