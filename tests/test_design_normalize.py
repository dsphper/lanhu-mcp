"""Synthetic source contracts: identity and export evidence never depend on names."""

from copy import deepcopy

import pytest

from lanhu_design.normalize import normalize_design


def _sketch():
    return {
        "type": "sketchPlugin",
        "ArtboardID": "canvas",
        "sliceScale": 2,
        "ArtboardScale": 1,
        "info": [
            {"id": "canvas", "ddsType": "artboard-group", "left": 0, "top": 0,
             "width": 1920, "height": 2000},
            {"id": "label", "name": "矩形备份", "type": "text", "parentID": "button",
             "left": 0, "top": 722.125, "width": 75.5, "height": 20,
             "font": {"content": "领取", "size": 14, "line": 20}, "opacity": 0,
             "isVisible": False},
            {"id": "button", "name": "矩形备份", "type": "layer-group", "parentID": "canvas",
             "left": 460, "top": 709, "width": 1000, "height": 111, "exportable": True,
             "image": {"imageUrl": "https://cdn.example.test/original.png",
                       "svgUrl": "https://cdn.example.test/original.svg",
                       "size": {"width": 1000, "height": 111},
                       "point": {"x": -999, "y": -444}},
             "ddsImage": {"imageUrl": "https://cdn.example.test/render.png"}},
            {"id": "decoration", "name": "download_button", "parentID": "button",
             "left": 480.25, "top": 720, "width": 15, "height": 12,
             "exportable": False, "ddsImage": {"imageUrl": "https://cdn.example.test/path.png"}},
        ],
    }


def _nodes(result):
    return {node["node_id"]: node for node in result["nodes"]}


def _codes(result):
    return {gap["code"] for gap in result["gaps"]}


def test_sketch_flat_parent_links_text_and_asset_categories_use_source_evidence():
    result = normalize_design(_sketch())
    nodes = _nodes(result)
    assert result["source_type"] == "sketch"
    assert result["coordinate_space"] == "source_canvas"
    assert result["canvas"] == {"width": 1920, "height": 2000}
    assert nodes["label"]["parent_id"] == "button"
    assert nodes["button"]["parent_id"] == "canvas"
    assert nodes["canvas"]["parent_id"] is None
    assert nodes["label"]["text"] == "领取"
    assert nodes["label"]["source_visible"] is False
    assert nodes["label"]["raw_style"]["opacity"] == 0
    assert nodes["label"]["bounds"]["x"] == 0
    assert nodes["label"]["bounds"]["y"] == 722.125
    assert nodes["button"]["bounds"] == {"x": 460, "y": 709, "width": 1000, "height": 111}
    exports = [asset for asset in result["assets"] if asset["kind"] == "exported_asset"]
    assert len(exports) == 1
    assert exports[0]["node_id"] == "button"
    assert exports[0]["render_bounds"] == nodes["button"]["bounds"]
    assert exports[0]["url"].endswith("original.png")
    assert {variant["format_hint"] for variant in exports[0]["variants"]} == {"png", "svg"}
    assert len([asset for asset in result["assets"] if asset["kind"] == "render_fallback"]) == 2
    assert "label" in nodes  # An exported parent does not suppress child evidence.
    assert exports[0]["pixel_dimensions"] is None
    assert "logical_coordinate_conversion_unknown" in _codes(result)


def test_layer_rename_does_not_change_identity_geometry_relationships_or_assets():
    raw = _sketch()
    renamed = deepcopy(raw)
    for index, layer in enumerate(renamed["info"]):
        layer["name"] = f"编组{index}"
    before = normalize_design(raw)
    after = normalize_design(renamed)
    assert before["assets"] == after["assets"]
    assert before["gaps"] == after["gaps"]
    assert before["canvas"] == after["canvas"]
    for node in before["nodes"] + after["nodes"]:
        node.pop("name")
    assert before["nodes"] == after["nodes"]


def test_designer_export_keeps_its_own_bounds_instead_of_dds_render_bounds():
    raw = _sketch()
    layer = raw["info"][2]
    layer["ddsOriginFrame"] = {"x": 459, "y": 709.98, "width": 1003, "height": 110}
    result = normalize_design(raw)
    export = next(a for a in result["assets"] if a["node_id"] == "button" and a["source_field"] == "image")
    dds = next(a for a in result["assets"] if a["node_id"] == "button" and a["source_field"] == "ddsImage")
    assert export["render_bounds"] == {"x": 460, "y": 709, "width": 1000, "height": 111}
    assert dds["render_bounds"] == layer["ddsOriginFrame"]


