---
name: creative-brief-generation
description: Use when creating or validating standardized cross-brand creative brief workbooks for new tasks and approved iteration types.
version: 1.1.1
author: Emater
license: Proprietary
metadata:
  hermes:
    tags: [creative-briefs, xlsx, validation, production]
    related_skills: [creative-operations-systems]
---

# Creative Brief Generation

## Coolina video task-opening metadata — scoped EDITING REVIEW prerequisite
The creating agent, not the human, gathers and writes required board metadata through its own guarded publisher. Human Owner/requester and actual AI Agent stay separate. Require evidence-backed explicit PCOdigits/Pnone, exactly one Iteration Type, one of the seven approved Primary Formats, Video Asset Type, board Funnel, Swimlane, Avatar and Angle; new task output starts v1, never hook count. Retrieve verified values first and ask only for genuinely unknown decisions. Optional blank brief fields below do not make required Monday metadata optional. Validate before remote creation/write and read back required columns after creation. Company pure metadata utility remains `scripts/coolina_initial_naming.py`; it is not a publisher or workflow trigger. Existing EDITING REVIEW workflow 18434960853 stays untouched; cancelled initial workflow/draft 18434990272 must not be enabled. No other-brand, non-video, status, filename-trigger or historical changes are authorized by this prerequisite.

## Overview

This is the company-wide structural source of truth for creative brief workbooks. It generates clean local masters or task-specific workbooks from strict JSON and validates tabs, labels, content, colors, row counts, contamination, and exact payload readback.

Supported types:

- `new-task`
- `policy-improvement`
- `hook-lead-iteration`
- `body-improvement`
- `mixing-task`

Read `references/shared-brief-contract.md`, then the matching type reference.

## When to Use

Use for any full creative brief that needs a Google Sheet. Do not use this skill for lightweight Monday Description-only adjustments, Monday board redesign, or profile rollout. Publishing is allowed only after local validation and must be followed by live export/readback validation.

## Liel-Approved New Task Rules

Apply these rules to every `new-task` brief:

1. `Writer` is the human who prompted the AI agent. Never put the AI agent's name in this field.
2. `Total Versions` equals the number of hook versions and its value cell is left-aligned.
3. New Task detail rows begin directly below the shared metadata. Do not add a `NEW TASK DETAILS` separator.
4. Keep `Product` blank unless the human task opener explicitly specifies the product for the brief.
5. Do not include a UGC Production row.
6. Keep `Editor Direction`, every `Text Overlay`, and every `Editor Note` blank unless the task opener explicitly supplies or approves those directions.
7. Describe Music only in positive terms: what it should sound or feel like. Do not add negative instructions. Use exactly `No Music` when that is the direction.
   - **AI voiceover default (Liel, 2026-10-18):** when `generate_ai_vo` is true (e.g. Coolina AI Voiceover briefs), leave `music` blank (`""`) unless the requester specifies music. Do not propose, infer, or copy a music direction and do not ask for one. Non-AI-VO New Tasks still need a positive description or exactly `No Music`.
8. Put supplied footage, asset, or material links in `Production Link`.
9. Populate `Reference` only when the task opener explicitly calls the supplied item a reference, inspiration, or swipe.
10. Do not infer a field from the concept, script, link, or brand context merely because it seems obvious.

## Copy / Script contains spoken words only — Liel-approved forward rule

Applies to all five brief types, including visual-only, ASMR, no-VO, Hook Stack, Hook Swap, and Lead Swap work.

- Every `copy` / `script` value contains only the exact approved words spoken or sung in the ad. Never put visual, audio, filming, performance, editing, clip-selection, source-reference, or timing instructions in these cells, even if those instructions were approved.
- Keep approved spoken wording unchanged. Do not strip ambiguous annotations from a frozen approved source or invent dialogue to fill a row. Separate copy and instructions before freezing the approval source; unresolved mixed content returns for clarification before publication.
- Put exact approved on-screen wording in `text_overlay`. Put approved row-specific visual/audio/clip instructions in `editor_note`, task-wide editing instructions in `editor_direction`, and shoot instructions in the matching Production section. Do not invent directions or populate unspecified fields.
- For a visual-only or ASMR opener with no spoken words, leave `copy` blank. Keep the version row and its approved instructions in the proper fields. Do not write `No spoken hook`, `ASMR: crunchy bark slice`, `Zac Smoke Show viral clip #1`, or a pitmaster shot description in Copy. Blank Copy is intentional, not a missing script to reconstruct.
- If the current compiler rejects a valid no-spoken-copy row, report the exact limitation. Never bypass it by stuffing instructions into Copy, writing filler, or hand-rolling a brief.
- Before publication and after live readback, inspect every populated Copy / Script cell for non-spoken content. Matching a payload is not sufficient if that payload already contains instructions in copy. Do not publish/link a brief that fails this check.

Routing examples:

| Approved content | Copy / Script | Correct instruction field |
|---|---|---|
| ASMR: crunchy bark slice; no spoken hook | blank | Editor Note: exact approved ASMR/shot instruction |
| Zac Smoke Show viral clip #1 | blank unless exact spoken clip words are supplied | Editor Note: approved clip reference |
| Pitmaster slicing picanha for a crowd | blank | Editor Note or Production: approved shot direction |
| Spoken line plus `[show product]` or `SFX: knife chop` | exact approved spoken words only | Editor Note / Production: approved direction, separated before source freezing |

This change governs future briefs. Do not repair or backfill existing briefs without a separate request.

## Local CLI

