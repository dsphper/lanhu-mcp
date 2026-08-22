"""Tests for the raw Sketch/Figma fallback converter."""

from lanhu_mcp_server import _get_sketch_design_scale, convert_sketch_to_html


def test_get_sketch_design_scale_reads_figma_meta():
    sketch_data = {
        "meta": {"device": "iOS @1x", "host": {"name": "figma"}},
        "artboard": {"frame": {"width": 375, "height": 1130}},
    }

    assert _get_sketch_design_scale(sketch_data) == 1.0


def test_convert_sketch_to_html_recurses_figma_group_layers():
    sketch_data = {
        "meta": {"device": "iOS @1x", "host": {"name": "figma"}},
        "artboard": {
            "frame": {"left": 0, "top": 0, "width": 375, "height": 1130},
            "layers": [
                {
                    "name": "Feedback Entry",
                    "type": "groupLayer",
                    "frame": {"left": 15, "top": 939, "width": 184, "height": 44},
                    "layers": [
                        {
                            "name": "Feedback Pill",
                            "type": "shapeLayer",
                            "frame": {"left": 30, "top": 950, "width": 169, "height": 28},
                        },
                        {
                            "name": "Feedback text",
                            "type": "textLayer",
                            "frame": {"left": 63, "top": 955, "width": 106, "height": 18},
                            "text": {
                                "value": "Feedback text",
                                "style": {
                                    "color": {"value": "rgba(72,76,79,1)"},
                                    "font": {
                                        "name": "PingFang SC",
                                        "size": 12,
                                        "fontWeight": 500,
                                        "lineHeight": {"unit": "PIXELS", "value": 18},
                                    },
                                },
                            },
                        },
                    ],
                }
            ],
        },
    }

    scale = _get_sketch_design_scale(sketch_data)
    html, image_mapping, annotations = convert_sketch_to_html(sketch_data, scale)

    assert "width:375.0px;height:1130.0px" in html
    assert "Feedback text" in html
    assert image_mapping == {}
    assert [annotation["name"] for annotation in annotations] == [
        "Feedback text",
        "Feedback Pill",
    ]
    assert annotations[0]["css"] == {
        "position": "absolute",
        "left": "63.0px",
        "top": "955.0px",
        "width": "106.0px",
        "height": "18.0px",
        "color": "rgba(72,76,79,1)",
        "font-size": "12.0px",
        "font-family": "PingFang SC",
        "font-weight": "500",
    }


def test_convert_sketch_to_html_keeps_figma_image_field_group():
    """Figma 编组带 image{imageUrl,svgUrl} 时应整体作为图片资源保留，不展开子层。"""
    sketch_data = {
        "meta": {"device": "iOS @1x", "host": {"name": "figma"}},
        "artboard": {
            "frame": {"left": 0, "top": 0, "width": 375, "height": 1130},
            "layers": [
                {
                    "name": "Robot Icon",
                    "type": "groupLayer",
                    "frame": {"left": 15, "top": 939, "width": 40, "height": 44},
                    "image": {
                        "imageUrl": "https://cdn.example.com/robot.png",
                        "svgUrl": "https://cdn.example.com/robot.svg",
                    },
                    "layers": [
                        {
                            "name": "Ellipse 426",
                            "type": "shapeLayer",
                            "frame": {"left": 17, "top": 945, "width": 38, "height": 38},
                        },
                    ],
                },
            ],
        },
    }

    html, image_mapping, annotations = convert_sketch_to_html(sketch_data, 1.0)

    # 带 image 字段的编组不再被展开成子层
    assert [annotation["name"] for annotation in annotations] == ["Robot Icon"]
    # 输出为 <img> 且 SVG/PNG 双版本进入映射表
    assert "<img" in html
    assert "robot.svg" in html
    assert "./assets/slices/Robot_Icon.svg" in image_mapping
    assert "./assets/slices/Robot_Icon.png" in image_mapping
    assert annotations[0].get("svg_url") == "https://cdn.example.com/robot.svg"
    assert annotations[0].get("png_url") == "https://cdn.example.com/robot.png"
