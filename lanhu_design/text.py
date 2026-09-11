"""Expose source text runs and font dependencies without guessing typography.

Sketch's string ranges count UTF-16 code units, not Python characters. Source
order, invalid ranges, overlapping runs and raw properties remain visible; this
module does not choose a winning style or manufacture missing font weights.
"""

from __future__ import annotations

import copy
import math
import re


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        result = float(value)
    except (ValueError, OverflowError):
        return None
    if not math.isfinite(result):
        return None
    return int(result) if result.is_integer() else result


def _offset(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str):
        # Preserve integer precision; offsets are not CSS dimensions or bytes.
        if not re.fullmatch(r"[0-9]+", value.strip()):
            return None
        try:
            return int(value)
        except ValueError:
            return None
    if isinstance(value, float) and math.isfinite(value) and value.is_integer() and value >= 0:
        return int(value)
    return None


def _style(source, pointer):
    result = {"font_family": None, "font_size": None, "font_weight": None,
              "color": None, "line_height": None, "letter_spacing": None,
              "source_fields": {}}
    # A source name can be a PostScript face, e.g. Example-Semibold. Keep it
    # intact instead of pretending it is an installed CSS family plus weight.
    for key in ("fontFamily", "fontName", "font"):
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            result["font_family"] = value
            result["font_name_kind"] = "source_name"
            result["source_fields"]["font_family"] = f"{pointer}/{key}"
            break
    numeric_fields = {
        "font_size": ("fontSize", "size"),
        "font_weight": ("fontWeight", "weight"),
        "line_height": ("lineHeight", "line"),
        "letter_spacing": ("letterSpacing", "kern", "kerning"),
        "paragraph_spacing": ("paragraphSpacing",),
        "paragraph_spacing_before": ("paragraphSpacingBefore",),
    }
    for target, candidates in numeric_fields.items():
        for key in candidates:
            value = _number(source.get(key))
            if value is not None:
                result[target] = value
                result["source_fields"][target] = f"{pointer}/{key}"
                break
    if result["font_weight"] is None:
        for key in ("fontWeight", "weight"):
            if isinstance(source.get(key), str) and source[key].strip():
                result["font_weight"] = source[key]
                result["source_fields"]["font_weight"] = f"{pointer}/{key}"
                break
    color = source.get("color")
    color_pointer = f"{pointer}/color"
    if isinstance(color, dict):
        # Real exports may have all-zero numeric channels alongside a valid
        # value string. Do not regenerate a transparent black CSS color.
        color = color.get("value")
        color_pointer += "/value"
    if isinstance(color, str) and color.strip():
        result["color"] = color
        result["source_fields"]["color"] = color_pointer
    for target, key in (("text_align", "align"), ("alignment_code", "alignment"),
                        ("decoration_line", "decorationLine"), ("display_name", "displayName")):
        if key in source:
            result[target] = copy.deepcopy(source[key])
            result["source_fields"][target] = f"{pointer}/{key}"
    return result


