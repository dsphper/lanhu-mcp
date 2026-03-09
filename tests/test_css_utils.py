"""Tests for design CSS helper utilities."""

from lanhu_mcp_server import _camel_to_kebab, _format_css_value, _merge_padding


def test_camel_to_kebab_basic():
    assert _camel_to_kebab("fontSize") == "font-size"
    assert _camel_to_kebab("backgroundColor") == "background-color"


def test_format_css_value_unit_handling():
    assert _format_css_value("fontSize", 14) == "14px"
    assert _format_css_value("zIndex", 3) == "3"
    assert _format_css_value("opacity", 0) == "0"


def test_format_css_value_numeric_string_handling():
    assert _format_css_value("lineHeight", "24") == "24px"
    assert _format_css_value("zIndex", "24") == "24"


def test_merge_padding_compacts_to_shorthand():
    styles = {
        "paddingTop": 8,
        "paddingRight": 12,
        "paddingBottom": 8,
        "paddingLeft": 12,
    }

    _merge_padding(styles)

    assert styles["padding"] == "8px 12px"
    assert "paddingTop" not in styles
    assert "paddingRight" not in styles
    assert "paddingBottom" not in styles
    assert "paddingLeft" not in styles
