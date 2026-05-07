---
name: Always copy full base game file before modifying
description: When adding to any base game file, copy the full original first — the game replaces entire files, not individual entries
type: feedback
---

Always copy the full base game file to the mod path, then append or modify. Never create a new file with only the mod additions.

**Why:** EU5 replaces the entire file, not individual entries. A mod file with only new content will overwrite the base game file, removing all vanilla data and causing crashes.

**How to apply:** For any file the mod needs to extend (e.g. 05_characters.txt, 10_countries.txt), copy the base game version first (`head -n -1` to strip the closing brace), then append the new content and re-close the block.
