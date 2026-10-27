# New Task Brief

Use for a net-new concept. `parent_serial_number` must be blank.

Required task fields: `product`, `generate_ai_vo`, optional approved `voiceover`, `music`, `production_link`, and `reference`. `product` stays blank unless the task opener explicitly specifies it. `music` must positively describe the desired genre/vibe/style or be exactly `No Music`; do not describe what the music should not sound like. Exception (Liel, 2026-10-18): when `generate_ai_vo` is true, `music` defaults to blank (`""`) and stays blank unless the requester specifies music; the key is still present in the payload. New Task briefs do not contain a UGC Production row.

New Task detail fields begin immediately below the shared metadata. Do not insert a `NEW TASK DETAILS` separator row.

`hooks` contains exactly `total_versions` rows:

```json
{"version":"V1","copy":"...","text_overlay":"...","editor_note":"..."}
```

`body` contains one or more ordered rows:

```json
{"line":1,"script":"...","text_overlay":"...","editor_note":"..."}
```

The Editors sheet renders separate Hooks and Body sections. Captions are the default and are not repeated as generic filler. `Editor Direction`, `Text Overlay`, and `Editor Note` remain blank unless the task opener explicitly supplied or approved those directions. Never infer production or editing instructions from the script alone. `writer` is the human task opener who prompted the AI agent, never the AI agent's name. Put supplied asset/material links in `production_link`; populate `reference` only when the task opener explicitly calls the item a reference, inspiration, or swipe.

When `generate_ai_vo` is true, voiceover details require accent, age, style, explicit `Male` or `Female`, and boolean approval `true`. The agent must obtain that approval rather than infer it.
