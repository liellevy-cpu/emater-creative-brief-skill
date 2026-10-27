# Hook / Lead Iteration Brief

Use for Hook Swap, Lead Swap, or Hookstack work where only the opener changes. `parent_serial_number` and `connect_to` are required.

A Lead Swap is formatted exactly like a Hook Swap: place the complete approved lead—including every paragraph—in one version's `hooks[].copy` cell, and put the exact first unchanged source-body line in `connect_to`. Do not split a Lead Swap into hook and body sections, and do not include the unchanged body.

`hooks` contains exactly `total_versions` rows:

```json
{"version":"V1","copy":"...","text_overlay":"...","editor_note":"..."}
```

For every version, `copy` contains only the exact approved spoken words. Visual-only / ASMR / clip-led openers have blank `copy` when there are no spoken words; keep approved shot, sound, or clip instructions in `editor_note` or task-wide `editor_direction`, and approved on-screen words in `text_overlay`. Never use a clip label, shot description, `ASMR: ...`, or `No spoken hook` as copy. Do not invent dialogue or bypass a compiler that rejects a valid blank-copy row; report the limitation instead. This rule also applies to Hook Stack versions.

The workbook renders only those replacement rows and the exact `Connect To` handoff. It must not contain, summarize, or copy the unchanged body. Inherited voice/music details are omitted unless a specific exception belongs in `Editor Direction`.
