"""
apply_new_countries.py

Reads mod_changes/new_countries.txt and dispatches each line to create_country.py.

Line format (produced by generate_new_countries.py):
  --name "Name" --name-adj "NameAdj" --region REGION
  [--provinces p1 p2] [--locations l1 l2] [--capital LOCATION] [--culture CULTURE]
  [--base-tag TAG]

A line with --base-tag gives the land to that existing base game country.

The --tag from the file is ignored. A country already in panda_express_map.txt keeps
its tag and color; otherwise create_country.py auto-generates a fresh tag.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    load_dotenv(Path(__file__).parent.parent / ".env.local", override=True)
except ImportError:
    pass

ROOT         = Path(os.environ.get("EU5_MOD_PATH", Path(__file__).parent.parent))
INPUT_FILE   = Path(__file__).parent.parent / "mod_changes/new_countries.txt"
COUNTRIES    = ROOT / "main_menu/setup/1337/10_countries.txt"
DEFINITIONS  = ROOT / "in_game/setup/countries/panda_express_map.txt"
SCRIPT      = Path(__file__).parent / "helpers" / "create_country.py"


def load_pinned_countries() -> dict[str, tuple[str, list[str]]]:
    """Return {name: (tag, [r, g, b])} from the mod's definitions so rebuilds keep tags and colors."""
    if not DEFINITIONS.exists():
        return {}
    text = DEFINITIONS.read_text(encoding="utf-8-sig")
    pattern = r"^([A-Z0-9]{3})\s*=\s*\{\s*#\s*(.+?)\s*\n\s*color\s*=\s*rgb\s*\{\s*(\d+\s+\d+\s+\d+)\s*\}"
    return {m.group(2): (m.group(1), m.group(3).split()) for m in re.finditer(pattern, text, re.MULTILINE)}


def load_existing_tags() -> set[str]:
    """Return the set of tags that already have a block in 10_countries.txt."""
    if not COUNTRIES.exists():
        return set()
    text = COUNTRIES.read_text(encoding="utf-8-sig")
    return set(re.findall(r"^\t([A-Z0-9]{3})\s*=\s*\{", text, re.MULTILINE))


def parse_line(line: str) -> tuple[str, list[str]] | None:
    """Return (name, args) for a valid entry line, or None to skip."""
    import shlex
    line = line.strip()
    if not line or line.startswith('#'):
        return None

    tokens = shlex.split(line.partition('#')[0])
    name = None
    args = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == '--tag':
            i += 2  # skip --tag and its value
        elif tok.startswith('--'):
            values = []
            i += 1
            while i < len(tokens) and not tokens[i].startswith('--'):
                values.append(tokens[i])
                i += 1
            if tok == '--name' and values:
                name = values[0]
            args.append(tok)
            args.extend(values)
        else:
            i += 1

    return (name, args) if name and args else None


def main():
    # Country names can hold letters the Windows console encoding can't print.
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    pinned = load_pinned_countries()
    existing_tags = load_existing_tags()

    lines = INPUT_FILE.read_text(encoding='utf-8').splitlines()
    entries = [parse_line(l) for l in lines]
    entries = [e for e in entries if e is not None]

    pending = []
    for name, args in entries:
        if name in pinned:
            tag, color = pinned[name]
            if tag in existing_tags:
                continue
            args = args + ['--tag', tag]
            if '--color' not in args:
                args = args + ['--color', *color]
        pending.append((name, args))
    skipped = len(entries) - len(pending)

    print(f"Found {len(entries)} entries — {skipped} already present, {len(pending)} to apply.\n")

    if not pending:
        print("Nothing to do.")
        return

    for i, (name, args) in enumerate(pending, 1):
        print(f"=== [{i}/{len(pending)}] {name} ===")
        result = subprocess.run([sys.executable, str(SCRIPT)] + args, capture_output=False)
        if result.returncode != 0:
            print(f"ERROR applying '{name}'", file=sys.stderr)
            sys.exit(1)

    print(f"\nAll {len(pending)} countries applied successfully.")


if __name__ == '__main__':
    main()
