"""Source variants retain identity across renames, ordering and signed URLs."""

from copy import deepcopy
from io import BytesIO
import json

import pytest
from PIL import Image

from lanhu_design.media import _inspect_asset
from lanhu_design.normalize import normalize_design
from lanhu_design.variants import (
    VariantSelectionError, public_asset, select_variants, validate_downloaded_variant,
)


def _asset():
    return {
        "asset_id": "node:image", "node_id": "node", "source_field": "image",
        "url": "https://cdn.example.test/item.png?signature=private-png", "format_hint": "png",
        "render_bounds": {"x": 11, "y": 12, "width": 20, "height": 30},
        "variants": [
            {"url": "https://cdn.example.test/item.png?signature=private-png",
             "format_hint": "png", "source_field": "image.imageUrl"},
            {"url": "https://cdn.example.test/item.svg?signature=private-svg",
             "format_hint": "svg", "source_field": "image.svgUrl"},
        ],
    }


def test_png_and_svg_select_actual_sources_with_distinct_cache_identities():
    asset = _asset()
    original, = select_variants([asset])
    raster, = select_variants([asset], "raster")
    vector, = select_variants([asset], "prefer_svg")
    assert original["asset_id"] == raster["asset_id"] == asset["asset_id"]
    assert original["url"] == raster["url"] == asset["url"]
    assert vector["asset_id"] != asset["asset_id"]
    assert vector["base_asset_id"] == asset["asset_id"]
    assert vector["url"] == asset["variants"][1]["url"]
    assert vector["selected_format_hint"] == "svg"
    assert vector["selected_source_field"] == "image.svgUrl"
    assert vector["selected_variant_id"] != original["selected_variant_id"]
    assert all(item["selection_fallback"] is None for item in [original, raster, vector])
    assert vector["requested_preference"] == "prefer_svg"


def test_svg_only_preserves_original_and_rejects_raster_without_conversion():
    asset = _asset()
    asset["variants"] = [asset["variants"][1]]
    asset.update(url=asset["variants"][0]["url"], format_hint="svg")
    original, = select_variants([asset])
    vector, = select_variants([asset], "prefer_svg")
    assert original["asset_id"] == vector["asset_id"] == asset["asset_id"]
    with pytest.raises(VariantSelectionError, match="no source raster variant") as error:
        select_variants([asset], "raster")
    assert error.value.code == "NoRasterVariant"


def test_extensionless_original_remains_unknown_and_svg_fallback_is_explicit():
    asset = _asset()
    asset["variants"] = [dict(asset["variants"][0], url="https://cdn.example.test/object?signature=secret", format_hint=None)]
    asset.update(url=asset["variants"][0]["url"], format_hint=None)
    raster, = select_variants([asset], "raster")
    fallback, = select_variants([asset], "prefer_svg")
    assert raster["selected_format_hint"] is None
    assert raster["format_hint"] is None
    assert raster["url"] == asset["url"]
    assert fallback["selected_variant_id"] == raster["selected_variant_id"]
    assert fallback["selection_fallback"] == "svg_unavailable_using_original"
    assert fallback["asset_id"] == asset["asset_id"]


@pytest.mark.parametrize("hint,field,url", [
    ("svg", "image.other", "https://cdn.example.test/object"),
    (None, "image.svgUrl", "https://cdn.example.test/object"),
    (None, "image.svg", "https://cdn.example.test/object"),
    (None, "image.other", "https://cdn.example.test/object.svg?token=private"),
])
def test_svg_source_evidence_does_not_require_a_url_extension(hint, field, url):
    asset = _asset()
    asset["variants"][1] = {"format_hint": hint, "source_field": field, "url": url}
    vector, = select_variants([asset], "prefer_svg")
    assert vector["url"] == url
    assert vector["selected_format_hint"] == "svg"


