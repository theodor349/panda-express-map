"""
apply_new_countries.py

Reads mod_changes/new_countries.txt and dispatches each line to create_country.py.

Line format (produced by generate_new_countries.py):
  "Name" "NameAdj" --tag TAG --region REGION [--provinces p1 p2] [--locations l1 l2]

The --tag from the file is ignored; create_country.py auto-generates a fresh tag.
"""

import os
import subprocess
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    load_dotenv(Path(__file__).parent.parent / ".env.local", override=True)
except ImportError:
    pass

ROOT       = Path(os.environ.get("EU5_MOD_PATH", Path(__file__).parent.parent))
INPUT_FILE = ROOT / "mod_changes/new_countries.txt"
SCRIPT     = Path(__file__).parent / "helpers" / "create_country.py"


def parse_line(line: str) -> list[str] | None:
    import shlex
    line = line.strip()
    if not line or line.startswith('#'):
        return None

    tokens = shlex.split(line.partition('#')[0])
    args = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == '--tag':
            i += 2  # skip --tag and its value
        elif tok.startswith('--'):
            args.append(tok)
            i += 1
            # collect subsequent non-flag values
            while i < len(tokens) and not tokens[i].startswith('--'):
                args.append(tokens[i])
                i += 1
        else:
            i += 1

    return args if args else None


def main():
    lines = INPUT_FILE.read_text(encoding='utf-8').splitlines()
    total = sum(1 for l in lines if l.strip() and not l.strip().startswith('#'))
    print(f"Applying {total} countries from {INPUT_FILE.name}\n")

    ok = 0
    for lineno, line in enumerate(lines, 1):
        args = parse_line(line)
        if args is None:
            continue

        cmd = [sys.executable, str(SCRIPT)] + args
        print(f"=== [{ok+1}/{total}] {' '.join(args)} ===")
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode != 0:
            print(f"ERROR on line {lineno}: {line}", file=sys.stderr)
            sys.exit(1)
        ok += 1

    print(f"\nAll {ok} countries applied successfully.")


if __name__ == '__main__':
    main()
