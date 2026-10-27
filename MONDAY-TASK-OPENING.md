# Opening Coolina Monday tasks the way Cole does

For Maor's Claude Code agent. Read `creative-brief-generation/SKILL.md` first. This page covers only the Monday side.

## The brief (the part that was wrong)

- Build the brief with `creative-brief-generation/scripts/creative_brief.py` (`generate`, then `validate`). Do NOT use the old 4-tab template (Strategy / Script / Production / Editing).
- The Sheet must have exactly 3 tabs, in this order: **Editors, Production, Media Buyer**.
- Pick exactly one brief type: `new-task`, `policy-improvement`, `hook-lead-iteration`, `body-improvement`, `mixing-task`.
- `writer` = the human who asked (e.g. `Maor`), never the AI.
- Leave Product, Editor Direction, Text Overlay and Editor Note blank unless Maor gave them. Copy cells hold spoken words only.
- Upload the xlsx to Google Drive as a Google Sheet, export it back, and run `validate --google-roundtrip` against the same payload. Only then put the link on Monday.
- Share the Sheet "anyone with the link can view".

## The Monday task (board 9298353728, Coolina Creative Development Pipeline)

Fill these before you call it done, then read them back:

| Column | Column ID | Value |
|---|---|---|
| Group | `topics` (New Concepts) | new tasks start here |
| Status | `status` | `Review - Writing` |
| Owner | `multiple_person_mkscqwjv` | Maor (the human who asked) |
| Creative Director | `person` | Maor |
| AI Agent | `color_mm4h23be` | `ClaudeCode` |
| Iteration Type | `dropdown_mkskhreg` | exactly one, e.g. `NetNew`, `New Video`, `Mixing Task`, `Hook Swap`, `Hook Stack`, `Lead Swap`, `Body Improvement` |
| Format | `dropdown_mm14rmx0` | exactly one of: `AI Voiceover`, `Face-to-camera`, `POV — Warehouse/Employee`, `POV — Store`, `POV — Customer/Home`, `Skit/Conversation`, `Song/Music-led` |
| Asset Type | `color_mkrxa713` | `Video` |
| Funnel | `color_mm3y9jqt` | `2NEW`, `BIS`, `BBQ`, `BEAST`, `Mystery Bundle`, `Holiday`, `New Arrivals`, `Unique` |
| Swimlane | `color_mkrxsgqr` | `NEW`, `IMPROVE`, `EXPAND`, `REFRESH` |
| Parent Serial Number | `text_mkrxd768` | `Pnone` for a brand-new idea, or `PCO1234` for the parent ad |
| Creative Brief Link | `link_mks5pgae` | the Google Sheet link, text `COxxxx Brief` |
| Ad Copy | `color_mm6dhpz` | `Default`, or `Check Brief` when the Media Buyer tab has copy |
| Platform | `color_mkts761t` | usually `Meta` |
| Aspect Ratio | `color_mkrxkpcp` | usually `9x16 (4x5 safe)` |
| Total Versions | `numeric_mkrxw6rb` | number of hook versions |
| Creative Offer | `color_mkrxt6yp` | e.g. `FreeBoardAndMystery` |

Leave alone (filled automatically): Serial Number, Final Name, Core Profile / Core Angle / Core Message. Never write the retired Avatar or Angle columns.

## Order of steps

1. Get every value above. If one is unknown, ask Maor. Don't guess.
2. Check the board for a task with the same name, so you don't make a duplicate.
3. Create the item, then wait for Monday to give it a Serial Number (COxxxx).
4. Build, upload and validate the brief named `COxxxx_CreativeBrief_<ShortTitle>`.
5. Set the Brief Link last, then read back every column in the table above.

## Not included here

Cole's own publisher script, tokens and the rest of the company repo are not part of this share. Use your own Monday and Google access.
