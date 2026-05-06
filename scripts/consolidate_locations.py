"""
consolidate_locations.py — merge geography into one country in 10_countries.txt.

Accepts any combination of regions, areas, provinces, and individual locations.
Resolves each geography name via definitions.txt, then:
  - Removes matching locations from each source country's own_control_core and
    appends them to its our_cores_conquered_by_others (creating the block if absent).
  - Adds all locations (deduplicated against what the target already owns) to the
    target country's own_control_core (creating the block if absent).

Usage:
    python consolidate_locations.py TJP \\
        --regions indochina_region \\
        --areas south_borneo_area north_borneo_area \\
        --provinces pegu_province \\
        --locations pagan mandalay
"""

import argparse
import os
import re
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    load_dotenv(Path(__file__).parent.parent / ".env.local", override=True)
except ImportError:
    pass

_DEFAULT_MOD_PATH = Path(__file__).parent.parent
_MOD_PATH = Path(os.environ.get("EU5_MOD_PATH", _DEFAULT_MOD_PATH))
DEFAULT_FILE = _MOD_PATH / r"main_menu\setup\start\10_countries.txt"

sys.path.insert(0, str(Path(__file__).parent))
from get_locations import parse_definitions, find_name, DEFINITIONS


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consolidate geography into a single country's own_control_core."
    )
    parser.add_argument("tag", help="Target country tag (e.g. TJP)")
    parser.add_argument("--regions",   nargs="*", default=[], metavar="NAME", help="Region names")
    parser.add_argument("--areas",     nargs="*", default=[], metavar="NAME", help="Area names")
    parser.add_argument("--provinces", nargs="*", default=[], metavar="NAME", help="Province names")
    parser.add_argument("--locations", nargs="*", default=[], metavar="NAME", help="Individual location names")
    parser.add_argument("--file", default=str(DEFAULT_FILE), help="Path to 10_countries.txt")
    parser.add_argument("--definitions", default=str(DEFINITIONS), help="Path to definitions.txt")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Block manipulation helpers
# ---------------------------------------------------------------------------

def find_block_extent(text: str, block_start: int) -> tuple[int, int]:
    depth = 0
    i = block_start
    while i < len(text):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return block_start, i
        i += 1
    raise ValueError(f"Unmatched brace starting at {block_start}")


def find_country_block(text: str, tag: str) -> tuple[int, int] | None:
    pattern = re.compile(r'^\t' + re.escape(tag) + r'\s*=\s*\{', re.MULTILINE)
    m = pattern.search(text)
    if not m:
        return None
    open_brace = text.index('{', m.start())
    return find_block_extent(text, open_brace)


def find_named_block(text: str, search_start: int, search_end: int, name: str) -> tuple[int, int] | None:
    pattern = re.compile(r'\b' + re.escape(name) + r'\s*=\s*\{')
    m = pattern.search(text, search_start, search_end)
    if not m:
        return None
    open_brace = text.index('{', m.start())
    return find_block_extent(text, open_brace)


def get_block_locations(text: str, open_brace: int, close_brace: int) -> list[str]:
    """Extract leaf tokens from a block, ignoring nested sub-blocks."""
    inner = text[open_brace + 1:close_brace]
    depth = 0
    cleaned = []
    for ch in inner:
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
        elif depth == 0:
            cleaned.append(ch)
    return re.findall(r'\w+', ''.join(cleaned))


def remove_locations_from_block(text: str, open_brace: int, close_brace: int, to_remove: set[str]) -> str:
    inner = text[open_brace + 1:close_brace]
    new_inner = re.sub(r'\b(' + '|'.join(re.escape(l) for l in to_remove) + r')\b', '', inner)
    return text[:open_brace + 1] + new_inner + text[close_brace:]


def append_to_block(text: str, close_brace: int, locations: list[str]) -> str:
    loc_str = '\t\t\t' + ' '.join(locations) + '\n\t\t'
    return text[:close_brace] + loc_str + text[close_brace:]


def insert_block_before_close(text: str, country_close: int, block_name: str, locations: list[str]) -> str:
    loc_str = '\t\t' + ' '.join(locations)
    new_block = f'\n\t\t{block_name} = {{\n{loc_str}\n\t\t}}\n\t'
    return text[:country_close] + new_block + text[country_close:]


# ---------------------------------------------------------------------------
# Geography resolution
# ---------------------------------------------------------------------------

