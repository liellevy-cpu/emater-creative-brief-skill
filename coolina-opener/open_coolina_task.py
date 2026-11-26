#!/usr/bin/env python3
"""Open a Coolina creative task exactly like Emater's agents (Cole, Camilla, Ivan).

One command does the whole job, in the same order the agents use:
  1. check the brief and every Monday field before anything is written
  2. build the 3-tab brief (Editors / Production / Media Buyer) with the company compiler
  3. upload it to the Creative Briefs drive as a Google Sheet and check the Google copy
  4. create the Monday task, wait for its serial, name it, write the Final Name
  5. link the brief last, then read every field back (and repair once if Monday automations moved something)

Usage:
  python3 open_coolina_task.py task.json --dry-run   # checks everything, writes nothing
  python3 open_coolina_task.py task.json             # opens the task

Needs (environment variables, never put them in the repo):
  MONDAY_API_TOKEN      your own Monday API token
  GOOGLE_CREDENTIALS    path to a Google credential JSON (service account or authorized user)
                        that can write to the Creative Briefs folder
  AI_AGENT_LABEL        your bot's label in the board's AI Agent column (Emater adds it for you)
Optional:
  BRIEFS_FOLDER_ID      Drive folder for briefs (default: Emater "Creative Briefs")

See COOLINA-TASK-OPENER.md for the task.json fields.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import os
import re
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "creative-brief-generation" / "scripts"))
import creative_brief  # noqa: E402  company brief compiler (same file the agents use)
import coolina_initial_naming as naming  # noqa: E402  company Final Name rules

BOARD_ID = 9298353728
GROUP_ID = "topics"  # New Concepts
DEFAULT_FOLDER = "15pQQ2nmn-pMYxLK0P3AiqZjSaqe8z72R"  # Creative Briefs (Emater shared drive)
ALBERT_ID = 38318866  # Team Leader the agents set

COL = {
    "status": "status", "serial": "text_mkrxa8kw", "owner": "multiple_person_mkscqwjv",
    "creative_director": "person", "copywriter": "multiple_person_mkrxvxb9",
    "team_leader": "multiple_person_mkrxen8b", "editor": "multiple_person_mkrwpfa6",
    "ai_agent": "color_mm4h23be", "iteration_type": "dropdown_mkskhreg", "format": "dropdown_mm14rmx0",
    "asset_type": "color_mkrxa713", "funnel": "color_mm3y9jqt", "swimlane": "color_mkrxsgqr",
    "parent": "text_mkrxd768", "brief_link": "link_mks5pgae", "ad_copy": "color_mm6dhpz",
    "platform": "color_mkts761t", "aspect": "color_mkrxkpcp", "total_versions": "numeric_mkrxw6rb",
    "offer": "color_mkrxt6yp", "priority": "color_mkrxe94b", "launch_date": "date_mktkp0x",
    "final_name": "long_text_mkrxjtnx", "tags": "tag_mm8bzts",
    "core_profile": "dropdown_mm8dgmyq", "core_angle": "dropdown_mm8d8rvj", "core_message": "dropdown_mm8d1jw3",
}
# (platform, ratio) -> exact Monday labels. Same three placements the agents support.
PLACEMENTS = {
    ("meta", "9:16"): ("Meta", "9x16 (4x5 safe)"),
    ("youtube", "16:9"): ("YouTube", "16x9"),
    ("youtube", "9:16"): ("YouTube", "9x16 (4x5 safe)"),
}
START_STATUSES = ("Review - Writing", "Ready for Production", "Ready for Post", "Ready for Editor")
RETIRED = {"dropdown_mm721msd", "dropdown_mm14xwvn", "dropdown_mm14etc4"}  # never write


class Stop(Exception):
    """A check failed. Nothing after this point was written."""


# ---------------------------------------------------------------- Monday

def monday(query, variables=None, retries=3):
    token = os.environ.get("MONDAY_API_TOKEN")
    if not token:
        raise Stop("MONDAY_API_TOKEN is not set")
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request("https://api.monday.com/v2", data=body, headers={
                "Authorization": token, "Content-Type": "application/json", "API-Version": "2024-10"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.load(r)
            if data.get("errors"):
                raise RuntimeError(f"Monday error: {data['errors']}")
            return data
        except (OSError, json.JSONDecodeError):
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("Monday request failed")


def live_schema():
    cols = monday("{ boards(ids:[%d]) { columns { id title type settings_str } } }" % BOARD_ID)
    return cols["data"]["boards"][0]["columns"]


def label_names(column):
    s = json.loads(column.get("settings_str") or "{}")
    labels = s.get("labels", {})
    off = {str(x) for x in s.get("deactivated_labels", [])}
    pairs = labels.items() if isinstance(labels, dict) else [(x["id"], x["name"]) for x in labels]
    return [name for key, name in pairs if name and str(key) not in off]


def read_item(item_id):
    ids = list(COL.values())
    r = monday('{ items(ids:[%s]) { name column_values(ids:%s) { id text value } } }' % (item_id, json.dumps(ids)))
    items = r["data"]["items"]
    if not items:
        raise RuntimeError(f"cannot read item {item_id}")
    return items[0]["name"], {row["id"]: row for row in items[0]["column_values"]}


def set_columns(item_id, values):
    monday("""mutation ($i: ID!, $b: ID!, $v: JSON!) { change_multiple_column_values(
              item_id:$i, board_id:$b, column_values:$v, create_labels_if_missing:false) { id } }""",
           {"i": str(item_id), "b": str(BOARD_ID), "v": json.dumps(values)})


# ---------------------------------------------------------------- Google

def google_drive():
    from googleapiclient.discovery import build
    path = os.environ.get("GOOGLE_CREDENTIALS") or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not path or not Path(path).expanduser().exists():
        raise Stop("GOOGLE_CREDENTIALS must point to a Google credential JSON file")
    info = json.loads(Path(path).expanduser().read_text())
    scopes = ["https://www.googleapis.com/auth/drive"]
    if info.get("type") == "service_account":
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_info(info, scopes=scopes)
    else:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        creds = Credentials.from_authorized_user_info(info, scopes)
        if not creds.valid and creds.refresh_token:
            creds.refresh(Request())
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def upload_and_check_sheet(drive, payload, name, folder):
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
    xlsx = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    with tempfile.TemporaryDirectory() as tmp:
        local, back = Path(tmp) / "brief.xlsx", Path(tmp) / "back.xlsx"
        creative_brief.generate_workbook(payload, local)
        creative_brief.validate_workbook(local, payload=payload)
        made = drive.files().create(
            body={"name": name, "parents": [folder], "mimeType": "application/vnd.google-apps.spreadsheet"},
            media_body=MediaFileUpload(str(local), mimetype=xlsx, resumable=False),
            fields="id", supportsAllDrives=True).execute()
        sheet_id = made["id"]
        try:
            with back.open("wb") as fh:
                dl = MediaIoBaseDownload(fh, drive.files().export_media(fileId=sheet_id, mimeType=xlsx))
                done = False
                while not done:
                    _, done = dl.next_chunk()
            creative_brief.validate_workbook(back, payload=payload, google_roundtrip=True)
        except Exception:
            trash(drive, sheet_id)
            raise
    return sheet_id, f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"


def trash(drive, file_id):
    try:
        drive.files().update(fileId=file_id, body={"trashed": True}, supportsAllDrives=True).execute()
    except Exception:
        pass


# ---------------------------------------------------------------- checks

def current_quarter(today):
    return f"Q{(today.month - 1) // 3 + 1}"


def launch_date(today):
    """Agents' rule: Mon-Wed -> this Friday; Thu-Sun -> next Wednesday."""
    if today.weekday() <= 2:
        return today + dt.timedelta(days=4 - today.weekday())
    return today + dt.timedelta(days=(2 - today.weekday()) % 7 or 7)


