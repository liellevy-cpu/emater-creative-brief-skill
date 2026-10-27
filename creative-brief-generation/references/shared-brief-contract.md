# Shared Creative Brief Contract

## Locked workbook shape

Every workbook has exactly three visible worksheets in this order: `Editors`, `Production`, `Media Buyer`. No sheet, row, or column may be hidden. Irrelevant operational areas retain all canonical sections with blank content cells; never use `N/A` or status filler.

Every cell inside each tab's owned rectangular area has a visible thin `#B7C3D0` border on all four sides. These divider lines remain present between adjacent rows and columns even where a content cell is blank.

## Editors

The Editors sheet begins with these labels in this exact order:

1. Writer
2. Brief Type
3. Platform
4. Aspect Ratio
5. Parent Serial Number
6. Total Versions
7. Editor Direction

The title uses `#0A111E`; label cells use `#DDEDF9`; value regions use `#F7F9FF`; section/table headers use `#336BAD`. `Writer` is always the human task opener who prompted the AI agent, never the AI agent. `Total Versions` is left-aligned. `Editor Direction` is blank unless the task opener explicitly supplied or approved a specific exception. New tasks retain the Parent Serial Number row but its value must be blank. New Task detail rows begin immediately below the shared metadata without a separate `NEW TASK DETAILS` section header.

Script-oriented tables use the canonical columns `Version` or `Line`, `Copy` or `Script`, `Text Overlay`, and `Editor Note`. Never infer `Text Overlay`, `Editor Note`, `Editor Direction`, or other execution instructions that the task opener did not explicitly supply or approve; keep those value cells blank. New Task briefs have no UGC Production row. New Task and Policy Improvement contain separate Hooks and Body sections. Hook / Lead Iteration contains only the replacement opener rows and no unchanged body.

`Copy` / `Script` cells contain only exact approved spoken or sung words across all brief types. Approved visual/audio/ASMR/clip/filming/editing instructions belong in `Editor Note`, `Editor Direction`, or the matching Production section—not Copy / Script. Exact approved on-screen words belong in `Text Overlay`. Unspecified directions remain blank.

A visual-only or no-VO opener keeps its version row with Copy blank and approved instructions in the proper fields. This intentional blank Copy is not an unexplained empty row. Never insert `No spoken hook`, a clip label, or a shot/sound description as copy to satisfy validation. If the compiler rejects this valid structure, report the limitation rather than bypassing it. Separate mixed copy/directions before freezing approved source; do not silently rewrite frozen content. Inspect semantic cell contents before publication and after live readback, not only workbook/payload equality.

Masters retain one empty, formatted data row in each relevant variable section. Generated workbooks create exactly the supplied ordered rows; no unexplained empty hook/body/script rows are permitted. These rules apply prospectively; historical-brief repairs require a separate request.

## Production

Every workbook includes, in order:

1. Project Details — Concept Name, Brief ID, Product
2. Creator Shot Sheet — Camera, Orientation, Style, Movement, Setting, Wardrobe, Tone
3. Key Delivery Notes — Notes
4. Master B-Roll Library — permanent guidance plus Link
5. Concept-Specific B-Roll — `#`, `Description`

Masters and irrelevant tabs keep the structure and blank values. Production section headers use `#2E3DB8`; table headers use `#4A58D0`; table rows alternate white and `#F0F1FA`.

## Media Buyer

The sheet has exactly four rows and two columns: dark-blue `#1E3F70` title, one blank spacer, `Primary Text`, and `Ad Headline`. Master and irrelevant values are blank.

## Validation and safety

The generator rejects unknown fields, missing requirements, version-count mismatches, nonblank New Task parent serials, blank New Task music (except AI voiceover tasks, where blank Music is the default), invalid body operations, old/new pairs in orange CHANGE cells, malformed mixing identity, and unapproved AI voiceovers. The validator rejects tab/style/content drift, hidden content, stale rows, forbidden legacy terms, and generated rows that differ from the normalized payload. Master validation rejects likely task, serial, brand, product, or person contamination.

The workflow is compiler-style: normalize payload → generate locally → validate → upload privately → export/read back → validate again. Publishing to Monday or routing this skill into Creative Hermes profiles is a separate, post-Liel-approval phase.