def resolve_locations(geo: dict, names: list[str], kind: str) -> set[str]:
    result: set[str] = set()
    for name in names:
        locs = find_name(geo, name)
        if locs is None:
            print(f"  WARNING: {kind} '{name}' not found in definitions.txt — skipped")
        else:
            result.update(locs)
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    target_tag = args.tag.upper()

    definitions_path = Path(args.definitions)
    if not definitions_path.exists():
        sys.exit(f"ERROR: definitions.txt not found at {definitions_path}")

    countries_file = Path(args.file)
    if not countries_file.exists():
        sys.exit(f"ERROR: file not found: {countries_file}")

    # Resolve all geography inputs into a single location set
    geo = parse_definitions(definitions_path)
    locations_to_add: set[str] = set()
    locations_to_add.update(resolve_locations(geo, args.regions,   "region"))
    locations_to_add.update(resolve_locations(geo, args.areas,     "area"))
    locations_to_add.update(resolve_locations(geo, args.provinces, "province"))
    locations_to_add.update(args.locations)

    if not locations_to_add:
        sys.exit("ERROR: no locations resolved from the provided inputs.")

    print(f"Resolved {len(locations_to_add)} unique location(s) total.")

    text = countries_file.read_text(encoding="utf-8")

    country_pattern = re.compile(r'^\t([A-Z]{3})\s*=\s*\{', re.MULTILINE)
    all_tags = [m.group(1) for m in country_pattern.finditer(text)]

    if target_tag not in all_tags:
        sys.exit(f"ERROR: tag '{target_tag}' not found in {countries_file.name}")

    # Deduplicate against what the target already owns
    c_open, c_close = find_country_block(text, target_tag)
    occ_block = find_named_block(text, c_open, c_close, 'own_control_core')
    already_owned = set(get_block_locations(text, *occ_block)) if occ_block else set()
    new_locations = locations_to_add - already_owned

    if not new_locations:
        print(f"[{target_tag}] already owns all resolved locations — nothing to do.")
        return

    skipped = locations_to_add & already_owned
    if skipped:
        print(f"[{target_tag}] skipping {len(skipped)} already-owned location(s).")

    blocks = ['own_control_core','own_control_integrated','own_control_conquered','own_control_colony','own_core','own_conquered','own_integrated','own_colony','control_core','control','our_cores_conquered_by_others']

    # --- Pass 1: strip new_locations from source countries ---
    source_edits: list[tuple[str, list[str]]] = []
    for tag in all_tags:
        if tag == target_tag:
            continue
        country_block = find_country_block(text, tag)
        if not country_block:
            continue

        for b in blocks:
            block = find_named_block(text, country_block[0], country_block[1], b)
            if block:
                in_block = set(get_block_locations(text, *block)) if block else set()
                to_move = sorted(new_locations & (in_block))
                if to_move:
                    source_edits.append((tag, to_move))

    # Sort in reverse file order so edits don't shift subsequent offsets
    source_edits.sort(key=lambda e: find_country_block(text, e[0])[0], reverse=True)

    for tag, to_move in source_edits:
        c_open, c_close = find_country_block(text, tag)

        for b in blocks:
            block = find_named_block(text, c_open, c_close, b)
            if block:
                text = remove_locations_from_block(text, block[0], block[1], set(to_move))

        c_open, c_close = find_country_block(text, tag)
        conquered = find_named_block(text, c_open, c_close, 'our_cores_conquered_by_others')
        if conquered:
            text = append_to_block(text, conquered[1], to_move)
        else:
            c_open, c_close = find_country_block(text, tag)
            text = insert_block_before_close(text, c_close, 'our_cores_conquered_by_others', to_move)

        print(f"  [{tag}] moved {len(to_move)} location(s) to our_cores_conquered_by_others: {' '.join(to_move)}")

    # --- Pass 2: add new locations to target ---
    c_open, c_close = find_country_block(text, target_tag)
    occ_block = find_named_block(text, c_open, c_close, 'own_control_core')
    sorted_new = sorted(new_locations)

    if occ_block:
        text = append_to_block(text, occ_block[1], sorted_new)
    else:
        c_open, c_close = find_country_block(text, target_tag)
        text = insert_block_before_close(text, c_close, 'own_control_core', sorted_new)

    print(f"  [{target_tag}] added {len(sorted_new)} new location(s) to own_control_core")

    countries_file.write_text(text, encoding="utf-8")
    print(f"\nDone. Written to {countries_file}")


if __name__ == "__main__":
    main()