def test_missing_bounds_are_unknown_and_source_id_zero_is_preserved():
    result = normalize_design({"info": [
        {"id": 0, "name": "missing position", "width": 10, "height": 5},
        {"id": "zero", "x": 0, "left": 12, "y": 0, "top": 13, "width": 0, "height": 0},
        {"id": "bad", "left": False, "top": 0, "width": 5, "height": 5},
        {"id": "nan", "left": float("nan"), "top": 0, "width": 5, "height": 5},
    ]})
    nodes = _nodes(result)
    assert nodes["0"]["source_id"] == "0"
    assert nodes["0"]["bounds"] is None
    assert nodes["zero"]["bounds"] == {"x": 0, "y": 0, "width": 0, "height": 0}
    assert nodes["bad"]["bounds"] is None
    assert nodes["nan"]["bounds"] is None
    assert result["canvas"] == {"width": None, "height": None}
    assert "missing_canvas_dimensions" in _codes(result)


def test_pointer_identity_and_duplicate_source_ids_are_explicit_and_unique():
    raw = {"info": [{"name": "same"}, {"name": "same"}, {"id": "dup"}, {"id": "dup"},
                    {"id": "child", "parentID": "dup"}]}
    result = normalize_design(raw)
    ids = [node["node_id"] for node in result["nodes"]]
    assert len(ids) == len(set(ids))
    assert result == normalize_design(deepcopy(raw))
    assert all(node["identity_source"] == "source_pointer" for node in result["nodes"][:2])
    assert all(node["identity_source"] == "duplicate_source_id_and_pointer" for node in result["nodes"][2:4])
    assert _nodes(result)["child"]["parent_id"] is None
    assert _nodes(result)["child"]["source_parent_id"] == "dup"
    assert "ambiguous_parent_id" in _codes(result)


def test_parent_cycles_and_dangling_references_do_not_create_recursive_tree():
    result = normalize_design({"info": [
        {"id": "a", "parentID": "b"}, {"id": "b", "parentID": "a"},
        {"id": "c", "parentID": "missing"}, {"id": "self", "parentID": "self"},
        {"id": "descendant", "parentID": "a"},
    ]})
    nodes = _nodes(result)
    assert nodes["a"]["parent_id"] is None
    assert nodes["b"]["parent_id"] is None
    assert nodes["self"]["parent_id"] is None
    assert nodes["a"]["source_parent_id"] == "b"
    assert nodes["descendant"]["parent_id"] == "a"
    assert nodes["c"]["parent_id"] is None
    assert {"parent_cycle", "missing_parent_id"} <= _codes(result)


def test_figma_nested_source_coordinates_are_not_added_to_parent_or_divided_by_scale():
    raw = {
        "meta": {"host": {"name": "figma"}, "sliceScale": 3},
        "artboard": {"id": "board", "frame": {"width": 375, "height": 1130}, "layers": [
            {"id": "group", "type": "groupLayer", "name": "组", "hasExportImage": True,
             "frame": {"left": 15, "top": 939, "width": 184, "height": 44},
             "image": {"imageUrl": "https://cdn.example.test/group.png"}, "layers": [
                 {"id": "text", "type": "textLayer", "name": "组", "frame":
                  {"left": 63, "top": 955, "width": 106, "height": 18},
                  "transform": [[1, 0, 63], [0, 1, 955]],
                  "text": {"value": "反馈", "style": {"font": {"size": 12}}}},
                 {"id": "shape", "type": "shapeLayer", "hasExportImage": False,
                  "ddsImage": {"imageUrl": "https://cdn.example.test/shape.png"},
                  "style": {"fills": [{"image": {"imageUrl": "https://cdn.example.test/fill.png"}}]}},
             ]},
        ]},
    }
    result = normalize_design(raw)
    nodes = _nodes(result)
    assert result["source_type"] == "figma"
    assert result["canvas"] == {"width": 375, "height": 1130}
    assert nodes["text"]["parent_id"] == "group"
    assert nodes["text"]["bounds"] == {"x": 63, "y": 955, "width": 106, "height": 18}
    assert nodes["text"]["text"] == "反馈"
    assert nodes["text"]["raw_style"]["transform"] == [[1, 0, 63], [0, 1, 955]]
    assert "transform_preserved_not_applied" in _codes(result)
    assert {asset["kind"] for asset in result["assets"]} == {"exported_asset", "render_fallback", "image_fill"}
    assert [asset["node_id"] for asset in result["assets"] if asset["kind"] == "exported_asset"] == ["group"]


