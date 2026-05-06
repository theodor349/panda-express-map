"""
consolidate_locations.py — merge a set of locations into one country in 10_countries.txt.

For each source country that owns any of the given locations:
  - Removes those locations from its own_control_core block.
  - Appends them to its our_cores_conquered_by_others block (creating it if absent).

For the target country:
  - Appends all locations to its own_control_core block (creating it if absent).

Usage:
    python consolidate_locations.py <TAG> <loc1> [loc2 ...] [--file PATH]
    python get_locations.py myanmar_region | xargs python consolidate_locations.py BUR
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Consolidate locations into a single country.")
    parser.add_argument("tag", help="Target country tag (e.g. BUR)")
    parser.add_argument("locations", nargs="+", help="Location names to consolidate")
    parser.add_argument("--file", default=str(DEFAULT_FILE), help="Path to 10_countries.txt")
    return parser.parse_args()


def find_block_extent(text: str, block_start: int) -> tuple[int, int]:
    """
    Given the index of the opening '{' of a block, return (open_brace, close_brace)
    indices (inclusive) for that block.
    """
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
    """Return (open_brace, close_brace) for the country tag's top-level block."""
    pattern = re.compile(r'^\t' + re.escape(tag) + r'\s*=\s*\{', re.MULTILINE)
    m = pattern.search(text)
    if not m:
        return None
    open_brace = text.index('{', m.start())
    return find_block_extent(text, open_brace)


def find_named_block(text: str, search_start: int, search_end: int, name: str) -> tuple[int, int] | None:
    """
    Within text[search_start:search_end], find a block named `name = { ... }`.
    Returns (open_brace, close_brace) absolute indices, or None.
    """
    pattern = re.compile(r'\b' + re.escape(name) + r'\s*=\s*\{')
    m = pattern.search(text, search_start, search_end)
    if not m:
        return None
    open_brace = text.index('{', m.start())
    return find_block_extent(text, open_brace)


def get_block_locations(text: str, open_brace: int, close_brace: int) -> list[str]:
    """Extract all word tokens from inside the block (excluding sub-block contents)."""
    inner = text[open_brace + 1:close_brace]
    # Strip nested blocks entirely before extracting tokens
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
    """Remove the given location tokens from the block's inner text."""
    inner = text[open_brace + 1:close_brace]
    new_inner = re.sub(r'\b(' + '|'.join(re.escape(l) for l in to_remove) + r')\b', '', inner)
    return text[:open_brace + 1] + new_inner + text[close_brace:]


def append_to_block(text: str, close_brace: int, locations: list[str]) -> str:
    """Insert locations before the closing brace of a block."""
    loc_str = '\t\t\t' + ' '.join(locations) + '\n\t\t'
    return text[:close_brace] + loc_str + text[close_brace:]


def insert_block_before_close(text: str, country_close: int, block_name: str, locations: list[str]) -> str:
    """Insert a new named block before the country's closing brace."""
    loc_str = '\t\t' + ' '.join(locations)
    new_block = f'\n\t\t{block_name} = {{\n{loc_str}\n\t\t}}\n\t'
    return text[:country_close] + new_block + text[country_close:]


def main() -> None:
    args = parse_args()
    target_tag = args.tag.upper()
    locations_to_move = set(args.locations)

    countries_file = Path(args.file)
    if not countries_file.exists():
        sys.exit(f"ERROR: file not found: {countries_file}")

    text = countries_file.read_text(encoding="utf-8")

    # Find all country tags that appear in the file
    country_pattern = re.compile(r'^\t([A-Z]{3})\s*=\s*\{', re.MULTILINE)
    all_tags = [m.group(1) for m in country_pattern.finditer(text)]

    if target_tag not in all_tags:
        sys.exit(f"ERROR: tag '{target_tag}' not found in {countries_file.name}")

    # --- Pass 1: remove locations from source countries and move to our_cores_conquered_by_others ---
    # We must process right-to-left to keep offsets valid after each edit.
    # Collect edits as (tag, locations_to_move_from_that_tag), then apply in reverse order.

    source_edits: list[tuple[str, list[str]]] = []

    for tag in all_tags:
        if tag == target_tag:
            continue
        block = find_country_block(text, tag)
        if not block:
            continue
        c_open, c_close = block

        occ_block = find_named_block(text, c_open, c_close, 'own_control_core')
        if not occ_block:
            continue

        in_occ = set(get_block_locations(text, *occ_block))
        to_move = sorted(locations_to_move & in_occ)
        if not to_move:
            continue

        source_edits.append((tag, to_move))

    # Apply edits in reverse file order so indices stay valid
    source_edits_with_pos: list[tuple[int, str, list[str]]] = []
    for tag, to_move in source_edits:
        block = find_country_block(text, tag)
        assert block
        source_edits_with_pos.append((block[0], tag, to_move))

    source_edits_with_pos.sort(key=lambda x: x[0], reverse=True)

    for _, tag, to_move in source_edits_with_pos:
        c_open, c_close = find_country_block(text, tag)

        # Remove from own_control_core
        occ_block = find_named_block(text, c_open, c_close, 'own_control_core')
        assert occ_block
        text = remove_locations_from_block(text, occ_block[0], occ_block[1], set(to_move))

        # Recalculate bounds after edit
        c_open, c_close = find_country_block(text, tag)

        # Add to our_cores_conquered_by_others
        conquered_block = find_named_block(text, c_open, c_close, 'our_cores_conquered_by_others')
        if conquered_block:
            text = append_to_block(text, conquered_block[1], to_move)
        else:
            c_open, c_close = find_country_block(text, tag)
            text = insert_block_before_close(text, c_close, 'our_cores_conquered_by_others', to_move)

        print(f"  [{tag}] moved {len(to_move)} location(s) to our_cores_conquered_by_others: {' '.join(to_move)}")

    # --- Pass 2: add all locations to the target country's own_control_core ---
    c_open, c_close = find_country_block(text, target_tag)
    occ_block = find_named_block(text, c_open, c_close, 'own_control_core')
    all_locations = sorted(locations_to_move)

    if occ_block:
        text = append_to_block(text, occ_block[1], all_locations)
    else:
        c_open, c_close = find_country_block(text, target_tag)
        text = insert_block_before_close(text, c_close, 'own_control_core', all_locations)

    print(f"  [{target_tag}] added {len(all_locations)} location(s) to own_control_core")

    countries_file.write_text(text, encoding="utf-8")
    print(f"\nDone. Written to {countries_file}")


if __name__ == "__main__":
    main()
