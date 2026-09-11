"""Synthetic typography contracts; no customer text or downloaded fonts."""

from copy import deepcopy

import pytest

from lanhu_design.text import text_spec


def _run(start, length, **style):
    return {"location": str(start), "length": str(length), "font": "ExampleSans-Regular",
            "size": "18", "line": 25, "color": {"value": "rgba(102,102,102,1)",
            "r": 0, "g": 0, "b": 0, "a": 0}, **style}


def _node(text, styles, **font):
    return {"node_id": "synthetic-label", "source_pointer": "/info/2", "text": text,
            "raw_style": {"font": {"styles": styles, **font}}}


def _codes(result):
    return {gap["code"] for gap in result["gaps"]}


def test_seven_runs_preserve_color_size_provenance_and_source_order():
    chunks = ["说明", "《甲》", "继续", "《乙》", "阅读", "《丙》", "结束"]
    cursor = 0
    styles = []
    for index, chunk in enumerate(chunks):
        styles.append(_run(cursor, len(chunk), content=chunk, size=str(18 + index),
                           color={"value": "#ff730a" if index % 2 else "#666666",
                                  "r": 0, "g": 0, "b": 0, "a": 0}))
        cursor += len(chunk)
    result = text_spec(_node("".join(chunks), styles))
    assert [run["text"] for run in result["text_runs"]] == chunks
    assert [run["font_size"] for run in result["text_runs"]] == list(range(18, 25))
    assert result["text_runs"][1]["color"] == "#ff730a"
    assert result["text_runs"][1]["source_pointer"] == "/info/2/font/styles/1"
    assert result["text_runs"][1]["source_fields"]["color"] == "/info/2/font/styles/1/color/value"
    assert result["text_runs"][1]["raw_style"] == styles[1]
    assert result["gaps"] == []


def test_utf16_ranges_handle_emoji_zwj_chinese_newlines_and_combining_marks():
    chunks = ["中", "😀", "👩‍💻", "\n", "e\u0301", "文"]
    styles = []
    cursor = 0
    for chunk in chunks:
        units = len(chunk.encode("utf-16-le")) // 2
        styles.append(_run(cursor, units, content=chunk))
        cursor += units
    result = text_spec(_node("".join(chunks), styles))
    assert [run["text"] for run in result["text_runs"]] == chunks
    assert [run["start"] for run in result["text_runs"]] == [0, 1, 3, 8, 9, 11]
    assert result["text_length_utf16"] == 12
    assert all(run["offset_unit"] == "utf16" for run in result["text_runs"])
    assert result["gaps"] == []


def test_partial_emoji_range_is_rejected_without_replacement_or_reinterpreting():
    result = text_spec(_node("A😀B", [_run(1, 1), _run(2, 1), _run(3, 1)]))
    assert [run["text"] for run in result["text_runs"]] == [None, None, "B"]
    assert "text_range_splits_surrogate_pair" in _codes(result)
    assert "uncovered_text_range" in _codes(result)


def test_fonts_use_explicit_weights_only_and_report_availability_as_unknown():
    result = text_spec(_node("¥28", [_run(0, 1, size="8"),
                                    _run(1, 2, font="ExampleSans-Semibold", size="12")],
                             font="ExampleSans-Regular"))
    assert [run["font_size"] for run in result["text_runs"]] == [8, 12]
    assert all(run["font_weight"] is None for run in result["text_runs"])
    assert {f["family"] for f in result["font_requirements"]} == {
        "ExampleSans-Regular", "ExampleSans-Semibold"}
    assert all(f["availability"] == "not_checked" and f["source"] == "design"
               and "weights" not in f for f in result["font_requirements"])
    weighted = text_spec(_node("ab", [_run(0, 1, fontWeight="400"), _run(1, 1, fontWeight=700)]))
    assert weighted["font_requirements"][0]["weights"] == [400, 700]
    assert len(weighted["font_requirements"][0]["source_pointers"]) == 2


