---
name: Comment syntax in mod data files
description: How comments work in mod data files (new_countries.txt, consolidations, etc.)
type: feedback
---

Data files use two comment forms:

```
# full-line comment
data data # inline comment
```

Parsers must strip everything from `#` to end-of-line before processing tokens. Use `line.partition('#')[0]` or equivalent — do not treat `#` inside quoted strings as a comment (shlex handles this correctly).

**Why:** both forms appear in mod_changes/ input files and must be ignored consistently.

**How to apply:** whenever writing a parser for any mod data file, handle both forms. `shlex.split(line.partition('#')[0])` is the established pattern in this project.
