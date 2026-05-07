"""
get_locations.py — resolve a geography name to its list of locations.

Usage:
    python get_locations.py <name> [--definitions PATH]

The name can be a continent, sub-continent, region, area, province, or individual
location as defined in definitions.txt. Match is case-insensitive; trailing
suffixes like _area, _region, _province, _sub_continent are optional.

Prints one location per line to stdout so output can be piped to other tools.
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

_DEFAULT_GAME_PATH = r"C:\Program Files (x86)\Steam\steamapps\common\Europa Universalis V\game"
_GAME_PATH = Path(os.environ.get("EU5_GAME_PATH", _DEFAULT_GAME_PATH))
DEFINITIONS = _GAME_PATH / r"in_game\map_data\definitions.txt"

# Suffixes appended to geography names in the file that users may omit.
GEO_SUFFIXES = ["_continent", "_sub_continent", "_region", "_area", "_province"]


def parse_definitions(path: Path) -> dict[str, list[str]]:
    """
    Parse definitions.txt into a flat dict mapping every geography name
    (continent, sub-continent, region, area, province) to its flat list
    of leaf locations.
    """
    text = re.sub(r'#[^\n]*', '', path.read_text(encoding="utf-8"))
    geo: dict[str, list[str]] = {}
    stack: list[tuple[str, list[str]]] = []  # (name, locations_list)

    token_re = re.compile(r'(\w+)\s*=\s*\{|\}|(\w+)')

    for m in token_re.finditer(text):
        block_name, leaf = m.group(1), m.group(2)
        if block_name:
            locations: list[str] = []
            geo[block_name] = locations
            stack.append((block_name, locations))
        elif leaf:
            # leaf location — add to all ancestor blocks and register itself
            for _, loc_list in stack:
                loc_list.append(leaf)
            if leaf not in geo:
                geo[leaf] = [leaf]
        else:
            # closing brace
            if stack:
                stack.pop()

    return geo


def normalise(name: str) -> str:
    return name.lower().strip()


def find_name(geo: dict[str, list[str]], query: str) -> list[str] | None:
    q = normalise(query)
    # Exact match first
    for key in geo:
        if normalise(key) == q:
            return geo[key]
    # Try appending known suffixes
    for suffix in GEO_SUFFIXES:
        candidate = q + suffix
        for key in geo:
            if normalise(key) == candidate:
                return geo[key]
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve a geography name to locations.")
    parser.add_argument("name", help="Continent/sub-continent/region/area/province name")
    parser.add_argument(
        "--definitions",
        default=str(DEFINITIONS),
        help="Path to definitions.txt",
    )
    args = parser.parse_args()

    definitions_path = Path(args.definitions)
    if not definitions_path.exists():
        sys.exit(f"ERROR: definitions.txt not found at {definitions_path}")

    geo = parse_definitions(definitions_path)
    locations = find_name(geo, args.name)

    if locations is None:
        sys.exit(f"ERROR: '{args.name}' not found in definitions.txt")

    for loc in locations:
        print(loc)


if __name__ == "__main__":
    main()
