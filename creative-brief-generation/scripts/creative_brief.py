#!/usr/bin/env python3
"""Generate and fail-closed validate Emater's canonical creative briefs."""
from __future__ import annotations

import argparse
import copy
import io
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from openpyxl import Workbook, load_workbook
from openpyxl.cell import Cell
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

BRIEF_TYPES = (
    "new-task", "policy-improvement", "hook-lead-iteration",
    "body-improvement", "mixing-task",
)
TABS = ["Editors", "Production", "Media Buyer"]
SHARED_LABELS = [
    "Writer", "Brief Type", "Platform", "Aspect Ratio",
    "Parent Serial Number", "Total Versions", "Editor Direction",
]
PRODUCTION_SECTIONS = [
    "Project Details", "Creator Shot Sheet", "Key Delivery Notes",
    "Master B-Roll Library", "Concept-Specific B-Roll",
]
PRODUCTION_VALUE_LABELS = [
    "Concept Name", "Brief ID", "Product", "Camera", "Orientation",
    "Style", "Movement", "Setting", "Wardrobe", "Tone", "Notes", "Link",
]
BODY_OPERATIONS = ("add", "remove", "change", "unchanged")
FORBIDDEN_LEGACY_TERMS = (
    "Base Ad ID", "Parent Creative", "Parent ID", "Creator Instructions",
    "Editing", "Ad Copy",
)
COLORS = {
    "editor_title": "0A111E", "shared_label": "DDEDF9",
    "value_region": "F7F9FF", "editor_header": "336BAD",
    "add": "93C47D", "remove": "E06666", "change": "F6B26B",
    "production_section": "2E3DB8", "production_table": "4A58D0",
    "production_alternate": "F0F1FA", "media_header": "1E3F70",
    "white": "FFFFFF", "black": "141414", "guidance": "FFF8E1",
    "gridline": "B7C3D0",
}
MASTER_FILENAMES = {
    "new-task": "creative-brief-new-task-master.xlsx",
    "policy-improvement": "creative-brief-policy-improvement-master.xlsx",
    "hook-lead-iteration": "creative-brief-hook-lead-iteration-master.xlsx",
    "body-improvement": "creative-brief-body-improvement-master.xlsx",
    "mixing-task": "creative-brief-mixing-task-master.xlsx",
}
DISPLAY_TYPES = {
    "new-task": "New Task", "policy-improvement": "Policy Improvement",
    "hook-lead-iteration": "Hook / Lead Iteration",
    "body-improvement": "Body Improvement", "mixing-task": "Mixing Task",
}


class SchemaError(ValueError):
    pass


class ValidationError(ValueError):
    pass


def _fill(color: str) -> PatternFill:
    return PatternFill("solid", fgColor=color)


def _font(*, bold: bool = False, color: str = COLORS["black"], size: int = 10,
          italic: bool = False) -> Font:
    return Font(name="Arial", size=size, bold=bold, italic=italic, color=color)


def _paint(cell: Cell, *, fill: str = COLORS["white"], bold: bool = False,
           color: str = COLORS["black"], size: int = 10, italic: bool = False,
           horizontal: Optional[str] = None, vertical: str = "top") -> None:
    cell.fill = _fill(fill)
    cell.font = _font(bold=bold, color=color, size=size, italic=italic)
    cell.alignment = Alignment(horizontal=horizontal, vertical=vertical, wrap_text=True)


def _style_row(ws, row: int, start: int, end: int, **kwargs: Any) -> None:
    for col in range(start, end + 1):
        _paint(ws.cell(row, col), **kwargs)


def _add_grid(ws, min_row: int, max_row: int, min_col: int, max_col: int) -> None:
    """Draw a visible thin divider around every cell in the owned rectangle."""
    side = Side(style="thin", color=COLORS["gridline"])
    border = Border(left=side, right=side, top=side, bottom=side)
    for row in ws.iter_rows(
        min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col,
    ):
        for cell in row:
            cell.border = border


