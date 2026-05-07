"""
set_resource.py — change the raw_material of a location in location_templates.txt.

Usage:
    python set_resource.py <location> <resource>

Edits the mod's copy of location_templates.txt in-place. If the mod copy does not
exist yet, copies the base game file first.
"""

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
    load_dotenv(Path(__file__).parent.parent.parent / ".env.local", override=True)
except ImportError:
    pass

_DEFAULT_GAME_PATH = r"C:\Program Files (x86)\Steam\steamapps\common\Europa Universalis V\game"
_GAME_PATH = Path(os.environ.get("EU5_GAME_PATH", _DEFAULT_GAME_PATH))
_DEFAULT_MOD_PATH = Path(__file__).parent.parent.parent
_MOD_PATH = Path(os.environ.get("EU5_MOD_PATH", _DEFAULT_MOD_PATH))

TEMPLATES_REL = Path("in_game") / "map_data" / "location_templates.txt"
GAME_TEMPLATES = _GAME_PATH / TEMPLATES_REL
MOD_TEMPLATES = _MOD_PATH / TEMPLATES_REL


def ensure_mod_file() -> None:
    if not MOD_TEMPLATES.exists():
        if not GAME_TEMPLATES.exists():
            sys.exit(f"ERROR: base game file not found at {GAME_TEMPLATES}")
        MOD_TEMPLATES.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(GAME_TEMPLATES, MOD_TEMPLATES)
        print(f"Copied base game file to {MOD_TEMPLATES}")


_LINE_RE = re.compile(r'^(\w+)\s*=\s*\{([^}]*)\}')
_RAW_MAT_RE = re.compile(r'\braw_material\s*=\s*\w+')


def set_resource(location: str, resource: str) -> None:
    replacement = f'raw_material = {resource}'
    found = False
    lines: list[str] = []

    with MOD_TEMPLATES.open(encoding="utf-8") as f:
        for line in f:
            if not found:
                m = _LINE_RE.match(line)
                if m and m.group(1) == location:
                    body = m.group(2)
                    if _RAW_MAT_RE.search(body):
                        new_body = _RAW_MAT_RE.sub(replacement, body)
                    else:
                        new_body = body.rstrip() + f' {replacement}'
                    line = f'{location} = {{{new_body}}}\n'
                    found = True
            lines.append(line)

    if not found:
        sys.exit(f"ERROR: location '{location}' not found in {MOD_TEMPLATES}")

    MOD_TEMPLATES.write_text("".join(lines), encoding="utf-8")
    print(f"Set {location} raw_material = {resource}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Set the raw_material of a location.")
    parser.add_argument("location", help="Location ID (e.g. villafranca_bierzo)")
    parser.add_argument("resource", help="Resource name (e.g. silver)")
    args = parser.parse_args()

    ensure_mod_file()
    set_resource(args.location, args.resource)


if __name__ == "__main__":
    main()
