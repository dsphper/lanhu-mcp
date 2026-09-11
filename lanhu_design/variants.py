"""Select existing source asset variants without converting or guessing image bytes.

Variant identity comes from the node-backed asset ID and source field, never a
layer name, list position, or expiring URL. The downloader remains authoritative
for the actual format and pixel dimensions.
"""

from copy import deepcopy
import hashlib
import json
from urllib.parse import urlsplit


_RASTER_FORMATS = {"png", "jpeg", "webp", "gif", "avif", "bmp", "tiff", "ico"}
_PREFERENCES = {"original", "prefer_svg", "raster"}
_OMIT = object()


class VariantSelectionError(ValueError):
    """A source cannot satisfy the requested variant policy."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _normalize_format(value) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip().lower().removeprefix("image/")
    return {"jpg": "jpeg", "svg+xml": "svg", "tif": "tiff"}.get(value, value)


def _hint(variant: dict) -> str | None:
    hint = _normalize_format(variant.get("format_hint"))
    field = str(variant.get("source_field", "")).lower().rsplit(".", 1)[-1]
    if hint == "svg" or field in {"svg", "svgurl", "svg_url"}:
        return "svg"
    if hint:
        return hint
    # Extensionless imageUrl values are common. They stay unknown until fetched.
    try:
        suffix = urlsplit(variant.get("url", "")).path.lower().rsplit(".", 1)[-1]
    except (TypeError, ValueError):
        return None
    suffix = {"jpg": "jpeg", "tif": "tiff"}.get(suffix, suffix)
    return suffix if suffix in _RASTER_FORMATS | {"svg"} else None


def _catalog(asset: dict) -> tuple[str, list[dict], dict]:
    base_id = asset.get("base_asset_id") or asset.get("asset_id")
    if not isinstance(base_id, str) or not base_id:
        raise VariantSelectionError("InvalidAssetVariants", "Asset must have a nonempty asset_id.")
    supplied = asset.get("variants") or []
    if not isinstance(supplied, list):
        raise VariantSelectionError("InvalidAssetVariants", "Asset variants must be a list.")
    raw_variants = deepcopy(supplied)
    original_url = asset.get("url")
    if not raw_variants or (original_url and not any(
        isinstance(item, dict) and item.get("url") == original_url for item in raw_variants
    )):
        raw_variants.append({"url": original_url, "source_field": asset.get("source_field"),
                             "format_hint": asset.get("format_hint")})
    variants = {}
    for variant in raw_variants:
        if not isinstance(variant, dict):
            raise VariantSelectionError("InvalidAssetVariants", "Each source variant must be an object.")
        field = variant.get("source_field") or asset.get("source_field")
        url = variant.get("url")
        if not isinstance(field, str) or not field or not isinstance(url, str) or not url:
            raise VariantSelectionError("InvalidAssetVariants", "Each source variant needs a source field and URL.")
        hint = _hint(variant)
        identity = json.dumps([base_id, field, hint], ensure_ascii=False, separators=(",", ":"))
        variant_id = "v-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
        previous = variants.get(variant_id)
        if previous and previous["url"] != url:
            raise VariantSelectionError(
                "InvalidAssetVariants", "Multiple source URLs share one variant identity; selection is ambiguous."
            )
        variants[variant_id] = {"variant_id": variant_id, "source_field": field,
                                "format_hint": hint, "url": url}
    ordered = sorted(variants.values(), key=lambda item: (item["source_field"], item["variant_id"]))
    # Preserve the default chosen by normalization even if the list was reordered.
    original = next((item for item in ordered if item["variant_id"] == asset.get("original_variant_id")), None)
    original = original or next((item for item in ordered if item["url"] == original_url), None)
    if original is None:
        original = next((item for item in ordered if item["source_field"].rsplit(".", 1)[-1] == "imageUrl"), ordered[0])
    return base_id, ordered, original


def _without_urls(value):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if str(key).lower().endswith(("url", "urls")):
                continue
            clean = _without_urls(item)
            if clean is not _OMIT:
                result[key] = clean
        return result
    if isinstance(value, list):
        return [clean for item in value if (clean := _without_urls(item)) is not _OMIT]
    if isinstance(value, str) and value.lstrip().lower().startswith(("http://", "https://", "//")):
        return _OMIT
    return deepcopy(value)


def public_asset(asset: dict) -> dict:
    """Expose source choices and geometry while keeping signed URLs private."""
    _, variants, original = _catalog(asset)
    result = _without_urls(asset)
    result["variants"] = [
        {"variant_id": item["variant_id"], "source_field": item["source_field"],
         "format_hint": item["format_hint"], "is_original": item["variant_id"] == original["variant_id"],
         "format_verification": "requires_download"}
        for item in variants
    ]
    return result


def validate_downloaded_variant(selected: dict, decoded: dict) -> None:
    """Check decoded bytes against the selected source and requested policy.

    Source metadata is a claim, not proof of a file's format. Unknown imageUrl
    sources remain format-neutral; only decoded bytes establish their format.
    Call this before admitting a downloaded or cached file to an export bundle.
    """
    actual = _normalize_format(decoded.get("format"))
    is_vector = decoded.get("is_vector")
    expected = _hint({
        "format_hint": selected.get("selected_format_hint", selected.get("format_hint")),
        "source_field": selected.get("selected_source_field", selected.get("source_field")),
    })

    def mismatch(message: str) -> None:
        raise VariantSelectionError("DownloadedVariantMismatch", message)

    if selected.get("requested_preference") == "raster" and (is_vector or actual == "svg"):
        mismatch("Raster was requested but the downloaded source is SVG; no conversion was performed.")
    if expected == "svg" and (actual != "svg" or is_vector is not True):
        mismatch("The selected source declares SVG but the downloaded bytes are not SVG.")
    if expected in _RASTER_FORMATS and (actual != expected or is_vector is not False):
        mismatch(f"The selected source declares {expected} but the downloaded bytes have a different format.")
    if actual not in _RASTER_FORMATS | {"svg"} or is_vector is not (actual == "svg"):
        mismatch("The decoded asset format metadata is missing, unsupported or inconsistent.")


def select_variants(assets: list, preference: str = "original") -> list:
    """Return copied assets pointing at a real source variant under this policy.

    ``original`` preserves the normalized source default. ``prefer_svg`` selects
    a supplied SVG, falling back explicitly to the original when absent.
    ``raster`` chooses a non-SVG image source, permitting unknown format hints
    such as extensionless imageUrl; the downloader must inspect its bytes.
    """
    if not isinstance(preference, str) or preference not in _PREFERENCES:
        raise VariantSelectionError("InvalidFormatPreference", "Select original, prefer_svg or raster.")
    result = []
    for asset in assets:
        if not isinstance(asset, dict):
            raise VariantSelectionError("InvalidAssetVariants", "Each asset must be an object.")
        base_id, variants, original = _catalog(asset)
        selected, fallback = original, None
        if preference == "prefer_svg":
            choices = [item for item in variants if item["format_hint"] == "svg"]
            if choices:
                selected = original if original in choices else choices[0]
            else:
                fallback = "svg_unavailable_using_original"
        elif preference == "raster":
            choices = [item for item in variants if item["format_hint"] in _RASTER_FORMATS | {None}]
            if not choices:
                raise VariantSelectionError("NoRasterVariant", "Asset has no source raster variant; no conversion was performed.")
            selected = original if original in choices else choices[0]
        copied = deepcopy(asset)
        copied.update({
            "asset_id": base_id if selected == original else f"{base_id}#variant={selected['variant_id']}",
            "base_asset_id": base_id,
            "url": selected["url"],
            "format_hint": selected["format_hint"],
            "original_variant_id": original["variant_id"],
            "requested_preference": preference,
            "selected_variant_id": selected["variant_id"],
            "selected_format_hint": selected["format_hint"],
            "selected_source_field": selected["source_field"],
            "selection_fallback": fallback,
        })
        result.append(copied)
    return result