def _title(ws, text: str, end_col: int = 5) -> None:
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=end_col)
    ws.cell(1, 1).value = text
    _style_row(ws, 1, 1, end_col, fill=COLORS["editor_title"], bold=True,
               color=COLORS["white"], size=15, horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 32


def _section(ws, row: int, text: str, end_col: int = 5,
             color: str = COLORS["editor_header"]) -> None:
    ws.cell(row, 1).value = text
    _style_row(ws, row, 1, end_col, fill=color, bold=True,
               color=COLORS["white"], vertical="center")
    ws.row_dimensions[row].height = 24


def _header(ws, row: int, values: Iterable[str], end_col: int = 5,
            color: str = COLORS["editor_header"]) -> None:
    for col, value in enumerate(values, 1):
        ws.cell(row, col).value = value
    _style_row(ws, row, 1, end_col, fill=color, bold=True,
               color=COLORS["white"], vertical="center")


def _assert_keys(obj: Mapping[str, Any], allowed: Iterable[str], where: str) -> None:
    unknown = sorted(set(obj) - set(allowed))
    if unknown:
        raise SchemaError(f"{where} contains unknown field(s): {', '.join(unknown)}")


def _text(data: Mapping[str, Any], key: str, *, required: bool = False) -> str:
    raw = data.get(key)
    if raw is None:
        value = ""
    elif not isinstance(raw, str):
        raise SchemaError(f"{key} must be text")
    else:
        value = raw.strip()
    if required and not value:
        raise SchemaError(f"{key} is required")
    return value


def _normalize_script_row(row: Mapping[str, Any], where: str,
                          operation: bool = False, source: bool = False) -> Dict[str, Any]:
    base = {"line", "script", "text_overlay", "editor_note"}
    if operation:
        base.add("operation")
    if source:
        base |= {"source", "source_parent_serial_number", "exact_source_version", "editor_direction"}
        base.discard("editor_note")
    _assert_keys(row, base, where)
    result = dict(row)
    line = row.get("line")
    if isinstance(line, bool) or not isinstance(line, int) or line <= 0:
        raise SchemaError(f"{where} line must be a positive integer")
    result["line"] = line
    result["script"] = _text(row, "script")
    result["text_overlay"] = _text(row, "text_overlay")
    if not result["script"] and not result["text_overlay"]:
        raise SchemaError(f"{where} requires Script or Text Overlay")
    if operation:
        if row.get("operation") not in BODY_OPERATIONS:
            raise SchemaError("body row operation must be add/remove/change/unchanged")
        if row.get("operation") == "change":
            paired_edit = re.search(
                r"(?is)(?:\b(?:old|current|before)\s*:\s*.+\b(?:new|revised|after)\s*:"
                r"|\breplace\b.+\bwith\b|\bold\b.+[/|].*\bnew\b|(?:->|→))",
                result["script"],
            )
            if paired_edit:
                raise SchemaError("change Script must contain the new version only")
        result["editor_note"] = _text(row, "editor_note")
    elif source:
        src = row.get("source")
        if src not in ("base", "mix-in", "blended"):
            raise SchemaError("mixing source must be base/mix-in/blended")
        result["source"] = src
        result["source_parent_serial_number"] = _text(row, "source_parent_serial_number")
        result["exact_source_version"] = _text(row, "exact_source_version")
        result["editor_direction"] = _text(row, "editor_direction")
        if src == "mix-in" and not result["source_parent_serial_number"]:
            raise SchemaError("mix-in source requires source_parent_serial_number")
        if src in ("base", "mix-in") and not result["exact_source_version"]:
            raise SchemaError("base and mix-in rows require exact_source_version")
    else:
        result["editor_note"] = _text(row, "editor_note")
    return result


def _normalize_hooks(rows: Any, total: int, where: str) -> List[Dict[str, Any]]:
    if not isinstance(rows, list) or not rows:
        raise SchemaError(f"{where} hooks must be a nonempty array")
    if len(rows) != total:
        raise SchemaError("total_versions must equal hooks length")
    normalized = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise SchemaError("each hook must be an object")
        _assert_keys(row, {"version", "copy", "text_overlay", "editor_note"}, f"{where} hook")
        item = {
            "version": _text(row, "version", required=True),
            "copy": _text(row, "copy"),
            "text_overlay": _text(row, "text_overlay"),
            "editor_note": _text(row, "editor_note"),
        }
        # Visual-only / no-VO openers keep Copy blank (spoken words only), but
        # a row must still carry approved on-screen text or an editor note.
        if not (item["copy"] or item["text_overlay"] or item["editor_note"]):
            raise SchemaError(f"{where} hook {item['version']} requires Copy, Text Overlay, or Editor Note")
        normalized.append(item)
    return normalized


def _normalize_body(rows: Any, where: str) -> List[Dict[str, Any]]:
    if not isinstance(rows, list) or not rows:
        raise SchemaError(f"{where} body must be a nonempty array")
    return [_normalize_script_row(row, f"{where} body row") for row in rows]


def normalize_payload(raw: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise SchemaError("payload must be an object")
    data = copy.deepcopy(dict(raw))
    common_allowed = {
        "task_title", "writer", "brief_type", "platform", "aspect_ratio",
        "parent_serial_number", "total_versions", "editor_direction",
        "production", "media_buyer",
    }
    union_allowed = common_allowed | {
        "hooks", "body", "versions", "product", "generate_ai_vo", "voiceover",
        "music", "production_link", "reference", "connect_to",
    }
    _assert_keys(data, union_allowed, "payload")
    brief_type = _text(data, "brief_type", required=True)
    if brief_type not in BRIEF_TYPES:
        raise SchemaError(f"brief_type must be one of: {', '.join(BRIEF_TYPES)}")
    type_allowed = {
        "new-task": common_allowed | {"hooks", "body", "product", "generate_ai_vo", "voiceover", "music", "production_link", "reference"},
        "policy-improvement": common_allowed | {"connect_to", "hooks", "body"},
        "hook-lead-iteration": common_allowed | {"connect_to", "hooks"},
        "body-improvement": common_allowed | {"versions"},
        "mixing-task": common_allowed | {"versions"},
    }
    _assert_keys(data, type_allowed[brief_type], f"{brief_type} payload")
    def reject_placeholders(value: Any, path: str = "payload") -> None:
        if isinstance(value, str):
            if re.search(r"(?i)(?<!\w)n\s*/\s*a(?!\w)", value):
                raise SchemaError(f"{path} must be blank rather than N/A")
            if re.fullmatch(r"\[[A-Z0-9 _-]+\]", value.strip()):
                raise SchemaError(f"{path} contains an unresolved placeholder")
        if isinstance(value, Mapping):
            for key, child in value.items():
                reject_placeholders(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                reject_placeholders(child, f"{path}[{index}]")
    reject_placeholders(data)
    data["brief_type"] = brief_type
    for key in ("task_title", "writer", "platform", "aspect_ratio"):
        data[key] = _text(data, key, required=True)
    data["parent_serial_number"] = _text(data, "parent_serial_number")
    data["editor_direction"] = _text(data, "editor_direction")
    raw_total = data.get("total_versions")
    if isinstance(raw_total, bool) or not isinstance(raw_total, int):
        raise SchemaError("total_versions must be a positive integer")
    total = raw_total
    if total <= 0:
        raise SchemaError("total_versions must be a positive integer")
    data["total_versions"] = total

    if brief_type == "new-task":
        if data["parent_serial_number"]:
            raise SchemaError("new-task Parent Serial Number must be blank")
        required = ("product", "generate_ai_vo", "music", "production_link", "reference")
        for key in required:
            if key not in data:
                raise SchemaError(f"new-task requires {key}")
        for key in ("product", "production_link", "reference"):
            data[key] = _text(data, key)
        if not isinstance(data.get("generate_ai_vo"), bool):
            raise SchemaError("generate_ai_vo must be boolean")
        # Liel, 2026-10-18: AI voiceover briefs (Coolina default) leave Music
        # blank unless the requester specifies it. Non-AI-VO tasks still
        # require a positive description or exactly "No Music".
        data["music"] = _text(data, "music", required=not data["generate_ai_vo"])
        if data["music"] and data["music"].casefold() in {
            "music", "any music", "anything", "whatever", "tbd", "unknown", "junk music",
        }:
            raise SchemaError("music must specify a genre/vibe/style or exactly No Music")
        if data["music"] and data["music"] != "No Music" and re.search(
            r"(?i)\b(?:no|not|without|avoid|never|don't|do not|shouldn't|mustn't)\b",
            data["music"],
        ):
            raise SchemaError("music must describe the desired sound positively")
        if not isinstance(data.get("generate_ai_vo"), bool):
            raise SchemaError("generate_ai_vo must be boolean")
        if data["generate_ai_vo"]:
            voice = data.get("voiceover")
            if not isinstance(voice, Mapping):
                raise SchemaError("voiceover details are required when generate_ai_vo is true")
            _assert_keys(voice, {"accent", "age", "gender", "style", "approved"}, "voiceover")
            normalized_voice: Dict[str, Any] = {
                key: _text(voice, key, required=True) for key in ("accent", "age", "style")
            }
            if voice.get("gender") not in ("Male", "Female"):
                raise SchemaError("voiceover gender must be exactly Male/Female")
            if voice.get("approved") is not True:
                raise SchemaError("voiceover gender must be explicitly approved")
            normalized_voice.update(gender=voice["gender"], approved=True)
            data["voiceover"] = normalized_voice
        elif data.get("voiceover") not in (None, {}, ""):
            raise SchemaError("voiceover must be omitted when generate_ai_vo is false")
        data["hooks"] = _normalize_hooks(data.get("hooks"), total, brief_type)
        data["body"] = _normalize_body(data.get("body"), brief_type)

    elif brief_type in ("policy-improvement", "hook-lead-iteration"):
        if not data["parent_serial_number"]:
            raise SchemaError("parent_serial_number is required for iteration briefs")
        if not re.fullmatch(r"[A-Za-z0-9-]+_V\d+", data["parent_serial_number"]):
            raise SchemaError("parent_serial_number must identify an exact _V# version")
        data["connect_to"] = _text(data, "connect_to", required=True)
        data["hooks"] = _normalize_hooks(data.get("hooks"), total, brief_type)
        if brief_type == "policy-improvement":
            data["body"] = _normalize_body(data.get("body"), brief_type)
        elif "body" in data:
            raise SchemaError("hook/lead iteration must not contain an unchanged body")

    else:
        if not data["parent_serial_number"]:
            raise SchemaError("parent_serial_number is required for iteration briefs")
        if not re.fullmatch(r"[A-Za-z0-9-]+_V\d+", data["parent_serial_number"]):
            raise SchemaError("parent_serial_number must identify an exact _V# version")
        versions = data.get("versions")
        if not isinstance(versions, list) or not versions:
            raise SchemaError("versions must be a nonempty array")
        if len(versions) != total:
            raise SchemaError("total_versions must equal versions length")
        normalized_versions = []
        for version in versions:
            if not isinstance(version, Mapping):
                raise SchemaError("each version must be an object")
            _assert_keys(version, {"version", "rows"}, f"{brief_type} version")
            name = _text(version, "version", required=True)
            rows = version.get("rows")
            if not isinstance(rows, list) or not rows:
                raise SchemaError(f"{brief_type} version rows must be nonempty")
            normalized_versions.append({
                "version": name,
                "rows": [
                    _normalize_script_row(
                        row, f"{brief_type} row",
                        operation=brief_type == "body-improvement",
                        source=brief_type == "mixing-task",
                    ) for row in rows
                ],
            })
        if brief_type == "mixing-task":
            for version in normalized_versions:
                for row in version["rows"]:
                    source = row["source"]
                    if source == "base":
                        if row["source_parent_serial_number"]:
                            raise SchemaError("base rows must not set source_parent_serial_number")
                        if row["exact_source_version"] != data["parent_serial_number"]:
                            raise SchemaError("base exact_source_version must equal parent_serial_number")
                    elif source == "mix-in":
                        if not re.fullmatch(r"[A-Za-z0-9-]+_V\d+", row["source_parent_serial_number"]):
                            raise SchemaError("mix-in source_parent_serial_number must identify an exact _V# version")
                        if row["exact_source_version"] != row["source_parent_serial_number"]:
                            raise SchemaError("mix-in exact_source_version must equal source_parent_serial_number")
                    elif row["exact_source_version"] or row["source_parent_serial_number"]:
                        raise SchemaError("blended rows must not claim source identity")
        data["versions"] = normalized_versions


    production = data.get("production")
    if production is not None:
        if not isinstance(production, Mapping):
            raise SchemaError("production must be an object")
        _assert_keys(production, {
            "concept_name", "brief_id", "product", "camera", "orientation",
            "style", "movement", "setting", "wardrobe", "tone", "notes",
            "master_b_roll_link", "concept_b_roll",
        }, "production")
        normalized_production = {}
        for key in ("concept_name", "brief_id", "product", "camera", "orientation", "style", "movement", "setting", "wardrobe", "tone", "notes", "master_b_roll_link"):
            normalized_production[key] = _text(production, key)
        concept_b_roll = production.get("concept_b_roll", [])
        if not isinstance(concept_b_roll, list):
            raise SchemaError("production.concept_b_roll must be an array")
        normalized_b_roll = []
        for index, item in enumerate(concept_b_roll):
            if not isinstance(item, str) or not item.strip():
                raise SchemaError(f"production.concept_b_roll[{index}] must be nonempty text")
            normalized_b_roll.append(item.strip())
        normalized_production["concept_b_roll"] = normalized_b_roll
        data["production"] = normalized_production
    media = data.get("media_buyer")
    if media is not None:
        if not isinstance(media, Mapping):
            raise SchemaError("media_buyer must be an object")
        _assert_keys(media, {"primary_text", "ad_headline"}, "media_buyer")
        data["media_buyer"] = {
            "primary_text": _text(media, "primary_text"),
            "ad_headline": _text(media, "ad_headline"),
        }
    return data


def _setup_editors(ws, brief_type: str, payload: Optional[Dict[str, Any]]) -> None:
    ws.title = "Editors"
    ws.sheet_view.showGridLines = False
    for col, width in {"A": 22, "B": 58, "C": 34, "D": 36, "E": 18}.items():
        ws.column_dimensions[col].width = width
    text = f"CREATIVE BRIEF — {DISPLAY_TYPES[brief_type].upper()}" if payload is None else payload["task_title"]
    _title(ws, text)
    values = [None] * 7 if payload is None else [
        payload["writer"], DISPLAY_TYPES[brief_type], payload["platform"],
        payload["aspect_ratio"], payload["parent_serial_number"] or None,
        payload["total_versions"], payload["editor_direction"] or None,
    ]
    for row, (label, value) in enumerate(zip(SHARED_LABELS, values), 3):
        ws.cell(row, 1).value = label
        _paint(ws.cell(row, 1), fill=COLORS["shared_label"], bold=True, vertical="center")
        ws.cell(row, 2).value = value
        for col in range(2, 6):
            _paint(
                ws.cell(row, col), fill=COLORS["value_region"],
                horizontal="left" if row == 8 and col == 2 else None, vertical="center",
            )
        ws.row_dimensions[row].height = 24


def _write_label_value(ws, row: int, label: str, value: Any) -> None:
    ws.cell(row, 1).value = label
    _paint(ws.cell(row, 1), fill=COLORS["shared_label"], bold=True)
    ws.cell(row, 2).value = value if value not in (None, "") else None
    for col in range(2, 6):
        _paint(ws.cell(row, col), fill=COLORS["value_region"])


def _write_hooks(ws, start: int, rows: Optional[List[Dict[str, Any]]], title: str) -> Tuple[int, Tuple[int, int]]:
    _section(ws, start, title)
    _header(ws, start + 1, ["Version", "Copy", "Text Overlay", "Editor Note"], end_col=5)
    values = rows if rows is not None else [None]
    first = start + 2
    for row_no, item in enumerate(values, first):
        rendered = [None] * 4 if item is None else [item["version"], item["copy"] or None, item["text_overlay"] or None, item["editor_note"] or None]
        for col, value in enumerate(rendered, 1):
            ws.cell(row_no, col).value = value
            _paint(ws.cell(row_no, col))
        _paint(ws.cell(row_no, 5))
        ws.row_dimensions[row_no].height = 46
    return first + len(values), (first, first + len(values) - 1)


def _write_body(ws, start: int, rows: Optional[List[Dict[str, Any]]], title: str = "BODY") -> Tuple[int, Tuple[int, int]]:
    _section(ws, start, title)
    _header(ws, start + 1, ["Line", "Script", "Text Overlay", "Editor Note"], end_col=5)
    values = rows if rows is not None else [None]
    first = start + 2
    for idx, (row_no, item) in enumerate(zip(range(first, first + len(values)), values), 1):
        rendered = [None] * 4 if item is None else [item.get("line") if item.get("line") not in (None, "") else idx, item["script"], item.get("text_overlay") or None, item.get("editor_note") or None]
        for col, value in enumerate(rendered, 1):
            ws.cell(row_no, col).value = value
            _paint(ws.cell(row_no, col))
        _paint(ws.cell(row_no, 5))
        ws.row_dimensions[row_no].height = 46
    return first + len(values), (first, first + len(values) - 1)


def _mix_marker(row: Mapping[str, Any]) -> str:
    if row["source"] == "base":
        marker = "🟩 Base"
    elif row["source"] == "mix-in":
        marker = f"🟥 Mix-in / {row['source_parent_serial_number']}"
    else:
        marker = "🟨 Blended rewrite"
    direction = row.get("editor_direction")
    if direction:
        marker += f"\n{direction}"
    return marker


def _write_version_bodies(ws, start: int, versions: Optional[List[Dict[str, Any]]],
                          brief_type: str) -> Tuple[int, List[Tuple[int, int]]]:
    _section(ws, start, "BODY IMPROVEMENT" if brief_type == "body-improvement" else "MIXING TASK")
    row = start + 1
    ranges = []
    values = versions if versions is not None else [None]
    for index, version in enumerate(values, 1):
        ws.cell(row, 2).value = f"BODY {index}" if version is not None else "BODY [VERSION]"
        _style_row(ws, row, 1, 5, fill=COLORS["value_region"], bold=True)
        row += 1
        _header(ws, row, ["Line", "Script", "Text Overlay", "Editor Note"], end_col=5)
        row += 1
        items = version["rows"] if version is not None else [None]
        first = row
        for item_index, item in enumerate(items, 1):
            if item is None:
                rendered = [None] * 4
            elif brief_type == "body-improvement":
                rendered = [item.get("line") if item.get("line") not in (None, "") else item_index,
                            item["script"], item["text_overlay"] or None, item["editor_note"] or None]
            else:
                rendered = [item.get("line") if item.get("line") not in (None, "") else item_index,
                            item["script"], item["text_overlay"] or None, _mix_marker(item)]
            for col, value in enumerate(rendered, 1):
                ws.cell(row, col).value = value
                fill = COLORS["white"]
                if item is not None and brief_type == "body-improvement" and col == 2:
                    fill = COLORS.get(item["operation"], COLORS["white"])
                _paint(ws.cell(row, col), fill=fill)
            _paint(ws.cell(row, 5))
            ws.row_dimensions[row].height = 48
            row += 1
        ranges.append((first, row - 1))
        row += 1
    return row, ranges


def editor_layout(brief_type: str, payload: Optional[Dict[str, Any]] = None,
                  master: bool = False) -> Dict[str, Any]:
    if brief_type not in BRIEF_TYPES:
        raise SchemaError("unknown brief type")
    if brief_type == "new-task":
        hook_count = 1 if master or payload is None else len(payload["hooks"])
        body_count = 1 if master or payload is None else len(payload["body"])
        hook_start = 20
        body_start = hook_start + hook_count + 3
        return {"hook_start": hook_start, "hook_end": hook_start + hook_count - 1,
                "body_start": body_start, "body_end": body_start + body_count - 1,
                "owned_end": body_start + body_count - 1}
    if brief_type in ("policy-improvement", "hook-lead-iteration"):
        hook_count = 1 if master or payload is None else len(payload["hooks"])
        hook_start = 15
        result = {"hook_start": hook_start, "hook_end": hook_start + hook_count - 1}
        if brief_type == "policy-improvement":
            body_count = 1 if master or payload is None else len(payload["body"])
            body_start = hook_start + hook_count + 3
            result.update({"body_start": body_start, "body_end": body_start + body_count - 1,
                           "owned_end": body_start + body_count - 1})
        else:
            result["owned_end"] = result["hook_end"]
        return result
    versions = [None] if master or payload is None else payload["versions"]
    row = 16
    ranges = []
    for version in versions:
        count = 1 if version is None else len(version["rows"])
        first = row + 2
        ranges.append((first, first + count - 1))
        row = first + count + 1
    return {"version_ranges": ranges, "owned_end": row - 1}


def _build_editors(wb: Workbook, brief_type: str, payload: Optional[Dict[str, Any]]) -> None:
    ws = wb.active
    if ws is None:
        raise RuntimeError("workbook has no active worksheet")
    _setup_editors(ws, brief_type, payload)
    if brief_type == "new-task":
        voice = ""
        if payload and payload.get("generate_ai_vo"):
            v = payload["voiceover"]
            voice = f"Accent: {v['accent']} | Age: {v['age']} | Gender: {v['gender']} | Style: {v['style']}"
        values = [
            payload.get("product", "") if payload else "",
            ("YES" if payload.get("generate_ai_vo") else "NO") if payload else "",
            voice,
            payload.get("music", "") if payload else "",
            payload.get("production_link", "") if payload else "",
            payload.get("reference", "") if payload else "",
        ]
        for row, (label, value) in enumerate(zip(
            ["Product", "Generate AI VO?", "Voiceover Details", "Music", "Production Link", "Reference"], values
        ), 10):
            _write_label_value(ws, row, label, value)
        _section(ws, 17, "SCRIPT")
        next_row, _ = _write_hooks(ws, 18, payload["hooks"] if payload else None, "HOOKS")
        _write_body(ws, next_row + 1, payload["body"] if payload else None)
    elif brief_type in ("policy-improvement", "hook-lead-iteration"):
        _write_label_value(ws, 11, "Connect To", payload.get("connect_to", "") if payload else "")
        title = "POLICY IMPROVEMENT" if brief_type == "policy-improvement" else "HOOK / LEAD ITERATIONS"
        next_row, _ = _write_hooks(ws, 13, payload["hooks"] if payload else None, title)
        if brief_type == "policy-improvement":
            _write_body(ws, next_row + 1, payload["body"] if payload else None)
    else:
        if brief_type == "body-improvement":
            for col, (label, key) in enumerate(zip(("ADD", "REMOVE", "CHANGE", "UNCHANGED"), ("add", "remove", "change", "white")), 1):
                ws.cell(11, col).value = label
                _paint(ws.cell(11, col), fill=COLORS[key], bold=True)
            _paint(ws.cell(11, 5))
        else:
            _write_label_value(ws, 11, "Key", "🟩 Base | 🟥 Mix-in / [Parent Serial Number] | 🟨 Blended rewrite")
        _write_version_bodies(ws, 13, payload["versions"] if payload else None, brief_type)
    ws.freeze_panes = "A3"
    _add_grid(ws, 1, ws.max_row, 1, 5)


def _value(data: Mapping[str, Any], key: str) -> Any:
    value = data.get(key)
    return value if value not in (None, "") else None


def _build_production(wb: Workbook, payload: Optional[Dict[str, Any]]) -> None:
    ws = wb.create_sheet("Production")
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 92
    ws.merge_cells("A1:B1")
    ws["A1"] = "PRODUCTION BRIEF"
    _style_row(ws, 1, 1, 2, fill=COLORS["editor_title"], bold=True,
               color=COLORS["white"], size=15, horizontal="center", vertical="center")
    production = payload.get("production", {}) if payload else {}
    for row, label in {3: "Project Details", 9: "Creator Shot Sheet", 19: "Key Delivery Notes",
                       23: "Master B-Roll Library", 27: "Concept-Specific B-Roll"}.items():
        _section(ws, row, label, end_col=2, color=COLORS["production_section"])
    for row, names in {4: ("Field", "Value"), 10: ("Field", "Value"),
                       20: ("Field", "Notes"), 28: ("#", "Description")}.items():
        _header(ws, row, names, end_col=2, color=COLORS["production_table"])
    entries = [
        (5, "Concept Name", "concept_name"), (6, "Brief ID", "brief_id"), (7, "Product", "product"),
        (11, "Camera", "camera"), (12, "Orientation", "orientation"), (13, "Style", "style"),
        (14, "Movement", "movement"), (15, "Setting", "setting"), (16, "Wardrobe", "wardrobe"),
        (17, "Tone", "tone"), (21, "Notes", "notes"), (25, "Link", "master_b_roll_link"),
    ]
    for row, label, key in entries:
        ws.cell(row, 1).value = label
        ws.cell(row, 2).value = _value(production, key)
        fill = COLORS["production_alternate"] if row % 2 == 0 else COLORS["white"]
        _style_row(ws, row, 1, 2, fill=fill)
        ws.cell(row, 1).font = _font(bold=True)
    ws["A24"] = "First-time creators: film all shots in the master library. Returning creators: skip this section."
    _style_row(ws, 24, 1, 2, fill=COLORS["guidance"])
    ws["A24"].font = _font(size=9, italic=True, color="8B6F00")
    broll = production.get("concept_b_roll") or []
    for index in range(max(1, len(broll))):
        row = 29 + index
        item = broll[index] if index < len(broll) else None
        ws.cell(row, 1).value = index + 1 if item is not None else None
        ws.cell(row, 2).value = item
        _style_row(ws, row, 1, 2, fill=COLORS["production_alternate"] if index % 2 else COLORS["white"])
    ws.freeze_panes = "A3"
    _add_grid(ws, 1, ws.max_row, 1, 2)


def _build_media(wb: Workbook, payload: Optional[Dict[str, Any]]) -> None:
    ws = wb.create_sheet("Media Buyer")
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 24
    ws.column_dimensions["B"].width = 88
    media = payload.get("media_buyer", {}) if payload else {}
    ws["A1"] = "Media Buyer"
    _style_row(ws, 1, 1, 2, fill=COLORS["media_header"], bold=True, color=COLORS["white"], size=12)
    _style_row(ws, 2, 1, 2)
    for row, label, key in ((3, "Primary Text", "primary_text"), (4, "Ad Headline", "ad_headline")):
        ws.cell(row, 1).value = label
        ws.cell(row, 2).value = _value(media, key)
        _paint(ws.cell(row, 1), fill=COLORS["media_header"], bold=True, color=COLORS["white"])
        _paint(ws.cell(row, 2))
    _add_grid(ws, 1, 4, 1, 2)


def _build_workbook(brief_type: str, payload: Optional[Dict[str, Any]]) -> Workbook:
    wb = Workbook()
    _build_editors(wb, brief_type, payload)
    _build_production(wb, payload)
    _build_media(wb, payload)
    wb.active = 0
    wb.calculation.fullCalcOnLoad = True
    return wb


def generate_workbook(raw_payload: Mapping[str, Any], output: Path) -> Dict[str, Any]:
    payload = normalize_payload(raw_payload)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    _build_workbook(payload["brief_type"], payload).save(output)
    return payload


def create_masters(output_dir: Path) -> Dict[str, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for brief_type in BRIEF_TYPES:
        path = output_dir / MASTER_FILENAMES[brief_type]
        _build_workbook(brief_type, None).save(path)
        paths[brief_type] = path
    return paths


def _rgb(value: Any) -> str:
    return str(value or "")[-6:].upper()


def _side_signature(side: Any) -> Tuple[Any, ...]:
    if side is None:
        return (None, None, "")
    color = getattr(side, "color", None)
    return (
        getattr(side, "style", None),
        getattr(color, "type", None) if color else None,
        _rgb(getattr(color, "rgb", "")) if color and color.type == "rgb" else "",
    )


def _signature(cell: Cell) -> Tuple[Any, ...]:
    font_color = cell.font.color
    return (
        cell.value, cell.fill.fill_type, cell.fill.fgColor.type, _rgb(cell.fill.fgColor.rgb),
        cell.font.name, cell.font.sz, cell.font.bold, cell.font.italic,
        font_color.type if font_color else None,
        _rgb(font_color.rgb) if font_color and font_color.type == "rgb" else "",
        cell.alignment.horizontal, cell.alignment.vertical, bool(cell.alignment.wrap_text),
        cell.alignment.text_rotation, bool(cell.alignment.shrink_to_fit), cell.alignment.indent,
        cell.number_format,
        _side_signature(cell.border.left), _side_signature(cell.border.right),
        _side_signature(cell.border.top), _side_signature(cell.border.bottom),
        _side_signature(cell.border.diagonal),
    )


def _cell_matches(actual: Any, expected: Any, *, google_roundtrip: bool) -> bool:
    actual_signature = list(_signature(actual))
    expected_signature = list(_signature(expected))
    if (
        google_roundtrip
        and actual.value is None
        and expected.value is None
        and actual_signature[4] == expected_signature[4] == "Calibri"
        and actual_signature[5] is None
        and expected_signature[5] == 11.0
    ):
        # Applying border-only formatting in Google Sheets can omit the default
        # 11pt font size from blank cells in XLSX exports. This is visually and
        # semantically identical; all nonblank and nondefault font styles remain exact.
        actual_signature[5] = 11.0
    return actual_signature == expected_signature


def _compare(actual_path: Path, expected: Workbook, *,
             google_roundtrip: bool = False) -> None:
    actual = load_workbook(actual_path)
    buffer = io.BytesIO()
    expected.save(buffer)
    buffer.seek(0)
    expected = load_workbook(buffer)
    if actual.sheetnames != TABS:
        raise ValidationError(f"tabs must be exactly {TABS}")

    for aws, ews in zip(actual.worksheets, expected.worksheets):
        if aws.sheet_state != "visible":
            raise ValidationError(f"hidden sheet: {aws.title}")
        if aws.sheet_view.showGridLines != ews.sheet_view.showGridLines:
            raise ValidationError(f"gridline setting mismatch in {aws.title}")
        if str(aws.freeze_panes or "") != str(ews.freeze_panes or ""):
            raise ValidationError(f"freeze-pane mismatch in {aws.title}")
        if any(d.hidden for d in aws.row_dimensions.values()) or any(d.hidden for d in aws.column_dimensions.values()):
            raise ValidationError(f"hidden rows or columns in {aws.title}")
        # Google Sheets' XLSX exporter may emit an extra default column
        # dimension (for example F) even when the canonical artifact owns
        # only A:E. Enforce every canonical dimension; ignore exporter-only
        # default dimensions outside the owned range.
        dimension_columns = (
            set(ews.column_dimensions)
            if google_roundtrip
            else set(aws.column_dimensions) | set(ews.column_dimensions)
        )
        for column in dimension_columns:
            actual_width = aws.column_dimensions[column].width
            expected_width = ews.column_dimensions[column].width
            width_matches = (
                abs((actual_width or 0) - (expected_width or 0)) <= 2.5
                if google_roundtrip else actual_width == expected_width
            )
            if not width_matches:
                raise ValidationError(f"column-width mismatch in {aws.title}!{column}")
        if google_roundtrip:
            # Google exports explicit default-height dimensions for many
            # otherwise untouched rows. Compare every row the canonical sheet
            # owns using effective heights, while ignoring exporter-only rows
            # below the owned range.
            dimension_rows = set(range(1, ews.max_row + 1))
        else:
            dimension_rows = set(aws.row_dimensions) | set(ews.row_dimensions)
        for row in dimension_rows:
            actual_height = aws.row_dimensions[row].height
            expected_height = ews.row_dimensions[row].height
            if google_roundtrip:
                actual_effective = actual_height or aws.sheet_format.defaultRowHeight
                expected_effective = expected_height or ews.sheet_format.defaultRowHeight
                height_matches = abs(actual_effective - expected_effective) <= 2.5
            else:
                height_matches = actual_height == expected_height
            if not height_matches:
                raise ValidationError(f"row-height mismatch in {aws.title}!{row}")
        if set(map(str, aws.merged_cells.ranges)) != set(map(str, ews.merged_cells.ranges)):
            raise ValidationError(f"merged-cell mismatch in {aws.title}")
        for row in range(1, max(aws.max_row, ews.max_row) + 1):
            for col in range(1, max(aws.max_column, ews.max_column) + 1):
                if not _cell_matches(
                    aws.cell(row, col), ews.cell(row, col),
                    google_roundtrip=google_roundtrip,
                ):
                    raise ValidationError(f"cell mismatch at {aws.title}!{get_column_letter(col)}{row}")


def validate_workbook(workbook: Path, payload: Optional[Mapping[str, Any]] = None,
                      *, master: bool = False, brief_type: Optional[str] = None,
                      google_roundtrip: bool = False) -> bool:
    workbook = Path(workbook)
    if not workbook.exists():
        raise ValidationError(f"workbook not found: {workbook}")
    if master:
        if brief_type not in BRIEF_TYPES:
            raise ValidationError("master validation requires a valid brief_type")
        expected = _build_workbook(str(brief_type), None)
    else:
        if payload is None:
            raise ValidationError("generated validation requires payload")
        normalized = normalize_payload(payload)
        expected = _build_workbook(normalized["brief_type"], normalized)
    wb = load_workbook(workbook)
    values = [str(c.value) for ws in wb.worksheets for row in ws.iter_rows() for c in row if c.value is not None]
    text = "\n".join(values)
    for term in FORBIDDEN_LEGACY_TERMS:
        if term in text:
            raise ValidationError(f"forbidden legacy term found: {term}")
    if master:
        scrubbed = re.sub(r"\[[^\]]*\]", "", text)
        if re.search(r"\b(?:BW|CO|BE)\d{3,5}(?:[_ -]?V\d+)?\b", scrubbed, re.I):
            raise ValidationError("master contamination: creative serial found")
        if re.search(r"\b(?:Bodywell|Coolina|Bernstein|Test Writer|Test Product|Ben|Liel)\b", scrubbed, re.I):
            raise ValidationError("master contamination: brand/person/task value found")
        if "N/A" in text:
            raise ValidationError("masters must use blank values, not N/A")
    _compare(workbook, expected, google_roundtrip=google_roundtrip)
    return True


def _load(path: Path) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise SchemaError("payload JSON must be an object")
    return data


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate")
    generate.add_argument("--payload", type=Path, required=True)
    generate.add_argument("--output", type=Path, required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--workbook", type=Path, required=True)
    validate.add_argument("--payload", type=Path)
    validate.add_argument("--master", action="store_true")
    validate.add_argument("--brief-type", choices=BRIEF_TYPES)
    validate.add_argument("--google-roundtrip", action="store_true")
    masters = sub.add_parser("create-masters")
    masters.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            raw = _load(args.payload)
            normalized = generate_workbook(raw, args.output)
            validate_workbook(args.output, payload=raw)
            result = {"status": "created", "brief_type": normalized["brief_type"], "output": str(args.output)}
        elif args.command == "validate":
            raw = _load(args.payload) if args.payload else None
            validate_workbook(
                args.workbook, payload=raw, master=args.master,
                brief_type=args.brief_type, google_roundtrip=args.google_roundtrip,
            )
            result = {"status": "valid", "workbook": str(args.workbook)}
        else:
            paths = create_masters(args.output_dir)
            for kind, path in paths.items():
                validate_workbook(path, master=True, brief_type=kind)
            result = {"status": "created", "files": {k: str(v) for k, v in paths.items()}}
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (SchemaError, ValidationError, OSError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