def test_duplicate_overlap_and_out_of_bounds_styles_are_retained_with_gaps():
    styles = [_run(1, 2), _run(1, 2), _run(2, 2), _run(4, 3)]
    result = text_spec(_node("abcde", styles))
    assert len(result["text_runs"]) == 4
    assert [run["raw_style"] for run in result["text_runs"]] == styles
    assert [run["text"] for run in result["text_runs"]] == ["bc", "bc", "cd", None]
    assert {"duplicate_text_range", "overlapping_text_ranges", "text_range_out_of_bounds",
            "uncovered_text_range"} <= _codes(result)


@pytest.mark.parametrize("offset", [True, False, -1, "-1", "1.5", "nan", float("inf"), {}, None])
def test_invalid_offsets_do_not_silently_become_zero_or_get_truncated(offset):
    result = text_spec(_node("abc", [_run(offset, 1, location=offset)]))
    assert result["text_runs"][0]["start"] is None
    assert result["text_runs"][0]["text"] is None
    assert "invalid_text_range" in _codes(result)


def test_huge_integer_offset_retains_precision_and_is_reported_out_of_bounds():
    position = 10 ** 30 + 1
    result = text_spec(_node("x", [_run(position, 1)]))
    assert result["text_runs"][0]["start"] == position
    assert "text_range_out_of_bounds" in _codes(result)


def test_missing_style_properties_are_not_filled_from_another_run_or_base_style():
    result = text_spec(_node("ab", [{"location": "0", "length": "1"}, _run(1, 1)],
                             font="BaseFont", size=30, line=36, color={"value": "red"}))
    first = result["text_runs"][0]
    assert all(first[key] is None for key in ("font_family", "font_size", "color", "line_height"))
    assert result["base_style"]["font_family"] == "BaseFont"
    assert "missing_text_style_properties" in _codes(result)


def test_source_content_mismatches_do_not_override_canonical_text():
    result = text_spec(_node("AB", [_run(0, 2, content="xy")], content="wrong"))
    assert result["text_runs"][0]["text"] == "AB"
    assert result["text_runs"][0]["raw_style"]["content"] == "xy"
    assert {"text_run_content_mismatch", "text_content_source_mismatch"} <= _codes(result)


def test_no_styles_or_unsupported_text_format_does_not_invent_a_run():
    result = text_spec(_node("text", [], font="ExampleFont"))
    assert result["text_runs"] == []
    assert result["font_requirements"][0]["family"] == "ExampleFont"
    assert {"missing_text_styles", "uncovered_text_range"} <= _codes(result)
    unsupported = text_spec({"text": "text", "raw_style": {"text": {"style": {"fontSize": 18}}}})
    assert unsupported["text_runs"] == []
    assert "missing_text_styles" in _codes(unsupported)
    assert text_spec({"text": None}) == {"text_runs": [], "font_requirements": [], "gaps": []}


def test_invalid_style_entries_and_unknown_fields_are_preserved_without_mutation():
    original = _node("ab", [None, "invalid", _run(0, 2, futureField={"nested": [1]})])
    before = deepcopy(original)
    result = text_spec(original)
    assert original == before
    assert len(result["text_runs"]) == 3
    assert result["text_runs"][0]["raw_style"] is None
    assert result["text_runs"][1]["raw_style"] == "invalid"
    assert "invalid_text_style" in _codes(result)
    result["text_runs"][2]["raw_style"]["futureField"]["nested"].append(2)
    assert original == before


def test_empty_text_and_zero_length_styles_are_valid():
    result = text_spec(_node("", [_run(0, 0)]))
    assert result["text_runs"][0]["text"] == ""
    assert result["gaps"] == []


def test_numeric_strings_preserve_zero_and_fractional_typography_values():
    result = text_spec(_node("x", [_run(0, 1, size="12.5", line="0", kern="-0.25",
                                              paragraphSpacing="0", fontWeight="600")]))
    run = result["text_runs"][0]
    assert (run["font_size"], run["line_height"], run["letter_spacing"], run["paragraph_spacing"],
            run["font_weight"]) == (12.5, 0, -0.25, 0, 600)


def test_nonfinite_style_numbers_are_not_exposed_as_normalized_dimensions():
    result = text_spec(_node("x", [_run(0, 1, size="nan", line=float("inf"), kern=True)]))
    run = result["text_runs"][0]
    assert run["font_size"] is None and run["line_height"] is None and run["letter_spacing"] is None
    assert "missing_text_style_properties" in _codes(result)