def test_photoshop_asset_index_resolves_to_board_layer_without_document_offset_or_scale():
    raw = {
        "type": "ps", "sliceScale": 2,
        "board": {"id": 1, "width": 1170, "height": 2532, "layers": [
            {"id": 7423, "name": "same", "left": 428.5, "top": 978, "width": 196, "height": 57,
             "images": {"png_xxxhd": "https://cdn.example.test/export.png", "svg": "https://cdn.example.test/export.svg"}},
            {"id": 7424, "name": "same", "isAsset": True,
             "bounds": {"left": 0, "top": 0, "right": 15, "bottom": 20},
             "images": {"png_xxxhd": "https://cdn.example.test/export2.png"}},
        ]},
        "assets": [{"id": 7423, "isAsset": True, "isSlice": False,
                    "bounds": {"left": 4089, "top": 2971, "right": 4285, "bottom": 3028}},
                   {"id": 999, "isAsset": True}],
        "info": [],
    }
    result = normalize_design(raw)
    nodes = _nodes(result)
    assert result["source_type"] == "photoshop"
    assert result["canvas"] == {"width": 1170, "height": 2532}
    assert nodes["7423"]["parent_id"] == "1"
    assert nodes["7423"]["bounds"] == {"x": 428.5, "y": 978, "width": 196, "height": 57}
    assert nodes["7424"]["bounds"] == {"x": 0, "y": 0, "width": 15, "height": 20}
    assert len(result["assets"]) == 2
    assert all(asset["kind"] == "exported_asset" for asset in result["assets"])
    assert result["assets"][0]["source_evidence"] == ["/assets/0"]
    assert {"unresolved_asset_node", "photoshop_coordinates_unconverted"} <= _codes(result)


def test_export_flag_without_url_and_false_string_are_not_successful_exports():
    result = normalize_design({"info": [
        {"id": "missing", "exportable": True},
        {"id": "string", "exportable": "false", "image": {"imageUrl": "https://cdn.example.test/preview.png"}},
        {"id": "bad-url", "exportable": True, "image": {"imageUrl": "javascript:alert(1)"}},
        {"id": "numeric", "exportable": 1, "image": {"svgUrl": "https://cdn.example.test/valid.svg"}},
    ]})
    assert [asset["node_id"] for asset in result["assets"] if asset["kind"] == "exported_asset"] == ["numeric"]
    assert {"export_marked_without_download_url", "asset_without_download_url"} <= _codes(result)


def test_normalization_does_not_mutate_source_and_output_styles_are_detached():
    raw = _sketch()
    original = deepcopy(raw)
    result = normalize_design(raw)
    assert raw == original
    _nodes(result)["label"]["raw_style"]["font"]["size"] = 999
    assert raw == original


def test_unsupported_structure_and_invalid_input_are_explicit():
    result = normalize_design({"unrecognized": []})
    assert result["source_type"] == "unknown"
    assert result["nodes"] == []
    assert "unsupported_source_structure" in _codes(result)
    with pytest.raises(TypeError):
        normalize_design([])


@pytest.mark.parametrize("raw", [
    {"meta": {"host": {"name": "figma"}}, "artboard": {
        "id": "board", "frame": {"x": 1000, "y": 2000, "width": 100, "height": 200},
        "layers": [{"id": "child", "frame": {"x": 1010, "y": 2020, "width": 20, "height": 30}}],
    }},
    {"type": "ps", "board": {
        "id": "board", "left": 1000, "top": 2000, "width": 100, "height": 200,
        "layers": [{"id": "child", "left": 1010, "top": 2020, "width": 20, "height": 30}],
    }},
])
def test_nonzero_canvas_origin_is_explicit_without_translating_nodes(raw):
    result = normalize_design(raw)
    assert result["canvas_origin"] == {"x": 1000, "y": 2000}
    assert result["canvas"] == {"width": 100, "height": 200}
    assert "nonzero_canvas_origin_unverified" in _codes(result)
    assert _nodes(result)["child"]["bounds"] == {"x": 1010, "y": 2020, "width": 20, "height": 30}


def test_sketch_document_position_is_not_a_canvas_origin():
    raw = _sketch()
    raw["info"][0].update({"position_x": -317, "position_y": -130.25})
    result = normalize_design(raw)
    assert result["canvas_origin"] == {"x": 0, "y": 0}
    assert "nonzero_canvas_origin_unverified" not in _codes(result)
    assert _nodes(result)["button"]["bounds"]["x"] == 460
    assert _nodes(result)["canvas"]["raw_style"]["position_y"] == -130.25


def test_canvas_without_position_has_unknown_origin_but_retains_dimensions():
    result = normalize_design({"artboard": {"id": "board", "frame": {"width": 375, "height": 1130}}})
    assert result["canvas"] == {"width": 375, "height": 1130}
    assert result["canvas_origin"] is None
    assert "nonzero_canvas_origin_unverified" not in _codes(result)
