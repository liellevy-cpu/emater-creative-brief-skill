# Coolina task opener (for outside bots)

Opens a Coolina creative task the same way Emater's agents do (Cole, Camilla, Ivan). The bot already has the approved copy. This tool puts it in the right brief cells and opens the Monday task with the right fields.

It uses the same brief builder (`creative-brief-generation/scripts/creative_brief.py`) and the same Final Name rules (`coolina_initial_naming.py`) as the agents. The checks below run before anything is written. If one fails, nothing is created.

## One-time setup

1. `pip install openpyxl google-api-python-client google-auth pytest` (Python 3.10 or newer)
2. Set these environment variables. Never put their values in a repo or a chat:
   - `MONDAY_API_TOKEN`: the bot's Monday API token.
   - `GOOGLE_CREDENTIALS`: path to a Google credential JSON (service account or signed-in user) that can add files to the **Creative Briefs** folder in Emater's shared drive.
   - `AI_AGENT_LABEL`: the bot's own label in the board's AI Agent column. Emater adds this label for you. The tool refuses to open tasks until the label exists.
3. Run `python3 -m pytest coolina-opener/tests creative-brief-generation/tests -q` once. Everything should pass.
4. Before every task, `git pull` this repo so you have the latest rules.

## Every task

1. Write a `task.json` (copy `example-task.json`).
2. `python3 coolina-opener/open_coolina_task.py task.json --dry-run`. This checks everything against the live board and writes nothing. Fix anything it reports.
3. `python3 coolina-opener/open_coolina_task.py task.json`. It prints the serial, the Monday link and the Sheet link.
4. If it says `STOPPED after creating Monday item ...`, do not run it again. Check that item on the board first.

## task.json: the `brief` part

This is the brief itself. Pick exactly one `brief_type`:

| What the task is | brief_type | Read |
|---|---|---|
| A new ad, no parent | `new-task` | `creative-brief-generation/references/new-task.md` |
| Hook Swap, Hook Stack, Lead Swap | `hook-lead-iteration` | `references/hook-lead-iteration.md` |
| Changing lines in a parent's body | `body-improvement` | `references/body-improvement.md` |
| Combining parts of 2+ ads | `mixing-task` | `references/mixing-task.md` |
| YouTube/platform policy fix | `policy-improvement` | `references/policy-improvement.md` |

Also read `references/shared-brief-contract.md` once. How to place the copy:

- **Copy / Script cells hold only spoken words.** No visual directions, no labels like `[HOOK]`, no `VO:`. If nothing is spoken (music + text overlay ads), leave Copy blank.
- **On-screen words go in `text_overlay`.** Row-specific editing notes go in `editor_note`. Notes for the whole video go in `editor_direction`.
- **One hook per row.** `total_versions` = the number of hooks.
- **`writer`** = the human's first name (e.g. `Lia`), never the bot.
- **`task_title`** must equal `monday.concept_name`.
- **Leave blank** anything the human didn't give you: Product, Editor Direction, Text Overlay, Editor Note, Reference. Never write `N/A`.
- **`music`**: describe what it should sound like (e.g. `Upbeat southern rock`), or exactly `No Music`. With AI voiceover, leave it blank unless the human asked for music.
- **`production_link`**: footage/material links the human supplied. `reference` only when they call it a reference/swipe/inspiration.
- **`media_buyer`**: empty `{}` by default. Fill `primary_text` and `ad_headline` only when the human gave exact ad copy. Then set `monday.ad_copy` to `Check Brief`.
- **Iterations**: `parent_serial_number` is the exact source version, e.g. `CO8561_V1`.

## task.json: the `monday` part

| Field | Required | Value |
|---|---|---|
| `concept_name` | yes | short task name, same as `brief.task_title` |
| `owner_monday_id`, `owner_name` | yes | the human who asked (Lia: `105298787`, `Lia Zucker`). Owner and Creative Director are both set to this person. |
| `owner_email` | no | gives that person edit access to the Sheet |
| `funnel` | yes | `Gifting`, `BIS`, `BBQ`, `BEAST`, `Mystery Bundle`, `2NEW`, `Holiday`, `New Arrivals`, `Unique`, `EVOLVE` |
| `swimlane` | yes | `NEW`, `IMPROVE`, `EXPAND`, `REFRESH` |
| `iteration_type` | yes | `New Video` for a new ad. Iterations: `Hook Swap`, `Hook Stack`, `Lead Swap`, `Body Improvement`, `Mixing Task` (full list in `coolina_initial_naming.py`) |
| `format` | yes | `AI Voiceover`, `Face-to-camera`, `POV — Warehouse/Employee`, `POV — Store`, `POV — Customer/Home`, `Skit/Conversation`, `Song/Music-led`, `Music + text overlay` |
| `parent_serial` | yes | `Pnone` for a new ad, else `PCO####` matching the brief's parent |
| `offer` | yes | a Creative Offer label. Agents' rule: script says "$100 off" → `BFCM $100 OFF`; "$80 off" → `BF $80 OFF`; Black Friday/holiday with no amount → `FreeBoardAndMystery`; otherwise what the human said (default `FreeBoardAndMystery`) |
| `ad_copy` | no | `Default` (normal) or `Check Brief` |
| `status` | no | default `Review - Writing` (same as the agents). Also allowed: `Ready for Production`, `Ready for Post`, `Ready for Editor` |
| `core_profile`, `core_angle`, `core_message` | no | exact board labels, if the human gave them. Otherwise Emater's labeler fills them later. |
| `tags` | no | existing board tags only |

Filled automatically, don't set: Serial Number, Final Name, Priority (current quarter), Target Launch Date (Mon–Wed → this Friday, Thu–Sun → next Wednesday), Team Leader (Albert), Platform/Aspect Ratio (from the brief), Total Versions (from the brief), AI Agent (from `AI_AGENT_LABEL`).

Only three placements are allowed: Meta 9:16, YouTube 16:9, YouTube 9:16.

## Never

- Never create a Sheet or task by hand, or use the old 4-tab template (Strategy/Script/Production/Editing) or a Google Doc brief.
- Never set or change a Serial Number.
- Never create new Monday labels. If a label is missing, ask the human.
- Never guess a required field. Ask the human.
- Never write the retired Avatar, Angle or Primary Format columns.
