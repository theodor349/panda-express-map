"""
promote_cores.py

For every country in 10_countries.txt that has ONLY our_cores_conquered_by_others
(no other location block), this script:
  1. Renames that block to own_control_core
  2. Removes each of those provinces from any other country's location blocks

Location block types recognised (from the file header):
  own_control_core, own_control_integrated, own_control_conquered,
  own_control_colony, own_core, own_conquered, own_integrated,
  own_colony, control_core, control, our_cores_conquered_by_others
"""

import os
import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    load_dotenv(Path(__file__).parent.parent / ".env.local", override=True)
except ImportError:
    pass

ROOT = Path(os.environ.get("EU5_MOD_PATH", Path(__file__).parent.parent))
FILE = ROOT / "main_menu/setup/start/10_countries.txt"

LOCATION_KEYS = {
    "own_control_core",
    "own_control_integrated",
    "own_control_conquered",
    "own_control_colony",
    "own_core",
    "own_conquered",
    "own_integrated",
    "own_colony",
    "control_core",
    "control",
    "our_cores_conquered_by_others",
}

# ── parser ────────────────────────────────────────────────────────────────────

def parse_countries(lines):
    """
    Returns:
      countries: dict[tag -> dict with keys:
                   'start'  – line index of 'TAG = {'
                   'end'    – line index of closing '}'
                   'blocks' – list of dicts:
                                'key'   – block keyword
                                'open'  – line index of 'key = {'
                                'close' – line index of closing '}'
                 ]
    """
    countries = {}
    i = 0
    n = len(lines)

    # We expect:  countries = {
    #               countries = {
    #                 TAG = { ... }
    while i < n:
        # Match a country tag line: "  TAG = {"
        m = re.match(r'^\t([A-Z0-9_]{2,4})\s*=\s*\{', lines[i])
        if m:
            tag = m.group(1)
            country_start = i
            depth = 1
            i += 1
            blocks = []

            while i < n and depth > 0:
                line = lines[i]

                # Count brace depth changes (ignoring commented lines)
                stripped = line.split('#')[0]
                opens = stripped.count('{')
                closes = stripped.count('}')

                # Check for a location block opening at depth==1
                if depth == 1:
                    bm = re.match(r'^\t\t(\w+)\s*=\s*\{', line)
                    if bm and bm.group(1) in LOCATION_KEYS:
                        block_key = bm.group(1)
                        block_open = i
                        # Find closing brace of this block
                        inner_depth = opens - closes  # net from this line
                        j = i + 1
                        while j < n and inner_depth > 0:
                            s2 = lines[j].split('#')[0]
                            inner_depth += s2.count('{') - s2.count('}')
                            j += 1
                        block_close = j - 1
                        blocks.append({
                            'key': block_key,
                            'open': block_open,
                            'close': block_close,
                        })

                depth += opens - closes
                i += 1

            countries[tag] = {
                'start': country_start,
                'end': i - 1,
                'blocks': blocks,
            }
        else:
            i += 1

    return countries