def test_variant_order_url_signatures_and_layer_names_do_not_change_ids():
    before = _asset()
    after = deepcopy(before)
    after["name"] = "编组123"
    after["variants"].reverse()
    for item in after["variants"]:
        item["url"] = item["url"].split("?")[0] + "?signature=refreshed"
    after["url"] = before["url"].split("?")[0] + "?signature=refreshed"
    for preference in ["original", "prefer_svg", "raster"]:
        old, = select_variants([before], preference)
        new, = select_variants([after], preference)
        assert old["asset_id"] == new["asset_id"]
        assert old["selected_variant_id"] == new["selected_variant_id"]


def test_normalized_asset_rename_retains_export_identity():
    layer = {"id": "button", "name": "领取", "exportable": True,
             "image": {"imageUrl": "https://cdn.example.test/a.png", "svgUrl": "https://cdn.example.test/a.svg"}}
    before = normalize_design({"info": [layer]})["assets"]
    layer["name"] = "矩形备份2"
    after = normalize_design({"info": [layer]})["assets"]
    assert select_variants(before, "prefer_svg") == select_variants(after, "prefer_svg")


@pytest.mark.parametrize("preference", ["png", "SVG", "", None, [], 2])
def test_invalid_preference_has_a_stable_error_code(preference):
    with pytest.raises(VariantSelectionError) as error:
        select_variants([_asset()], preference)
    assert error.value.code == "InvalidFormatPreference"


def test_public_metadata_exposes_choices_without_signed_urls():
    asset = _asset()
    asset["source_evidence"] = {"imageUrl": asset["url"], "nested": [{"source_url": asset["url"]}],
                                "download": asset["url"], "format": "png"}
    asset["variants"][0]["unexpected_url"] = "https://cdn.example.test/private"
    public = public_asset(asset)
    text = json.dumps(public)
    assert "https://" not in text
    assert "signature" not in text
    assert "private" not in text
    assert public["asset_id"] == asset["asset_id"]
    assert public["render_bounds"] == asset["render_bounds"]
    assert {item["format_hint"] for item in public["variants"]} == {"png", "svg"}
    assert sum(item["is_original"] for item in public["variants"]) == 1
    selected, = select_variants([asset], "prefer_svg")
    assert selected["selected_variant_id"] in {item["variant_id"] for item in public["variants"]}


def test_selection_and_public_metadata_are_deep_copies():
    asset = _asset()
    saved = deepcopy(asset)
    selected, = select_variants([asset], "prefer_svg")
    public = public_asset(asset)
    selected["render_bounds"]["x"] = -100
    selected["variants"][0]["source_field"] = "changed"
    public["render_bounds"]["width"] = 999
    assert asset == saved


def test_old_asset_without_variants_uses_its_existing_source():
    asset = _asset()
    del asset["variants"]
    selected, = select_variants([asset], "prefer_svg")
    assert selected["url"] == asset["url"]
    assert selected["asset_id"] == asset["asset_id"]
    assert selected["selection_fallback"] == "svg_unavailable_using_original"
    assert len(public_asset(asset)["variants"]) == 1


def test_reselecting_an_asset_does_not_change_its_original_identity():
    asset = _asset()
    vector, = select_variants([asset], "prefer_svg")
    original, = select_variants([vector], "original")
    assert original["asset_id"] == asset["asset_id"]
    assert original["url"] == asset["url"]
    assert [item["is_original"] for item in public_asset(vector)["variants"]] == [True, False]


def test_ambiguous_source_identity_fails_instead_of_using_list_position():
    asset = _asset()
    asset["variants"].append(dict(asset["variants"][1], url="https://cdn.example.test/different.svg"))
    with pytest.raises(VariantSelectionError) as error:
        select_variants([asset], "prefer_svg")
    assert error.value.code == "InvalidAssetVariants"


def test_non_svg_raster_source_is_not_assumed_png():
    asset = _asset()
    asset["variants"][0].update(url="https://cdn.example.test/item.webp", format_hint="webp")
    asset.update(url=asset["variants"][0]["url"], format_hint="webp")
    selected, = select_variants([asset], "raster")
    assert selected["selected_format_hint"] == "webp"
    assert selected["url"].endswith(".webp")


