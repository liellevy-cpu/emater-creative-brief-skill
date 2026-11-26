"""Offline checks for the Coolina opener. No network, no credentials."""
import copy
import datetime as dt
import json
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import open_coolina_task as op  # noqa: E402

EXAMPLE = json.loads((HERE.parent / "example-task.json").read_text())


@pytest.fixture(autouse=True)
def agent(monkeypatch):
    monkeypatch.setenv("AI_AGENT_LABEL", "Cole 2.4")  # any label already in the company naming list


def task(**monday):
    t = copy.deepcopy(EXAMPLE)
    t["monday"].update(monday)
    return t


def test_example_builds_the_same_final_name_shape_as_the_agents():
    plan = op.prepare(task(), today=dt.date(2026, 11, 26))
    assert plan["final_name_preview"] == (
        "CO0000_v1_BBQEnthusiastTestImpressHisGuests_Pnone_BBQ_SwNew_NewVideo_TBD_TBD_TBD_"
        "FmtMusictextoverlay_Video_OwnLiaZucker_ColeAgent2.4_EdtTBD")
    cols = plan["columns"]
    assert cols[op.COL["ai_agent"]] == {"label": "Cole 2.4"}
    assert cols[op.COL["ad_copy"]] == {"label": "Default"}
    assert cols[op.COL["launch_date"]] == {"date": "2026-12-02"}  # Thursday -> next Wednesday
    assert cols[op.COL["priority"]] == {"label": "Q4"}
    assert cols[op.COL["aspect"]] == {"label": "9x16 (4x5 safe)"}
    assert plan["status"] == "Review - Writing"


@pytest.mark.parametrize("field", ["funnel", "swimlane", "iteration_type", "format", "parent_serial", "offer"])
def test_missing_field_stops(field):
    with pytest.raises(op.Stop):
        op.prepare(task(**{field: ""}))


def test_writer_must_be_the_human():
    t = task()
    t["brief"]["writer"] = "GrokBot"
    with pytest.raises(op.Stop, match="writer"):
        op.prepare(t)


def test_new_task_needs_pnone_and_iteration_needs_matching_parent():
    with pytest.raises(op.Stop):
        op.prepare(task(parent_serial="PCO123"))


def test_ad_copy_default_rejects_media_buyer_copy():
    t = task()
    t["brief"]["media_buyer"] = {"primary_text": "Buy now", "ad_headline": "Sharp"}
    with pytest.raises(op.Stop, match="Default"):
        op.prepare(t)


def test_unknown_format_or_old_swimlane_stops():
    with pytest.raises(op.Stop):
        op.prepare(task(format="UGC"))
    with pytest.raises(op.Stop):
        op.prepare(task(swimlane="Net New"))


def test_bad_brief_stops_before_any_write():
    t = task()
    t["brief"]["hooks"][0]["copy"] = "N/A"
    with pytest.raises(op.Stop, match="brief"):
        op.prepare(t)


def test_missing_agent_label_stops(monkeypatch):
    monkeypatch.delenv("AI_AGENT_LABEL")
    with pytest.raises(op.Stop, match="AI_AGENT_LABEL"):
        op.prepare(task())
