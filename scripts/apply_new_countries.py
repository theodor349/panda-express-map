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

ROOT         = Path(os.environ.get("EU5_MOD_PATH", Path(__file__).parent.parent))
INPUT_FILE   = ROOT / "mod_changes/new_countries.txt"
LOCALIZATION = ROOT / "main_menu/localization/english/country_names_l_english.yml"
SCRIPT       = Path(__file__).parent / "helpers" / "create_country.py"


def load_existing_names() -> set[str]:
    """Return the set of country names already present in the localization file."""
    if not LOCALIZATION.exists():
        return set()
    raw = LOCALIZATION.read_bytes()
    text = raw[3:].decode("utf-8") if raw.startswith(b"\xef\xbb\xbf") else raw.decode("utf-8")
    return {m.group(1) for m in __import__("re").finditer(r':\s*"([^"]+)"', text)}


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
    existing_names = load_existing_names()

    lines = INPUT_FILE.read_text(encoding='utf-8').splitlines()
    entries = [parse_line(l) for l in lines]
    entries = [e for e in entries if e is not None]

    pending = [(name, args) for name, args in entries if name not in existing_names]
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