```bash
SKILL=emater/skills/creative-brief-generation

python3 "$SKILL/scripts/creative_brief.py" create-masters \
  --output-dir emater/projects/EMATER-2026-09-CreativeBriefStandardization/previews

python3 "$SKILL/scripts/creative_brief.py" generate \
  --payload /path/to/payload.json \
  --output /path/to/brief.xlsx

python3 "$SKILL/scripts/creative_brief.py" validate \
  --workbook /path/to/brief.xlsx \
  --payload /path/to/payload.json

python3 "$SKILL/scripts/creative_brief.py" validate \
  --workbook /path/to/master.xlsx \
  --master --brief-type new-task

# Only for an XLSX exported back from Google Sheets:
python3 "$SKILL/scripts/creative_brief.py" validate \
  --workbook /path/to/google-readback.xlsx \
  --payload /path/to/payload.json \
  --google-roundtrip
```

Every command prints JSON and exits nonzero on schema or validation failure.

## Shared Payload

```json
{
  "task_title": "Task title",
  "writer": "Writer name",
  "brief_type": "new-task",
  "platform": "Meta",
  "aspect_ratio": "9:16",
  "parent_serial_number": "",
  "total_versions": 2,
  "editor_direction": "",
  "hooks": [
    {"version":"V1","copy":"...","text_overlay":"...","editor_note":"..."},
    {"version":"V2","copy":"...","text_overlay":"...","editor_note":"..."}
  ],
  "body": [
    {"line":1,"script":"...","text_overlay":"...","editor_note":"..."}
  ]
}
```

New Task and Policy Improvement use `hooks` plus `body`. Hook / Lead Iteration uses `hooks` only. Body Improvement and Mixing Task use `versions`, each containing ordered `rows`. See the type references for exact fields.

`writer`, `platform`, and `aspect_ratio` are required. `writer` is the human task opener who prompted the AI agent, never the AI agent's name. New Task parent must be blank. Iterations require an exact version-level parent ending in `_V#`. Counts must match. Unknown or type-irrelevant fields fail closed.

For AI voiceover, `generate_ai_vo: true` requires:

```json
{
  "voiceover": {
    "accent": "US",
    "age": "30-40",
    "gender": "Female",
    "style": "Warm",
    "approved": true
  }
}
```

Gender is exactly `Male` or `Female` and must be explicitly approved by the task opener. The generator never invents voice details.

## Compiler Workflow

1. Classify exactly one approved brief type.
2. Build one strict structured payload from approved content. Do not infer Product, Text Overlay, Editor Note, Editor Direction, or other execution instructions; unspecified values stay blank. Put supplied asset/material links in Production Link. Use Reference only when the task opener explicitly identifies a reference, inspiration, or swipe.
3. Generate locally from a clean contract—not by editing an old task Sheet.
4. Validate locally against the exact payload.
5. Upload privately to the canonical Drive area.
6. Export the live Google Sheet back to XLSX.
7. Validate the exported readback against the same payload.
8. Only then return/link the Sheet.
9. Monday task creation and Creative Hermes profile rollout remain separate gates.

On any failure, quarantine or trash the disposable copy and report the exact error. Never publish a nearly-correct brief.

Local validation remains exact. Explicit `--google-roundtrip` mode still compares all content, tabs, visible colors, nondefault fonts, number formats, borders, alignment, merged cells, freeze panes, and visibility, while allowing only Google Sheets' deterministic dimension quantization (up to 2.5 units), exporter-only default dimensions outside the owned range, and omission of the visually identical default 11pt font size on blank cells after border-only formatting.

## Self-Test

```bash
python3 -m pytest emater/skills/creative-brief-generation/tests/test_creative_brief.py -q
```

## Common Pitfalls

1. Never remove an irrelevant tab or write `N/A`; preserve all sections and leave content cells blank.
2. Never add unrequested Product, Text Overlays, Editor Notes, Editor Direction, or other production/editing instructions. Unspecified values stay blank. New Task has no UGC Production row.
3. Write Music as a positive description of the desired sound (or exactly `No Music`), never as a list of what to avoid. AI voiceover New Tasks leave Music blank unless the requester specified it.
4. Preserve the thin visible borders between every adjacent row and column throughout each owned tab area.
5. Never paste an unchanged body into a Hook / Lead Iteration.
6. Never omit the `Text Overlay` column from script tables; its values may be blank when unspecified.
7. Body operation color belongs on the Script cell; orange CHANGE holds only the new version.
8. Mixing Script cells stay neutral; source identity belongs in `Editor Note`.
9. Mixing Task `Editor Direction` stays blank unless the human task opener explicitly provides a direction. Never insert a generic source-visual instruction automatically.
10. Do not manually append rows after generation; regenerate from the payload.
11. Do not use a populated task as a master.
12. Do not create a Monday task or change profiles before the live Sheet passes readback.

## Verification Checklist

- [ ] Exactly three visible tabs in order: Editors, Production, Media Buyer
- [ ] Shared labels and terminology are exact
- [ ] Writer is the human task opener, not the AI agent
- [ ] Total Versions matches hook count and is left-aligned
- [ ] New Task has no details separator and no UGC Production row
- [ ] Unspecified Product, Editor Direction, Text Overlay, and Editor Note values are blank
- [ ] Music is positive-only (blank on AI voiceover briefs unless specified); asset links and references are routed by the approved rules
- [ ] Mixing Task Editor Direction is blank unless explicitly supplied
- [ ] Thin visible borders separate every row and column in each owned tab area
- [ ] Hooks/Body/Text Overlay/Editor Note structure matches the selected type
- [ ] Production retains all five standard sections
- [ ] Media Buyer contains only Primary Text and Ad Headline
- [ ] No stale task content, old terminology, hidden rows, or unexplained empty rows
- [ ] Local workbook validates against the payload
- [ ] Google export/readback validates against the same payload
- [ ] No Monday or profile rollout occurred without the separate approval gate