def prepare(task, schema=None, today=None):
    """Check everything and return the exact plan. No writes."""
    today = today or dt.date.today()
    if set(task) - {"brief", "monday"}:
        raise Stop("task.json may only contain 'brief' and 'monday'")
    m = dict(task.get("monday") or {})
    allowed = {"concept_name", "owner_monday_id", "owner_name", "owner_email", "funnel", "swimlane",
               "iteration_type", "format", "parent_serial", "offer", "priority", "status", "ad_copy",
               "launch_date", "team_leader_id", "core_profile", "core_angle", "core_message", "tags"}
    extra = set(m) - allowed
    if extra:
        raise Stop(f"unknown monday fields: {sorted(extra)}")
    for key in ("concept_name", "owner_monday_id", "owner_name", "funnel", "swimlane", "iteration_type",
                "format", "parent_serial", "offer"):
        if m.get(key) in (None, ""):
            raise Stop(f"monday.{key} is required; ask the human, don't guess")

    agent = os.environ.get("AI_AGENT_LABEL", "").strip()
    if not agent:
        raise Stop("AI_AGENT_LABEL is not set")

    try:
        brief = creative_brief.normalize_payload(task.get("brief") or {})
    except Exception as exc:
        raise Stop(f"brief: {exc}") from exc

    owner_first = str(m["owner_name"]).split()[0]
    if brief["writer"] != owner_first:
        raise Stop(f"brief.writer must be the human's first name ({owner_first!r}), never the bot")
    if brief["task_title"] != m["concept_name"]:
        raise Stop("brief.task_title must equal monday.concept_name")

    parent = str(m["parent_serial"]).strip()
    if brief["brief_type"] == "new-task":
        if parent != "Pnone":
            raise Stop("a new-task brief needs monday.parent_serial = 'Pnone'")
    else:
        found = re.fullmatch(r"CO(\d+)_V\d+", brief["parent_serial_number"], re.I)
        if not found or parent != f"PCO{found.group(1)}":
            raise Stop("monday.parent_serial must be PCO#### matching brief.parent_serial_number CO####_V#")

    ratio = brief["aspect_ratio"].lower().split()[0].replace("x", ":")
    placement = PLACEMENTS.get((brief["platform"].casefold(), ratio))
    if not placement:
        raise Stop("only Meta 9:16, YouTube 16:9 and YouTube 9:16 are supported")

    ad_copy = m.get("ad_copy") or "Default"
    media = brief.get("media_buyer") or {}
    has_copy = any(str(v or "").strip() for v in media.values())
    if ad_copy == "Default" and has_copy:
        raise Stop("Ad Copy = Default, so the Media Buyer tab must stay empty")
    if ad_copy == "Check Brief" and not (media.get("primary_text") and media.get("ad_headline")):
        raise Stop("Ad Copy = Check Brief needs the exact primary_text and ad_headline in the brief")
    if ad_copy not in ("Default", "Check Brief"):
        raise Stop("ad_copy must be Default or Check Brief")

    status = m.get("status") or "Review - Writing"
    if status not in START_STATUSES:
        raise Stop(f"status must be one of {START_STATUSES}")

    cfg = {
        "brand": "Coolina", "asset_type": "Video", "concept_name": m["concept_name"],
        "creative_funnel": str(m["funnel"]).upper(), "swimlane": m["swimlane"],
        "iteration_type": m["iteration_type"], "format": m["format"], "parent_serial": parent,
        "requester_monday_name": m["owner_name"], "requester_monday_user_id": int(m["owner_monday_id"]),
        "owner_id": int(m["owner_monday_id"]), "_ai_agent_name": agent, "tags": m.get("tags") or [],
        "core_profile": m.get("core_profile"), "core_angle": m.get("core_angle"),
        "core_message": m.get("core_message"),
    }
    try:
        naming.validate(cfg)
        naming.build("CO1", cfg)
    except ValueError as exc:
        if "AI Agent" in str(exc):
            raise Stop(f"AI Agent label {agent!r} is not in the company naming list yet; ask Emater to add it") from exc
        raise Stop(f"monday fields: {exc}") from exc
    funnel_label = naming.FUNNEL_LABELS[cfg["creative_funnel"]]

    columns = {
        COL["owner"]: {"personsAndTeams": [{"id": cfg["owner_id"], "kind": "person"}]},
        COL["creative_director"]: {"personsAndTeams": [{"id": cfg["owner_id"], "kind": "person"}]},
        COL["team_leader"]: {"personsAndTeams": [{"id": int(m.get("team_leader_id") or ALBERT_ID), "kind": "person"}]},
        COL["ai_agent"]: {"label": agent},
        COL["iteration_type"]: {"labels": [cfg["iteration_type"]]},
        COL["format"]: {"labels": [cfg["format"]]},
        COL["asset_type"]: {"label": "Video"},
        COL["funnel"]: {"label": funnel_label},
        COL["swimlane"]: {"label": cfg["swimlane"]},
        COL["parent"]: parent,
        COL["ad_copy"]: {"label": ad_copy},
        COL["platform"]: {"label": placement[0]},
        COL["aspect"]: {"label": placement[1]},
        COL["total_versions"]: str(brief["total_versions"]),
        COL["offer"]: {"label": m["offer"]},
        COL["priority"]: {"label": m.get("priority") or current_quarter(today)},
        COL["launch_date"]: {"date": str(m.get("launch_date") or launch_date(today))},
    }
    for key in ("core_profile", "core_angle", "core_message"):
        if m.get(key):
            columns[COL[key]] = {"labels": [m[key]]}

    if schema is not None:
        by_id = {c["id"]: c for c in schema}
        try:
            naming.validate_schema(schema, cfg)
        except ValueError as exc:
            raise Stop(f"live board check: {exc}") from exc
        for cid, value in columns.items():
            if cid in RETIRED:
                raise Stop(f"refusing to write retired column {cid}")
            wanted = None
            if isinstance(value, dict) and "label" in value:
                wanted = value["label"]
            elif isinstance(value, dict) and "labels" in value:
                wanted = value["labels"][0]
            if wanted and wanted not in label_names(by_id[cid]):
                raise Stop(f"{by_id[cid]['title']}: label {wanted!r} does not exist on the board; don't create labels")
        if status not in label_names(by_id["status"]):
            raise Stop(f"status {status!r} not on the board")

    return {"cfg": cfg, "brief": brief, "columns": columns, "status": status, "agent": agent,
            "owner_email": m.get("owner_email") or "", "final_name_preview": naming.build("CO0000", cfg)}


