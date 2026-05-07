# Memory Index

- [Comment syntax in mod data files](feedback_comment_syntax.md) — both `# line` and `data # inline` forms must be stripped; use `shlex.split(line.partition('#')[0])`
- [Always copy full base game file before modifying](feedback_copy_base_game_files.md) — EU5 replaces entire files; copy base game first, then append mod additions