def _decoded(format):
    if format == "SVG":
        return _inspect_asset(b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>')
    buffer = BytesIO()
    Image.new("RGB", (10, 10), "red").save(buffer, format=format)
    return _inspect_asset(buffer.getvalue())


def _unknown_asset():
    asset = _asset()
    asset["variants"] = [dict(asset["variants"][0], url="https://cdn.example.test/object", format_hint=None)]
    asset.update(url=asset["variants"][0]["url"], format_hint=None)
    return asset


def test_extensionless_raster_selection_rejects_svg_bytes():
    selected, = select_variants([_unknown_asset()], "raster")
    assert selected["selected_format_hint"] is None
    with pytest.raises(VariantSelectionError, match="Raster was requested") as error:
        validate_downloaded_variant(selected, _decoded("SVG"))
    assert error.value.code == "DownloadedVariantMismatch"


@pytest.mark.parametrize("preference", ["original", "prefer_svg"])
def test_svg_selection_rejects_png_bytes(preference):
    asset = _asset()
    asset["variants"] = [asset["variants"][1]]
    asset.update(url=asset["variants"][0]["url"], format_hint="svg")
    selected, = select_variants([asset], preference)
    with pytest.raises(VariantSelectionError, match="declares SVG") as error:
        validate_downloaded_variant(selected, _decoded("PNG"))
    assert error.value.code == "DownloadedVariantMismatch"


def test_explicit_svg_source_field_is_validated_even_without_format_hint():
    selected, = select_variants([_asset()], "prefer_svg")
    selected["selected_format_hint"] = None
    with pytest.raises(VariantSelectionError, match="declares SVG"):
        validate_downloaded_variant(selected, _decoded("PNG"))


@pytest.mark.parametrize("format", ["PNG", "JPEG"])
@pytest.mark.parametrize("preference", ["original", "prefer_svg", "raster"])
def test_unknown_source_accepts_actual_raster_format(format, preference):
    selected, = select_variants([_unknown_asset()], preference)
    decoded = _decoded(format)
    before = deepcopy((selected, decoded))
    assert validate_downloaded_variant(selected, decoded) is None
    assert (selected, decoded) == before
    assert selected["selected_format_hint"] is None


@pytest.mark.parametrize("hint,actual", [("png", "JPEG"), ("jpg", "PNG"), ("jpeg", "PNG"),
                                        ("webp", "PNG"), ("png", "SVG")])
def test_declared_raster_format_rejects_different_downloaded_bytes(hint, actual):
    asset = _unknown_asset()
    asset["variants"][0]["format_hint"] = hint
    asset["format_hint"] = hint
    selected, = select_variants([asset])
    with pytest.raises(VariantSelectionError, match="different format") as error:
        validate_downloaded_variant(selected, _decoded(actual))
    assert error.value.code == "DownloadedVariantMismatch"


@pytest.mark.parametrize("hint,format", [("png", "PNG"), ("jpg", "JPEG"), ("jpeg", "JPEG"),
                                      ("tif", "TIFF"), ("tiff", "TIFF"), ("webp", "WEBP"),
                                      ("image/svg+xml", "SVG")])
def test_equivalent_declared_and_decoded_formats_are_accepted(hint, format):
    asset = _unknown_asset()
    asset["variants"][0]["format_hint"] = hint
    asset["format_hint"] = hint
    selected, = select_variants([asset])
    assert validate_downloaded_variant(selected, _decoded(format)) is None


def test_unknown_original_can_be_svg_without_promising_a_raster():
    selected, = select_variants([_unknown_asset()])
    assert validate_downloaded_variant(selected, _decoded("SVG")) is None


@pytest.mark.parametrize("decoded", [{}, {"format": "png", "is_vector": True},
                                     {"format": "svg", "is_vector": False}])
def test_invalid_decoded_format_metadata_is_rejected(decoded):
    selected, = select_variants([_unknown_asset()])
    with pytest.raises(VariantSelectionError) as error:
        validate_downloaded_variant(selected, decoded)
    assert error.value.code == "DownloadedVariantMismatch"