def check_duplicate(name):
    r = monday("""query ($b:[ID!], $n:CompareValue!) { boards(ids:$b) { items_page(limit:20, query_params:{
        rules:[{column_id:"name", compare_value:$n, operator:contains_text}]}) { items { id name } } } }""",
               {"b": [str(BOARD_ID)], "n": name})
    hits = [i for i in r["data"]["boards"][0]["items_page"]["items"]
            if re.sub(r"^CO\d+\s*[—–-]\s*", "", i["name"]).strip() == name.strip()]
    if hits:
        raise Stop(f"a task with this name already exists: {hits[0]['name']} (id {hits[0]['id']})")


# ---------------------------------------------------------------- verify

def verify(item_id, plan, serial, sheet_url):
    cfg = plan["cfg"]
    _, rows = read_item(item_id)
    problems = []
    try:
        naming.verify_rows(rows, cfg, serial)
    except Exception as exc:
        problems.append(str(exc))
    expect = {
        COL["status"]: plan["status"], COL["ad_copy"]: plan["columns"][COL["ad_copy"]]["label"],
        COL["platform"]: plan["columns"][COL["platform"]]["label"],
        COL["aspect"]: plan["columns"][COL["aspect"]]["label"],
        COL["offer"]: plan["columns"][COL["offer"]]["label"],
        COL["total_versions"]: plan["columns"][COL["total_versions"]],
        COL["brief_link"]: sheet_url,
    }
    for cid, want in expect.items():
        if str(rows.get(cid, {}).get("text") or "").strip() != str(want):
            problems.append(f"{cid} reads {rows.get(cid, {}).get('text')!r}, expected {want!r}")
    return problems


