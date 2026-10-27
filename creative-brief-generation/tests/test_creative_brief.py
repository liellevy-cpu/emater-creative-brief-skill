import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import openpyxl
import pytest
from openpyxl.styles import PatternFill

SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "creative_brief.py"
PROJECT_DIR = SKILL_DIR.parents[1] / "projects" / "EMATER-2026-09-CreativeBriefStandardization"
_spec = importlib.util.spec_from_file_location("creative_brief", SCRIPT)
creative_brief = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(creative_brief)


def load_project_script(filename, module_name):
    spec = importlib.util.spec_from_file_location(module_name, PROJECT_DIR / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

TABS = ["Editors", "Production", "Media Buyer"]
SHARED = ["Writer", "Brief Type", "Platform", "Aspect Ratio", "Parent Serial Number", "Total Versions", "Editor Direction"]
FORBIDDEN = ["Base Ad ID", "Parent Creative", "Parent ID", "Creator Instructions", "Editing", "Ad Copy"]


def base(kind, count=2):
    return {
        "task_title": "Test Creative",
        "writer": "Test Writer",
        "brief_type": kind,
        "platform": "Meta",
        "aspect_ratio": "9:16",
        "parent_serial_number": "PARENT-100_V1",
        "total_versions": count,
        "editor_direction": "Only the supplied exception.",
        "production": {
            "concept_name": "Concept Alpha", "brief_id": "TEST-100", "product": "Test Product",
            "camera": "Phone", "orientation": "Vertical", "style": "Direct to camera",
            "movement": "Static", "setting": "Studio", "wardrobe": "Neutral", "tone": "Clear",
            "notes": "Deliver clean takes.", "master_b_roll_link": "https://example.test/master",
            "concept_b_roll": ["Pack shot", "Demonstration"],
        },
        "media_buyer": {"primary_text": "Test primary text", "ad_headline": "Test headline"},
    }


def hooks(count=2):
    return [{
        "version": f"V{i}", "copy": f"Hook copy {i}",
        "text_overlay": f"Overlay {i}", "editor_note": f"Hook note {i}",
    } for i in range(1, count + 1)]


def body_rows(count=2):
    return [{
        "line": i, "script": f"Body script {i}",
        "text_overlay": f"Body overlay {i}", "editor_note": f"Body note {i}",
    } for i in range(1, count + 1)]


def payload_for(kind, count=2):
    p = base(kind, count)
    if kind == "new-task":
        p.update({
            "parent_serial_number": "", "product": "Test Product", "generate_ai_vo": False,
            "music": "Light instrumental",
            "production_link": "https://example.test/production", "reference": "https://example.test/reference",
            "hooks": hooks(count), "body": body_rows(2),
        })
    elif kind == "policy-improvement":
        p.update({"connect_to": "Connect to source body line one.", "hooks": hooks(count), "body": body_rows(2)})
    elif kind == "hook-lead-iteration":
        p.update({"connect_to": "First unchanged source-body line.", "hooks": hooks(count)})
    elif kind == "body-improvement":
        ops = ["add", "remove", "change", "unchanged"]
        p["versions"] = [{
            "version": f"V{i}",
            "rows": [{
                "line": j, "operation": op, "script": f"{op.title()} script {i}",
                "text_overlay": f"Overlay {i}-{j}", "editor_note": f"Note {i}-{j}",
            } for j, op in enumerate(ops, 1)],
        } for i in range(1, count + 1)]
    elif kind == "mixing-task":
        p["versions"] = [{
            "version": f"V{i}",
            "rows": [
                {"line": 1, "script": f"Base script {i}", "text_overlay": "", "source": "base",
                 "source_parent_serial_number": "", "exact_source_version": "PARENT-100_V1", "editor_direction": "Retain."},
                {"line": 2, "script": f"Mix script {i}", "text_overlay": "Mix overlay", "source": "mix-in",
                 "source_parent_serial_number": "MIX200_V3", "exact_source_version": "MIX200_V3", "editor_direction": "Insert."},
                {"line": 3, "script": f"Blend script {i}", "text_overlay": "", "source": "blended",
                 "source_parent_serial_number": "", "exact_source_version": "", "editor_direction": "Use transition."},
            ],
        } for i in range(1, count + 1)]
    else:
        raise AssertionError(kind)
    return p


def rgb(cell):
    return str(cell.fill.fgColor.rgb or "")[-6:].upper()


def values(wb):
    return [c.value for ws in wb.worksheets for row in ws.iter_rows() for c in row if c.value is not None]


@pytest.mark.parametrize("kind", creative_brief.BRIEF_TYPES)
def test_all_five_generate_validate_and_have_locked_shape(tmp_path, kind):
    payload = payload_for(kind)
    out = tmp_path / f"{kind}.xlsx"
    normalized = creative_brief.generate_workbook(payload, out)
    assert creative_brief.validate_workbook(out, payload=payload)
    wb = openpyxl.load_workbook(out)
    assert wb.sheetnames == TABS
    assert [wb["Editors"].cell(r, 1).value for r in range(3, 10)] == SHARED
    assert all(ws.sheet_state == "visible" for ws in wb.worksheets)
    assert all(not d.hidden for ws in wb.worksheets for d in ws.row_dimensions.values())
    assert all(not d.hidden for ws in wb.worksheets for d in ws.column_dimensions.values())
    assert rgb(wb["Editors"]["A1"]) == "0A111E"
    assert rgb(wb["Editors"]["A3"]) == "DDEDF9"
    assert rgb(wb["Editors"]["B3"]) == "F7F9FF"
    assert normalized["brief_type"] == kind
    text = "\n".join(map(str, values(wb)))
    assert not any(term in text for term in FORBIDDEN)


@pytest.mark.parametrize("kind", creative_brief.BRIEF_TYPES)
def test_all_masters_are_clean_and_validate(tmp_path, kind):
    path = creative_brief.create_masters(tmp_path)[kind]
    creative_brief.validate_workbook(path, master=True, brief_type=kind)
    wb = openpyxl.load_workbook(path)
    assert wb.sheetnames == TABS
    assert all(wb["Editors"].cell(r, 2).value is None for r in range(3, 10))
    text = "\n".join(map(str, values(wb)))
    assert "Test Writer" not in text and "Test Product" not in text and "N/A" not in text
    layout = creative_brief.editor_layout(kind, master=True)
    if kind in ("new-task", "policy-improvement", "hook-lead-iteration"):
        assert layout["hook_start"] == layout["hook_end"]
        assert all(wb["Editors"].cell(layout["hook_start"], c).value is None for c in range(1, 5))
        if kind in ("new-task", "policy-improvement"):
            assert layout["body_start"] == layout["body_end"]
            assert all(wb["Editors"].cell(layout["body_start"], c).value is None for c in range(1, 5))
    else:
        assert len(layout["version_ranges"]) == 1
        start, end = layout["version_ranges"][0]
        assert start == end and all(wb["Editors"].cell(start, c).value is None for c in range(1, 5))


def test_new_policy_and_hook_render_text_overlay_and_correct_sections(tmp_path):
    for kind in ("new-task", "policy-improvement", "hook-lead-iteration"):
        p = payload_for(kind, 2)
        out = tmp_path / f"{kind}.xlsx"
        creative_brief.generate_workbook(p, out)
        wb = openpyxl.load_workbook(out)
        text = values(wb)
        assert "Text Overlay" in text and "Overlay 1" in text
        if kind in ("new-task", "policy-improvement"):
            assert "BODY" in text and "Body script 1" in text and "Body overlay 1" in text
        else:
            assert "BODY" not in text and "Body script 1" not in text
        if kind != "new-task":
            assert "Connect To" in text


def test_hook_rows_allow_blank_copy_for_visual_only_openers(tmp_path):
    for kind in ("new-task", "policy-improvement", "hook-lead-iteration"):
        p = payload_for(kind, 3)
        p["hooks"][0].update(copy="", text_overlay="", editor_note="Start on the slicing.")
        p["hooks"][1].update(copy="", text_overlay="raw or perfect?", editor_note="")
        out = tmp_path / f"{kind}-no-vo.xlsx"
        creative_brief.generate_workbook(p, out)
        creative_brief.validate_workbook(out, payload=p)
        ws = openpyxl.load_workbook(out)["Editors"]
        rows = {r[0]: r for r in ws.iter_rows(values_only=True) if r and r[0] in ("V1", "V2", "V3")}
        assert rows["V1"][1] is None and rows["V1"][3] == "Start on the slicing."
        assert rows["V2"][1] is None and rows["V2"][2] == "raw or perfect?"
        assert rows["V3"][1] == "Hook copy 3"


def test_hook_row_with_no_content_is_rejected():
    p = payload_for("hook-lead-iteration", 2)
    p["hooks"][0].update(copy="", text_overlay="", editor_note="")
    with pytest.raises(creative_brief.SchemaError, match="requires Copy, Text Overlay, or Editor Note"):
        creative_brief.normalize_payload(p)


def test_new_task_supports_text_overlay_only_body_rows(tmp_path):
    p = payload_for("new-task", 1)
    p["body"] = [
        {"line": 1, "script": "", "text_overlay": "30% off + free shipping — Buy Now", "editor_note": ""},
        {"line": 2, "script": "", "text_overlay": "45% off — Pre-Order", "editor_note": ""},
    ]
    out = tmp_path / "overlay-only.xlsx"
    creative_brief.generate_workbook(p, out)
    assert creative_brief.validate_workbook(out, payload=p)
    wb = openpyxl.load_workbook(out)
    layout = creative_brief.editor_layout("new-task", payload=p)
    assert wb["Editors"].cell(layout["body_start"], 2).value is None
    assert wb["Editors"].cell(layout["body_start"], 3).value == "30% off + free shipping — Buy Now"

    p["body"][0]["text_overlay"] = ""
    with pytest.raises(creative_brief.SchemaError, match="Script or Text Overlay"):
        creative_brief.generate_workbook(p, tmp_path / "empty-body-row.xlsx")


def test_new_task_keeps_unspecified_execution_fields_blank_and_has_no_details_separator(tmp_path):
    p = payload_for("new-task", 5)
    p["editor_direction"] = ""
    p["product"] = ""
    for row in p["hooks"] + p["body"]:
        row["text_overlay"] = ""
        row["editor_note"] = ""
    out = tmp_path / "new-task-unspecified-fields.xlsx"
    creative_brief.generate_workbook(p, out)
    assert creative_brief.validate_workbook(out, payload=p)
    ws = openpyxl.load_workbook(out)["Editors"]
    assert ws["B8"].value == 5
    assert ws["B8"].alignment.horizontal == "left"
    assert ws["B9"].value is None
    assert ws["A10"].value == "Product"
    assert ws["B10"].value is None
    assert "NEW TASK DETAILS" not in [cell.value for row in ws.iter_rows() for cell in row]
    assert "UGC Production?" not in [cell.value for row in ws.iter_rows() for cell in row]
    assert ws["A13"].value == "Music"
    layout = creative_brief.editor_layout("new-task", payload=p)
    assert layout["hook_start"] == 20
    assert layout["hook_end"] == 24
    assert layout["body_start"] == 28
    for row in range(layout["hook_start"], layout["hook_end"] + 1):
        assert ws.cell(row, 3).value is None
        assert ws.cell(row, 4).value is None
    for row in range(layout["body_start"], layout["body_end"] + 1):
        assert ws.cell(row, 3).value is None
        assert ws.cell(row, 4).value is None


def test_new_task_music_parent_and_voiceover_gates(tmp_path):
    p = payload_for("new-task", 1)
    p["music"] = ""
    with pytest.raises(creative_brief.SchemaError, match="music"):
        creative_brief.generate_workbook(p, tmp_path / "bad.xlsx")
    p = payload_for("new-task", 1)
    p["music"] = "Modern documentary music, no ominous cues"
    with pytest.raises(creative_brief.SchemaError, match="positively"):
        creative_brief.generate_workbook(p, tmp_path / "negative-music.xlsx")
    p = payload_for("new-task", 1)
    p["ugc_production"] = False
    with pytest.raises(creative_brief.SchemaError, match="unknown field"):
        creative_brief.generate_workbook(p, tmp_path / "ugc-row.xlsx")
    p = payload_for("new-task", 1)
    p["parent_serial_number"] = "CO100_V1"
    with pytest.raises(creative_brief.SchemaError, match="must be blank"):
        creative_brief.generate_workbook(p, tmp_path / "bad-parent.xlsx")
    p = payload_for("new-task", 1)
    p["generate_ai_vo"] = True
    with pytest.raises(creative_brief.SchemaError, match="voiceover"):
        creative_brief.generate_workbook(p, tmp_path / "bad-vo.xlsx")
    p["voiceover"] = {"accent": "US", "age": "30-40", "gender": "Female", "style": "Warm", "approved": False}
    with pytest.raises(creative_brief.SchemaError, match="approved"):
        creative_brief.generate_workbook(p, tmp_path / "bad-approval.xlsx")
    p["voiceover"]["approved"] = True
    out = tmp_path / "good.xlsx"
    creative_brief.generate_workbook(p, out)
    assert "Accent: US | Age: 30-40 | Gender: Female | Style: Warm" in values(openpyxl.load_workbook(out))


def test_ai_vo_new_task_music_defaults_blank(tmp_path):
    """Liel 2026-10-18: AI voiceover briefs leave Music blank unless specified."""
    p = payload_for("new-task", 1)
    p["generate_ai_vo"] = True
    p["voiceover"] = {"accent": "US", "age": "30s", "gender": "Male", "style": "Casual", "approved": True}
    p["music"] = ""
    out = tmp_path / "aivo-blank-music.xlsx"
    creative_brief.generate_workbook(p, out)
    assert creative_brief.validate_workbook(out, p)
    ws = openpyxl.load_workbook(out)["Editors"]
    music_rows = [r for r in range(1, ws.max_row + 1) if ws.cell(r, 1).value == "Music"]
    assert len(music_rows) == 1
    assert ws.cell(music_rows[0], 2).value in (None, "")
    # A specified AI VO music direction is still kept and still positive-only.
    p["music"] = "Warm upbeat acoustic"
    creative_brief.generate_workbook(p, tmp_path / "aivo-music.xlsx")
    assert "Warm upbeat acoustic" in values(openpyxl.load_workbook(tmp_path / "aivo-music.xlsx"))
    p["music"] = "Upbeat, not cheesy"
    with pytest.raises(creative_brief.SchemaError, match="positively"):
        creative_brief.generate_workbook(p, tmp_path / "aivo-negative.xlsx")
    # Non-AI-VO tasks still require Music.
    p = payload_for("new-task", 1)
    p["music"] = ""
    with pytest.raises(creative_brief.SchemaError, match="music"):
        creative_brief.generate_workbook(p, tmp_path / "human-blank.xlsx")


@pytest.mark.parametrize("gender", ["", "Woman", "male", None])
def test_voiceover_gender_exact(gender, tmp_path):
    p = payload_for("new-task", 1)
    p["generate_ai_vo"] = True
    p["voiceover"] = {"accent": "US", "age": "30-40", "gender": gender, "style": "Warm", "approved": True}
    with pytest.raises(creative_brief.SchemaError, match="Male/Female"):
        creative_brief.generate_workbook(p, tmp_path / "bad.xlsx")


def test_body_colors_are_on_script_and_change_is_new_only(tmp_path):
    p = payload_for("body-improvement", 1)
    out = tmp_path / "body.xlsx"
    creative_brief.generate_workbook(p, out)
    ws = openpyxl.load_workbook(out)["Editors"]
    found = {}
    for row in range(1, ws.max_row + 1):
        text = ws.cell(row, 2).value
        if isinstance(text, str) and text.lower().startswith(tuple(creative_brief.BODY_OPERATIONS)):
            found[text.split()[0].lower()] = ws.cell(row, 2)
    assert rgb(found["add"]) == "93C47D"
    assert rgb(found["remove"]) == "E06666"
    assert rgb(found["change"]) == "F6B26B"
    assert rgb(found["unchanged"]) not in {"93C47D", "E06666", "F6B26B"}
    assert all(label in values(ws.parent) for label in ["ADD", "REMOVE", "CHANGE", "UNCHANGED"])
    bad = payload_for("body-improvement", 1)
    bad["versions"][0]["rows"][2]["script"] = "OLD: bad line NEW: good line"
    with pytest.raises(creative_brief.SchemaError, match="new version only"):
        creative_brief.generate_workbook(bad, tmp_path / "bad.xlsx")


def test_mixing_markers_are_in_editor_note_and_scripts_neutral(tmp_path):
    p = payload_for("mixing-task", 1)
    p["editor_direction"] = ""
    out = tmp_path / "mix.xlsx"
    creative_brief.generate_workbook(p, out)
    creative_brief.validate_workbook(out, payload=p)
    ws = openpyxl.load_workbook(out)["Editors"]
    assert ws["B9"].value is None
    markers = []
    for row in range(1, ws.max_row + 1):
        note = ws.cell(row, 4).value
        if isinstance(note, str) and note[:1] in {"🟩", "🟥", "🟨"}:
            markers.append(note.split("\n")[0])
            assert rgb(ws.cell(row, 2)) not in {"93C47D", "E06666", "F6B26B"}
    assert markers == ["🟩 Base", "🟥 Mix-in / MIX200_V3", "🟨 Blended rewrite"]
    bad = payload_for("mixing-task", 1)
    bad["versions"][0]["rows"][0]["exact_source_version"] = ""
    with pytest.raises(creative_brief.SchemaError, match="exact_source_version"):
        creative_brief.generate_workbook(bad, tmp_path / "bad.xlsx")
    bad = payload_for("mixing-task", 1)
    bad["versions"][0]["rows"][1]["exact_source_version"] = "OTHER_V1"
    with pytest.raises(creative_brief.SchemaError, match="must equal"):
        creative_brief.generate_workbook(bad, tmp_path / "mismatch.xlsx")


def test_production_complete_and_blank_when_irrelevant(tmp_path):
    p = payload_for("policy-improvement", 1)
    p.pop("production")
    p.pop("media_buyer")
    out = tmp_path / "blank.xlsx"
    creative_brief.generate_workbook(p, out)
    wb = openpyxl.load_workbook(out)
    prod = wb["Production"]
    labels = [prod.cell(r, 1).value for r in range(1, prod.max_row + 1)]
    assert [x for x in labels if x in creative_brief.PRODUCTION_SECTIONS] == creative_brief.PRODUCTION_SECTIONS
    for label in creative_brief.PRODUCTION_VALUE_LABELS:
        row = next(r for r in range(1, prod.max_row + 1) if prod.cell(r, 1).value == label)
        assert prod.cell(row, 2).value is None
    assert "First-time creators: film all shots in the master library. Returning creators: skip this section." in labels
    assert wb["Media Buyer"]["B3"].value is None and wb["Media Buyer"]["B4"].value is None
    assert "N/A" not in values(wb)


def test_media_buyer_exact_master_layout(tmp_path):
    path = creative_brief.create_masters(tmp_path)["mixing-task"]
    ws = openpyxl.load_workbook(path)["Media Buyer"]
    assert ws["A1"].value == "Media Buyer"
    assert ws["A2"].value is None and ws["B2"].value is None
    assert ws["A3"].value == "Primary Text" and ws["B3"].value is None
    assert ws["A4"].value == "Ad Headline" and ws["B4"].value is None
    assert rgb(ws["A1"]) == "1E3F70" and rgb(ws["A3"]) == "1E3F70"
    assert ws.max_row == 4 and ws.max_column == 2


@pytest.mark.parametrize("kind", creative_brief.BRIEF_TYPES)
def test_every_owned_cell_has_visible_grid_borders(tmp_path, kind):
    path = creative_brief.create_masters(tmp_path)[kind]
    wb = openpyxl.load_workbook(path)
    for ws in wb.worksheets:
        max_col = 5 if ws.title == "Editors" else 2
        merged = list(ws.merged_cells.ranges)
        for row in range(1, ws.max_row + 1):
            for col in range(1, max_col + 1):
                cell = ws.cell(row, col)
                if any(cell.coordinate in area for area in merged):
                    continue
                for side in (cell.border.left, cell.border.right, cell.border.top, cell.border.bottom):
                    assert side.style == "thin", f"missing divider at {ws.title}!{cell.coordinate}"
                    assert str(side.color.rgb)[-6:].upper() == "B7C3D0"


def test_google_roundtrip_allows_only_blank_default_font_size_omission(tmp_path):
    path = creative_brief.create_masters(tmp_path)["new-task"]
    wb = openpyxl.load_workbook(path)
    font = copy.copy(wb["Editors"]["A2"].font)
    font.sz = None
    wb["Editors"]["A2"].font = font
    wb.save(path)
    with pytest.raises(creative_brief.ValidationError):
        creative_brief.validate_workbook(path, master=True, brief_type="new-task")
    assert creative_brief.validate_workbook(
        path, master=True, brief_type="new-task", google_roundtrip=True,
    )


def test_validator_rejects_stale_reordered_hidden_style_and_forbidden(tmp_path):
    p = payload_for("policy-improvement", 2)
    out = tmp_path / "policy.xlsx"
    creative_brief.generate_workbook(p, out)
    layout = creative_brief.editor_layout("policy-improvement", payload=creative_brief.normalize_payload(p))
    wb = openpyxl.load_workbook(out)
    wb["Editors"].cell(layout["owned_end"] + 1, 1).value = "STALE"
    wb.save(out)
    with pytest.raises(creative_brief.ValidationError): creative_brief.validate_workbook(out, payload=p)
    creative_brief.generate_workbook(p, out)
    wb = openpyxl.load_workbook(out)
    a = layout["hook_start"]
    wb["Editors"].cell(a, 1).value, wb["Editors"].cell(a + 1, 1).value = wb["Editors"].cell(a + 1, 1).value, wb["Editors"].cell(a, 1).value
    wb.save(out)
    with pytest.raises(creative_brief.ValidationError): creative_brief.validate_workbook(out, payload=p)
    creative_brief.generate_workbook(p, out)
    wb = openpyxl.load_workbook(out)
    wb["Production"].sheet_state = "hidden"
    wb["Editors"].row_dimensions[4].hidden = True
    wb["Editors"]["A1"].fill = PatternFill("solid", fgColor="FFFFFF")
    wb.save(out)
    with pytest.raises(creative_brief.ValidationError): creative_brief.validate_workbook(out, payload=p)
    for term in FORBIDDEN:
        creative_brief.generate_workbook(p, out)
        wb = openpyxl.load_workbook(out)
        wb["Editors"]["E60"] = term
        wb.save(out)
        with pytest.raises(creative_brief.ValidationError, match="forbidden"):
            creative_brief.validate_workbook(out, payload=p)


@pytest.mark.parametrize("mutation", ["column-width", "row-height", "unexpected-row-height", "freeze", "gridlines", "number-format", "border"])
def test_validator_rejects_formatting_drift(tmp_path, mutation):
    p = payload_for("new-task", 1)
    out = tmp_path / "format.xlsx"
    creative_brief.generate_workbook(p, out)
    wb = openpyxl.load_workbook(out)
    ws = wb["Editors"]
    if mutation == "column-width": ws.column_dimensions["A"].width = 99
    elif mutation == "row-height": ws.row_dimensions[1].height = 99
    elif mutation == "unexpected-row-height": ws.row_dimensions[12].height = 99
    elif mutation == "freeze": ws.freeze_panes = "B4"
    elif mutation == "gridlines": ws.sheet_view.showGridLines = True
    elif mutation == "number-format": ws["A3"].number_format = "0.00"
    else:
        from openpyxl.styles import Border, Side
        ws["A3"].border = Border(bottom=Side(style="thin", color="000000"))
    wb.save(out)
    with pytest.raises(creative_brief.ValidationError):
        creative_brief.validate_workbook(out, payload=p)
    if mutation == "unexpected-row-height":
        with pytest.raises(creative_brief.ValidationError):
            creative_brief.validate_workbook(out, payload=p, google_roundtrip=True)


def test_shorter_generation_has_no_stale_rows(tmp_path):
    out = tmp_path / "same.xlsx"
    creative_brief.generate_workbook(payload_for("hook-lead-iteration", 4), out)
    short = payload_for("hook-lead-iteration", 1)
    creative_brief.generate_workbook(short, out)
    creative_brief.validate_workbook(out, payload=short)
    text = "\n".join(map(str, values(openpyxl.load_workbook(out))))
    assert "Hook copy 1" in text and "Hook copy 2" not in text


def test_strict_schema_and_counts(tmp_path):
    p = payload_for("new-task", 1)
    p["mystery"] = "x"
    with pytest.raises(creative_brief.SchemaError, match="unknown"):
        creative_brief.generate_workbook(p, tmp_path / "bad.xlsx")
    p = payload_for("new-task", 1)
    p["writer"] = ""
    with pytest.raises(creative_brief.SchemaError, match="writer"):
        creative_brief.generate_workbook(p, tmp_path / "bad2.xlsx")
    p = payload_for("new-task", 1)
    p["total_versions"] = 2
    with pytest.raises(creative_brief.SchemaError, match="total_versions"):
        creative_brief.generate_workbook(p, tmp_path / "bad3.xlsx")
    for invalid in (1.0, True):
        p = payload_for("new-task", 1)
        p["total_versions"] = invalid
        with pytest.raises(creative_brief.SchemaError, match="positive integer"):
            creative_brief.generate_workbook(p, tmp_path / "bad-total.xlsx")
    p = payload_for("new-task", 1)
    p["connect_to"] = "irrelevant"
    with pytest.raises(creative_brief.SchemaError, match="unknown"):
        creative_brief.generate_workbook(p, tmp_path / "irrelevant.xlsx")
    p = payload_for("policy-improvement", 1)
    p["music"] = "No Music"
    with pytest.raises(creative_brief.SchemaError, match="unknown"):
        creative_brief.generate_workbook(p, tmp_path / "irrelevant-policy.xlsx")
    p = payload_for("policy-improvement", 1)
    p["production"]["camera"] = "N/A"
    with pytest.raises(creative_brief.SchemaError, match="blank rather than N/A"):
        creative_brief.generate_workbook(p, tmp_path / "na.xlsx")
    p = payload_for("policy-improvement", 1)
    p["production"]["notes"] = "This field is n / a today"
    with pytest.raises(creative_brief.SchemaError, match="blank rather than N/A"):
        creative_brief.generate_workbook(p, tmp_path / "na-phrase.xlsx")
    p = payload_for("new-task", 1)
    p["hooks"][0]["copy"] = "[TASK COPY]"
    with pytest.raises(creative_brief.SchemaError, match="unresolved placeholder"):
        creative_brief.generate_workbook(p, tmp_path / "placeholder.xlsx")
    for key in ("product", "production_link", "reference"):
        p = payload_for("new-task", 1)
        p[key] = {"not": "text"}
        with pytest.raises(creative_brief.SchemaError, match="must be text"):
            creative_brief.generate_workbook(p, tmp_path / f"bad-{key}.xlsx")
    p = payload_for("new-task", 1)
    p["music"] = "junk music"
    with pytest.raises(creative_brief.SchemaError, match="genre/vibe/style"):
        creative_brief.generate_workbook(p, tmp_path / "junk-music.xlsx")
    p = payload_for("policy-improvement", 1)
    p["body"][0]["line"] = True
    with pytest.raises(creative_brief.SchemaError, match="positive integer"):
        creative_brief.generate_workbook(p, tmp_path / "bad-line.xlsx")
    p = payload_for("policy-improvement", 1)
    p["parent_serial_number"] = "CO1234"
    with pytest.raises(creative_brief.SchemaError, match="exact _V# version"):
        creative_brief.generate_workbook(p, tmp_path / "bad-parent-version.xlsx")
    p = payload_for("policy-improvement", 1)
    p["hooks"][0]["copy"] = {"not": "text"}
    with pytest.raises(creative_brief.SchemaError, match="must be text"):
        creative_brief.generate_workbook(p, tmp_path / "bad-text.xlsx")


@pytest.mark.parametrize("cell,value", [
    ("B3", "[WRITER]"),
    ("A3", "[CORRUPTED LABEL]"),
    ("A23", "[TASK COPY]"),
    ("E99", "[HIDDEN TASK VALUE]"),
])
def test_master_rejects_arbitrary_bracketed_content(tmp_path, cell, value):
    path = creative_brief.create_masters(tmp_path)["new-task"]
    wb = openpyxl.load_workbook(path)
    wb["Editors"][cell] = value
    wb.save(path)
    with pytest.raises(creative_brief.ValidationError):
        creative_brief.validate_workbook(path, master=True, brief_type="new-task")


def test_master_contamination_rejected(tmp_path):
    path = creative_brief.create_masters(tmp_path)["body-improvement"]
    wb = openpyxl.load_workbook(path)
    wb["Editors"]["B3"] = "BW1234_V2"
    wb.save(path)
    with pytest.raises(creative_brief.ValidationError, match="contamination"):
        creative_brief.validate_workbook(path, master=True, brief_type="body-improvement")


@pytest.mark.parametrize("script", [
    "OLD: x NEW: y", "Before: x After: y", "x -> y",
    "Replace x with y", "Old x / New y",
])
def test_change_script_rejects_paired_old_new_instructions(tmp_path, script):
    p = payload_for("body-improvement", 1)
    p["versions"][0]["rows"][0]["script"] = script
    p["versions"][0]["rows"][0]["operation"] = "change"
    with pytest.raises(creative_brief.SchemaError, match="new version only"):
        creative_brief.generate_workbook(p, tmp_path / "paired.xlsx")


@pytest.mark.parametrize("mutation", ["base-parent", "bad-mix-version", "blended-parent"])
def test_mixing_rejects_conflicting_source_identity(tmp_path, mutation):
    p = payload_for("mixing-task", 1)
    row = p["versions"][0]["rows"][0]
    if mutation == "base-parent":
        row["source_parent_serial_number"] = "OTHER100_V1"
    elif mutation == "bad-mix-version":
        row.update(source="mix-in", source_parent_serial_number="CO1234", exact_source_version="CO1234")
    else:
        row.update(source="blended", source_parent_serial_number="OTHER100_V1", exact_source_version="")
    with pytest.raises(creative_brief.SchemaError):
        creative_brief.generate_workbook(p, tmp_path / "bad-source.xlsx")


def test_cli_generate_validate_and_masters(tmp_path):
    p = tmp_path / "payload.json"
    p.write_text(json.dumps(payload_for("new-task", 1)), encoding="utf-8")
    out = tmp_path / "generated.xlsx"
    result = subprocess.run([sys.executable, str(SCRIPT), "generate", "--payload", str(p), "--output", str(out)], check=True, capture_output=True, text=True)
    assert json.loads(result.stdout)["status"] == "created"
    result = subprocess.run([sys.executable, str(SCRIPT), "validate", "--workbook", str(out), "--payload", str(p)], check=True, capture_output=True, text=True)
    assert json.loads(result.stdout)["status"] == "valid"
    result = subprocess.run([sys.executable, str(SCRIPT), "create-masters", "--output-dir", str(tmp_path / "masters")], check=True, capture_output=True, text=True)
    assert len(json.loads(result.stdout)["files"]) == 5


@pytest.mark.skipif(not PROJECT_DIR.exists(), reason="company publishing scripts are not part of this share")
@pytest.mark.parametrize("filename", ["publish_masters.py", "run_live_qa.py"])
def test_upload_id_recovery_from_unexpected_success_response(monkeypatch, filename):
    module = load_project_script(filename, "project_" + filename.replace(".", "_"))
    calls = []

    def fake_run(*args):
        calls.append(args)
        return {"files": [{"id": "RECOVERED-ID"}]}

    monkeypatch.setattr(module, "run", fake_run)
    assert module.resolve_upload_id(
        {"unexpected": "shape"}, title="Unique QA title",
        account="automation@emater.io", folder="folder-id",
    ) == "RECOVERED-ID"
    assert calls and calls[0][:3] == ("gog", "drive", "search")


@pytest.mark.skipif(not PROJECT_DIR.exists(), reason="company publishing scripts are not part of this share")
@pytest.mark.parametrize("filename", ["publish_masters.py", "run_live_qa.py"])
def test_upload_id_recovery_fails_closed_when_not_unique(monkeypatch, filename):
    module = load_project_script(filename, "project_fail_" + filename.replace(".", "_"))
    monkeypatch.setattr(module, "run", lambda *args: {"files": []})
    with pytest.raises(RuntimeError, match="recovery"):
        module.resolve_upload_id(
            {}, title="Unique QA title", account="automation@emater.io", folder="folder-id",
        )
