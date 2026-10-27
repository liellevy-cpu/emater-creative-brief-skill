# Body Improvement Brief

Use when changing selected body lines in an existing creative. `parent_serial_number` is required. `versions.length` must equal `total_versions`.

Each version contains ordered rows:

```json
{"version":"V1","rows":[{"line":1,"operation":"change","script":"new version only","text_overlay":"...","editor_note":"..."}]}
```

Allowed operations:

- ADD — Script fill `#93C47D`
- REMOVE — Script fill `#E06666`
- CHANGE — Script fill `#F6B26B`
- UNCHANGED — neutral Script fill

The visible legend is permanent. Orange CHANGE Script cells contain only the new version, never an old/new pair. `Text Overlay` and `Editor Note` retain their canonical columns.
