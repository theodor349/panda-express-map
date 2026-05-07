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
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
    load_dotenv(Path(__file__).parent.parent.parent / ".env.local", override=True)
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
    parser.add_argument("--tags",      nargs="*", default=[], metavar="TAG",  help="Take all locations from these country tags")
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


def index_country_blocks(text: str) -> dict[str, tuple[int, int]]:
    """Build a tag -> (open, close) map in one pass."""
    pattern = re.compile(r'^\t([A-Z]{3})\s*=\s*\{', re.MULTILINE)
    index: dict[str, tuple[int, int]] = {}
    for m in pattern.finditer(text):
        tag = m.group(1)
        open_brace = text.index('{', m.start())
        index[tag] = find_block_extent(text, open_brace)
    return index


def find_named_block(text: str, search_start: int, search_end: int, name: str) -> tuple[int, int] | None:
    pattern = re.compile(r'\b' + re.escape(name) + r'\s*=\s*\{')
    m = pattern.search(text, search_start, search_end)
    if not m:
        return None
    open_brace = text.index('{', m.start())
    return find_block_extent(text, open_brace)


def get_block_locations(text: str, open_brace: int, close_brace: int) -> list[str]:
    """Extract leaf tokens from a block, ignoring nested sub-blocks and # comments."""
    inner = text[open_brace + 1:close_brace]
    # Strip line comments before tokenising
    inner = re.sub(r'#[^\n]*', '', inner)
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


def _format_locations(locations: list[str], indent: str, chunk_size: int = 4) -> str:
    rows = [locations[i:i + chunk_size] for i in range(0, len(locations), chunk_size)]
    return '\n'.join(indent + ' '.join(row) for row in rows)


def append_to_block(text: str, close_brace: int, locations: list[str]) -> str:
    loc_str = '\n' + _format_locations(locations, '\t\t\t') + '\n\t\t'
    return text[:close_brace] + loc_str + text[close_brace:]


def insert_block_before_close(text: str, country_close: int, block_name: str, locations: list[str]) -> str:
    loc_str = _format_locations(locations, '\t\t\t')
    new_block = f'\n\t\t{block_name} = {{\n{loc_str}\n\t\t}}\n\t'
    return text[:country_close] + new_block + text[country_close:]


# ---------------------------------------------------------------------------
# Tag-based location resolution
# ---------------------------------------------------------------------------

SOURCE_BLOCKS = ['own_control_core','own_control_integrated','own_control_conquered','own_control_colony','own_core','own_conquered','own_integrated','own_colony','control_core','control']

def resolve_tag_locations(text: str, block_index: dict, tags: list[str], errors: list[str]) -> set[str]:
    result: set[str] = set()
    for tag in tags:
        tag = tag.upper()
        if tag not in block_index:
            errors.append(f"  tag '{tag}' not found in 10_countries.txt")
            continue
        c_open, c_close = block_index[tag]
        for b in SOURCE_BLOCKS:
            blk = find_named_block(text, c_open, c_close, b)
            if blk:
                result.update(get_block_locations(text, *blk))
    return result


# ---------------------------------------------------------------------------
# Geography resolution
# ---------------------------------------------------------------------------

def resolve_locations(geo: dict, names: list[str], kind: str, errors: list[str]) -> set[str]:
    result: set[str] = set()
    for name in names:
        locs = find_name(geo, name)
        if locs is None:
            errors.append(f"  {kind} '{name}' not found in definitions.txt")
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

    # Resolve geography inputs
    geo = parse_definitions(definitions_path)
    errors: list[str] = []
    locations_to_add: set[str] = set()
    locations_to_add.update(resolve_locations(geo, args.regions,   "region",   errors))
    locations_to_add.update(resolve_locations(geo, args.areas,     "area",     errors))
    locations_to_add.update(resolve_locations(geo, args.provinces, "province", errors))
    locations_to_add.update(resolve_locations(geo, args.locations, "location", errors))

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        sys.exit("ERROR: one or more names not found in definitions.txt")

    text = countries_file.read_text(encoding="utf-8")
    block_index = index_country_blocks(text)

    if target_tag not in block_index:
        sys.exit(f"ERROR: tag '{target_tag}' not found in {countries_file.name}")

    # Resolve --tags inputs (requires file to be loaded)
    if args.tags:
        tag_errors: list[str] = []
        locations_to_add.update(resolve_tag_locations(text, block_index, args.tags, tag_errors))
        if tag_errors:
            for e in tag_errors:
                print(e, file=sys.stderr)
            sys.exit("ERROR: one or more tags not found in 10_countries.txt")

    if not locations_to_add:
        print(f"[{target_tag}] no locations to add — skipping.")
        return

    print(f"Resolved {len(locations_to_add)} unique location(s) total.")

    # Deduplicate against what the target already owns
    c_open, c_close = block_index[target_tag]
    occ_block = find_named_block(text, c_open, c_close, 'own_control_core')
    already_owned = set(get_block_locations(text, *occ_block)) if occ_block else set()
    new_locations = locations_to_add - already_owned

    if not new_locations:
        print(f"[{target_tag}] already owns all resolved locations — nothing to do.")
        return

    skipped = locations_to_add & already_owned
    if skipped:
        print(f"[{target_tag}] skipping {len(skipped)} already-owned location(s).")

    blocks = SOURCE_BLOCKS

    # --- Pass 1: find which source tags need edits, sorted reverse file order ---
    source_edits: list[tuple[str, list[str]]] = []
    for tag, (cb_open, cb_close) in sorted(block_index.items(), key=lambda kv: kv[1][0], reverse=True):
        if tag == target_tag:
            continue
        to_move: set[str] = set()
        for b in blocks:
            blk = find_named_block(text, cb_open, cb_close, b)
            if blk:
                to_move.update(new_locations & set(get_block_locations(text, *blk)))
        if to_move:
            source_edits.append((tag, sorted(to_move)))

    for tag, to_move in source_edits:
        # Work on a substring so we never need to re-index the full file.
        # Processing in reverse file order keeps unvisited block offsets valid.
        c_open, c_close = block_index[tag]
        blk_text = text[c_open:c_close + 1]

        for b in blocks:
            sub = find_named_block(blk_text, 0, len(blk_text), b)
            if sub:
                blk_text = remove_locations_from_block(blk_text, sub[0], sub[1], set(to_move))

        conquered = find_named_block(blk_text, 0, len(blk_text), 'our_cores_conquered_by_others')
        if conquered:
            blk_text = append_to_block(blk_text, conquered[1], to_move)
        else:
            blk_text = insert_block_before_close(blk_text, len(blk_text) - 1, 'our_cores_conquered_by_others', to_move)

        text = text[:c_open] + blk_text + text[c_close + 1:]
        print(f"  [{tag}] moved {len(to_move)} location(s) to our_cores_conquered_by_others: {' '.join(to_move)}")

    # --- Pass 2: add new locations to target ---
    block_index = index_country_blocks(text)
    c_open, c_close = block_index[target_tag]
    occ_block = find_named_block(text, c_open, c_close, 'own_control_core')
    sorted_new = sorted(new_locations)

    if occ_block:
        text = append_to_block(text, occ_block[1], sorted_new)
    else:
        text = insert_block_before_close(text, c_close, 'own_control_core', sorted_new)

    print(f"  [{target_tag}] added {len(sorted_new)} new location(s) to own_control_core")

    countries_file.write_text(text, encoding="utf-8")
    print(f"\nDone. Written to {countries_file}")


if __name__ == "__main__":
    main()
