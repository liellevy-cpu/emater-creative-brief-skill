# Mixing Task Brief

Use when composing a final edit in sequence from a base creative, one or more mix-ins, and/or blended rewrites. `parent_serial_number` is required. `versions.length` equals `total_versions`.

Keep the shared `Editor Direction` value blank unless the task opener explicitly provides a direction for the editor. Do not insert a generic instruction to use winning visuals from the source scripts.

Each version contains final-edit-order rows:

```json
{"version":"V1","rows":[{"line":1,"script":"...","text_overlay":"...","source":"mix-in","source_parent_serial_number":"CO1234_V2","exact_source_version":"CO1234_V2","editor_direction":"Insert here."}]}
```

Script cells remain neutral. `Editor Note` carries the keyed source identity:

- `🟩 Base`
- `🟥 Mix-in / [Parent Serial Number]`
- `🟨 Blended rewrite`

Any row-specific direction follows the marker in the same Editor Note cell. The base `exact_source_version` must equal the top-level Parent Serial Number; a mix-in's `exact_source_version` must equal its version-specific `source_parent_serial_number`. This preserves exact identity without adding a second visible marker. The visible legend uses the same marker language.