def repair(item_id, plan, sheet_url):
    values = dict(plan["columns"])
    values[COL["status"]] = {"label": plan["status"]}
    values[COL["brief_link"]] = {"url": sheet_url, "text": sheet_url}
    set_columns(item_id, values)


# ---------------------------------------------------------------- main flow

def open_task(task, dry_run=False):
    plan = prepare(task, live_schema())
    check_duplicate(plan["cfg"]["concept_name"])
    with tempfile.TemporaryDirectory() as tmp:  # local brief must build and validate before any write
        creative_brief.generate_workbook(plan["brief"], Path(tmp) / "b.xlsx")
        creative_brief.validate_workbook(Path(tmp) / "b.xlsx", payload=plan["brief"])
    if dry_run:
        return {"dry_run": True, "would_open": plan["cfg"]["concept_name"], "status": plan["status"],
                "ai_agent": plan["agent"], "final_name_preview": plan["final_name_preview"],
                "columns": plan["columns"]}

    drive = google_drive()
    folder = os.environ.get("BRIEFS_FOLDER_ID") or DEFAULT_FOLDER
    sheet_id, sheet_url = upload_and_check_sheet(
        drive, plan["brief"], f"PRIVATE — {plan['cfg']['concept_name']} — {time.time_ns()}", folder)
    item_id, linked = None, False
    try:
        owner = {COL["owner"]: plan["columns"][COL["owner"]]}
        item_id = monday("""mutation ($b:ID!, $g:String!, $n:String!, $v:JSON!) { create_item(board_id:$b,
            group_id:$g, item_name:$n, column_values:$v, create_labels_if_missing:false) { id } }""",
                         {"b": str(BOARD_ID), "g": GROUP_ID, "n": plan["cfg"]["concept_name"],
                          "v": json.dumps(owner)})["data"]["create_item"]["id"]
        set_columns(item_id, plan["columns"])
        serial = None
        for i in range(20):
            time.sleep(2 if i < 3 else 4)
            _, rows = read_item(item_id)
            text = str(rows.get(COL["serial"], {}).get("text") or "")
            if re.fullmatch(r"CO\d+", text):
                serial = text
                break
        if not serial:
            raise RuntimeError(f"Monday never gave item {item_id} a serial number")
        monday("""mutation ($i:ID!, $b:ID!, $v:String!) { change_simple_column_value(item_id:$i, board_id:$b,
                  column_id:"name", value:$v) { id } }""",
               {"i": str(item_id), "b": str(BOARD_ID), "v": f"{serial} — {plan['cfg']['concept_name']}"})
        set_columns(item_id, {COL["final_name"]: {"text": naming.build(serial, plan["cfg"])}})
        short = re.sub(r"[^A-Za-z0-9]", "", plan["cfg"]["concept_name"].title())[:60]
        drive.files().update(fileId=sheet_id, body={"name": f"{serial}_CreativeBrief_{short}"},
                             supportsAllDrives=True).execute()
        drive.permissions().create(fileId=sheet_id, body={"type": "anyone", "role": "reader"},
                                   supportsAllDrives=True).execute()
        if plan["owner_email"]:
            drive.permissions().create(fileId=sheet_id, sendNotificationEmail=False, supportsAllDrives=True,
                                       body={"type": "user", "role": "writer", "emailAddress": plan["owner_email"]}).execute()
        set_columns(item_id, {COL["status"]: {"label": plan["status"]}})
        set_columns(item_id, {COL["brief_link"]: {"url": sheet_url, "text": sheet_url}})  # link goes last
        linked = True
        time.sleep(35)  # let board automations finish, then check
        problems = verify(item_id, plan, serial, sheet_url)
        if problems:
            repair(item_id, plan, sheet_url)
            time.sleep(5)
            problems = verify(item_id, plan, serial, sheet_url)
        if problems:
            raise RuntimeError("readback failed after one repair: " + "; ".join(problems))
        return {"serial": serial, "item_id": str(item_id), "sheet_url": sheet_url,
                "monday_url": f"https://coolina.monday.com/boards/{BOARD_ID}/pulses/{item_id}",
                "final_name": naming.build(serial, plan["cfg"])}
    except Exception:
        if not linked:
            trash(drive, sheet_id)
        if item_id:
            print(f"STOPPED after creating Monday item {item_id}. Do not retry blindly; "
                  f"check that item first.", file=sys.stderr)
        raise


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("task", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    try:
        result = open_task(json.loads(args.task.read_text()), dry_run=args.dry_run)
    except Stop as exc:
        print(f"NOT OPENED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