def text_spec(node: dict) -> dict:
    """Read normalized ``text`` and ``raw_style.font.styles`` without network I/O.

    Every input style produces one output run, including malformed entries.
    Invalid range text is ``None`` (never clipped or reinterpreted); raw source
    content remains in ``raw_style``. A font requirement records a source name,
    not a claim about local installation, licensing, downloadability or CSS
    family resolution. Missing styles are reported instead of synthesizing runs.
    """
    if not isinstance(node, dict):
        raise TypeError("A normalized design node must be a dictionary")
    result = {"text_runs": [], "font_requirements": [], "gaps": []}
    text = node.get("text")
    raw = node.get("raw_style")
    font = raw.get("font") if isinstance(raw, dict) else None
    if not isinstance(text, str) and font is None:
        return result  # Ordinary shapes are not missing text specifications.

    pointer = str(node.get("source_pointer") or "") + "/font"

    def gap(code, source_pointer=pointer, **evidence):
        result["gaps"].append({"code": code, "node_id": node.get("node_id"),
                               "source_pointer": source_pointer, **evidence})

    result["raw_font"] = copy.deepcopy(font)
    if not isinstance(font, dict):
        gap("missing_text_styles" if font is None else "invalid_font_source")
        return result
    result["base_style"] = _style(font, pointer)
    result["base_style"]["source_pointer"] = pointer
    if not isinstance(text, str):
        gap("missing_text_content")
    elif isinstance(font.get("content"), str) and font["content"] != text:
        gap("text_content_source_mismatch")

    # Unit positions map only to complete Unicode characters. Astral characters
    # occupy two UTF-16 units and cannot be split into separate Python slices.
    boundaries = {0: 0}
    text_units = 0
    if isinstance(text, str):
        for index, char in enumerate(text):
            text_units += 2 if ord(char) > 0xFFFF else 1
            boundaries[text_units] = index + 1
        if any(0xD800 <= ord(char) <= 0xDFFF for char in text):
            gap("unpaired_surrogate_in_text")
    result["text_length_utf16"] = text_units if isinstance(text, str) else None

    requirements = {}

    def add_font(style, source_pointer):
        family = style.get("font_family")
        if family is None:
            return
        requirement = requirements.setdefault(family, {
            "family": family, "name_kind": "source_name", "source": "design",
            "availability": "not_checked", "source_pointers": [],
        })
        if source_pointer not in requirement["source_pointers"]:
            requirement["source_pointers"].append(source_pointer)
        weight = style.get("font_weight")
        if weight is not None:
            weights = requirement.setdefault("weights", [])
            if weight not in weights:
                weights.append(weight)

    add_font(result["base_style"], pointer)
    styles = font.get("styles")
    if not isinstance(styles, list):
        gap("missing_text_styles" if styles is None else "invalid_text_styles", pointer + "/styles")
        styles = []
    elif not styles and text:
        gap("missing_text_styles", pointer + "/styles")
    intervals = []
    seen = {}
    for index, source in enumerate(styles):
        run_pointer = f"{pointer}/styles/{index}"
        run = {"start": None, "length": None, "offset_unit": "utf16", "text": None,
               "source_pointer": run_pointer, "raw_style": copy.deepcopy(source)}
        run.update(_style(source if isinstance(source, dict) else {}, run_pointer))
        result["text_runs"].append(run)
        if not isinstance(source, dict):
            gap("invalid_text_style", run_pointer)
            continue
        add_font(run, run_pointer)
        missing = [key for key in ("font_family", "font_size", "color", "line_height")
                   if run[key] is None]
        if missing:
            gap("missing_text_style_properties", run_pointer, properties=missing)
        start, length = _offset(source.get("location")), _offset(source.get("length"))
        run["start"], run["length"] = start, length
        if start is None or length is None:
            gap("invalid_text_range", run_pointer)
            continue
        end = start + length
        if (start, end) in seen:
            gap("duplicate_text_range", run_pointer, other_source_pointer=seen[(start, end)])
        else:
            seen[(start, end)] = run_pointer
        if not isinstance(text, str):
            continue
        if end > text_units or start > text_units:
            gap("text_range_out_of_bounds", run_pointer, start=start, length=length,
                text_length_utf16=text_units)
            continue
        if start not in boundaries or end not in boundaries:
            gap("text_range_splits_surrogate_pair", run_pointer, start=start, length=length)
            continue
        run["text"] = text[boundaries[start]:boundaries[end]]
        if isinstance(source.get("content"), str) and source["content"] != run["text"]:
            gap("text_run_content_mismatch", run_pointer)
        if length:
            for other_start, other_end, other_pointer in intervals:
                if start < other_end and end > other_start:
                    gap("overlapping_text_ranges", run_pointer, other_source_pointer=other_pointer)
            intervals.append((start, end, run_pointer))

    if isinstance(text, str):
        covered_until = 0
        for start, end, _ in sorted(intervals):
            if start > covered_until:
                gap("uncovered_text_range", start=covered_until, length=start - covered_until,
                    offset_unit="utf16")
            covered_until = max(covered_until, end)
        if covered_until < text_units:
            gap("uncovered_text_range", start=covered_until, length=text_units - covered_until,
                offset_unit="utf16")
    result["font_requirements"] = list(requirements.values())
    return result
