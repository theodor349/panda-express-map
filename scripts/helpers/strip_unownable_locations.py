"""
strip_unownable_locations.py — remove impassable mountains and lakes from country location blocks.

The base game gives these locations no owner, culture, religion or raw material. Assigning a whole
area or province to a country would otherwise give them one.

Usage:
    python scripts/helpers/strip_unownable_locations.py [--file PATH] [--map PATH]
"""

import argparse
import os
import re
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
    load_dotenv(Path(__file__).parent.parent.parent / ".env.local", override=True)
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).parent))
from create_country import write_text_with_retry

_DEFAULT_GAME_PATH = r"E:\SteamLibrary\steamapps\common\Europa Universalis V\game"
_GAME_PATH = Path(os.environ.get("EU5_GAME_PATH", _DEFAULT_GAME_PATH))
_DEFAULT_MOD_PATH = Path(__file__).parent.parent.parent
_MOD_PATH = Path(os.environ.get("EU5_MOD_PATH", _DEFAULT_MOD_PATH))
DEFAULT_MAP = _GAME_PATH / "in_game/map_data/default.map"
DEFAULT_FILE = _MOD_PATH / "main_menu/setup/1337/10_countries.txt"

UNOWNABLE_LISTS = ["impassable_mountains", "lakes"]
LOCATION_BLOCK = re.compile(r"(?m)^([ \t]*(?:own_\w+|control\w*|our_cores\w*)\s*=\s*\{)([^{}]*)(\})")


def load_unownable(map_path: Path) -> set[str]:
    """Return every location in default.map's impassable mountain and lake lists."""
    text = re.sub(r"#[^\n]*", "", map_path.read_text(encoding="utf-8-sig"))
    unownable: set[str] = set()
    for name in UNOWNABLE_LISTS:
        match = re.search(rf"(?m)^{name}\s*=\s*\{{([^{{}}]*)\}}", text)
        if not match:
            sys.exit(f"ERROR: list '{name}' not found in {map_path}")
        unownable.update(match.group(1).split())
    return unownable


def strip_block(body: str, unownable: set[str]) -> tuple[str, int]:
    """Remove unownable locations from a block body, keeping comments and untouched lines as they are."""
    removed = 0
    lines = []
    for line in body.split("\n"):
        code, hash_mark, comment = line.partition("#")
        tokens = code.split()
        kept = [token for token in tokens if token not in unownable]
        if len(kept) == len(tokens):
            lines.append(line)
            continue
        removed += len(tokens) - len(kept)
        if kept or hash_mark:
            indent = code[:len(code) - len(code.lstrip())]
            lines.append(indent + " ".join(kept) + (" " + hash_mark + comment if hash_mark else ""))
    return "\n".join(lines), removed


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove impassable mountains and lakes from country location blocks.")
    parser.add_argument("--file", default=str(DEFAULT_FILE), help="Path to 10_countries.txt")
    parser.add_argument("--map", default=str(DEFAULT_MAP), help="Path to default.map")
    args = parser.parse_args()

    countries_path = Path(args.file)
    map_path = Path(args.map)
    for path in (countries_path, map_path):
        if not path.exists():
            sys.exit(f"ERROR: file not found: {path}")

    unownable = load_unownable(map_path)
    text = countries_path.read_text(encoding="utf-8")
    total = 0

    def replace(match: re.Match) -> str:
        nonlocal total
        body, removed = strip_block(match.group(2), unownable)
        total += removed
        return match.group(1) + body + match.group(3)

    text = LOCATION_BLOCK.sub(replace, text)
    write_text_with_retry(countries_path, text)
    print(f"Removed {total} impassable mountain and lake location(s) from {countries_path.name}.")


if __name__ == "__main__":
    main()