def extract_provinces(lines, block):
    """Return the set of province tokens from a location block."""
    provinces = set()
    for li in range(block['open'], block['close'] + 1):
        # Strip comments
        text = lines[li].split('#')[0]
        # Remove the keyword = { and } delimiters
        text = re.sub(r'\b\w+\s*=\s*\{', '', text)
        text = text.replace('}', '')
        for token in text.split():
            if token:
                provinces.add(token)
    return provinces


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    text = FILE.read_text(encoding='utf-8')
    lines = text.splitlines(keepends=True)

    print(f"Loaded {len(lines)} lines from {FILE.name}")

    countries = parse_countries(lines)
    print(f"Parsed {len(countries)} country blocks")

    # Step 1: find candidates — countries with ONLY our_cores_conquered_by_others
    candidates = {}
    for tag, info in countries.items():
        keys = {b['key'] for b in info['blocks']}
        if keys == {'our_cores_conquered_by_others'}:
            candidates[tag] = info

    print(f"\nCandidates (only our_cores_conquered_by_others): {sorted(candidates)}")
    if not candidates:
        print("Nothing to do.")
        return

    # Step 2: collect all provinces owned by each candidate
    candidate_provinces = {}  # tag -> set of province tokens
    for tag, info in candidates.items():
        for block in info['blocks']:
            candidate_provinces[tag] = extract_provinces(lines, block)

    all_candidate_provinces = set()
    for provs in candidate_provinces.values():
        all_candidate_provinces |= provs

    # Step 3: for every non-candidate country, record which of those provinces
    #         appear in its location blocks, and where
    # removal_map: province -> list of (tag, block)
    removal_map = defaultdict(list)
    for tag, info in countries.items():
        if tag in candidates:
            continue
        for block in info['blocks']:
            provs = extract_provinces(lines, block)
            for p in provs & all_candidate_provinces:
                removal_map[p].append((tag, block))

    # Step 4: apply edits (work on lines list, back to front to preserve indices)
    # Collect all line-level edits first, then apply from last to first line.

    # edits: list of (line_index, old_content, new_content)
    edits = []

    # 4a: rename our_cores_conquered_by_others -> own_control_core in candidates
    for tag, info in candidates.items():
        for block in info['blocks']:
            if block['key'] == 'our_cores_conquered_by_others':
                li = block['open']
                old = lines[li]
                new = old.replace('our_cores_conquered_by_others', 'own_control_core', 1)
                edits.append((li, old, new))

    # 4b: remove candidate provinces from other countries' blocks
    # For each block that needs province removal, rewrite the province lines
    # We group by (tag, block open line) to handle each block once.
    block_removals = defaultdict(set)  # (tag, block_open) -> set of provinces to remove
    for prov, entries in removal_map.items():
        for tag, block in entries:
            block_removals[(tag, block['open'])].add(prov)

    # Build a lookup: block_open -> block info
    block_by_open = {}
    for tag, info in countries.items():
        for block in info['blocks']:
            block_by_open[block['open']] = (tag, block)

    for (tag, block_open), to_remove in block_removals.items():
        _, block = block_by_open[block_open]
        # Rewrite each line inside the block, stripping the removed tokens
        for li in range(block['open'] + 1, block['close']):
            original = lines[li]
            # Split off comment
            comment_match = re.search(r'(\s*#.*)$', original)
            comment = comment_match.group(1) if comment_match else ''
            code_part = original[:comment_match.start()] if comment_match else original

            tokens = code_part.split()
            remaining = [t for t in tokens if t not in to_remove]

            if remaining:
                # Preserve leading whitespace
                ws = re.match(r'^(\s*)', original).group(1)
                new_line = ws + ' '.join(remaining) + comment + '\n'
            else:
                # Line becomes empty — drop it (replace with empty string to delete)
                new_line = ''

            if new_line != original:
                edits.append((li, original, new_line))

    # Step 5: apply edits back-to-front
    edits_by_line = {}
    for li, old, new in edits:
        edits_by_line[li] = new  # last write wins (shouldn't conflict)

    new_lines = []
    for li, line in enumerate(lines):
        if li in edits_by_line:
            replacement = edits_by_line[li]
            if replacement != '':
                new_lines.append(replacement)
            # else: line deleted
        else:
            new_lines.append(line)

    # Step 6: write output
    output = ''.join(new_lines)
    FILE.write_text(output, encoding='utf-8')
    print(f"\nWrote {len(new_lines)} lines (removed {len(lines) - len(new_lines)} empty lines)")

    # Step 7: report
    print("\n=== Summary ===")
    for tag in sorted(candidates):
        provs = candidate_provinces[tag]
        donors = defaultdict(set)
        for p in provs:
            for donor_tag, _ in removal_map.get(p, []):
                donors[donor_tag].add(p)
        print(f"\n{tag}: promoted {len(provs)} provinces to own_control_core")
        if donors:
            for donor, dp in sorted(donors.items()):
                print(f"  removed from {donor}: {sorted(dp)}")
        else:
            unowned = provs - set(removal_map.keys())
            if unowned:
                print(f"  (provinces were not in any other country: {sorted(unowned)})")

    print("\nDone.")


if __name__ == '__main__':
    main()
