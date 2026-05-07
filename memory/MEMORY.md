# Memory Index

- [Comment syntax in mod data files](feedback_comment_syntax.md) — both `# line` and `data # inline` forms must be stripped; use `shlex.split(line.partition('#')[0])`
