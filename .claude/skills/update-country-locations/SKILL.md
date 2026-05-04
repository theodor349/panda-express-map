---
description: Update a country's location blocks in 10_countries.txt, ensuring no locations appears in more than one country. Use when creating or modifying a country's territory.
---

# Update Country Locations

The user wants to set or modify the locations belonging to a country in:
`main_menu/setup/start/10_countries.txt`

## Location block types (listed at top of file)
- `own_control_core` — normal sovereign territory (most common)
- `own_control_integrated` — integrated locations
- `own_control_conquered` — recently conquered
- `own_control_colony` — colonies
- `own_core` / `own_conquered` / `own_integrated` / `own_colony` — without control
- `control_core` / `control` — control without ownership
- `our_cores_conquered_by_others` — cores held by another country (non-sovereign starts)

## Steps

1. **Identify the target country** from the user's request (3-letter tag, e.g. `TRA`).

2. **Determine the desired locations** — either from user input, or infer from context (region, history).

3. **Scan for conflicts**: For every location the user wants to assign to the target country, grep the file to find if that location already appears inside any other country's location block. Report any conflicts found.

4. **Resolve conflicts**: For each conflicting location, remove it from the other country's block. If removing it leaves a block with only whitespace/empty, remove the entire block keyword too.

5. **Update target country**: Find the target country's block (`TAG = {`) and update or add the appropriate location block(s) with the new location list. Preserve comments on location lines if they exist.

6. **Verify**: After edits, grep for each changed location to confirm it now appears exactly once across all country blocks in the file.

7. **Report**: Summarise what was added, what was removed from other countries, and list any locations that were already correctly assigned (no change needed).

## Rules
- Never duplicate a location across two countries.
- Preserve all other fields in each country block (government, technology, includes, etc.).
- Keep inline comments (e.g. `#doboka_location`) on the same line as the locations they annotate.
- When the user says "make X a normal country", use `own_control_core`.
