"""
migrate_mod_countries.py

Migrates mod_countries.txt into 10_countries.txt:
  1. Appends every country block from mod_countries.txt into the inner
     'countries = {' block of 10_countries.txt (just before the two
     closing braces at the end of the file).
  2. Removes every province that appears in any mod country's
     own_control_core from all existing countries in 10_countries.txt.
"""

import re
from pathlib import Path
from collections import defaultdict

MOD_FILE  = Path(__file__).parent.parent / "main_menu/setup/start/mod_countries.txt"
MAIN_FILE = Path(__file__).parent.parent / "main_menu/setup/start/10_countries.txt"

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


# ── parser (same logic as promote_cores.py) ───────────────────────────────────

def parse_countries(lines):
    countries = {}
    i = 0
    n = len(lines)
    while i < n:
        m = re.match(r'^\t([A-Z0-9_]{2,4})\s*=\s*\{', lines[i])
        if m:
            tag = m.group(1)
            country_start = i
            depth = 1
            i += 1
            blocks = []
            while i < n and depth > 0:
                line = lines[i]
                stripped = line.split('#')[0]
                opens = stripped.count('{')
                closes = stripped.count('}')
                if depth == 1:
                    bm = re.match(r'^\t\t(\w+)\s*=\s*\{', line)
                    if bm and bm.group(1) in LOCATION_KEYS:
                        block_key = bm.group(1)
                        block_open = i
                        inner_depth = opens - closes
                        j = i + 1
                        while j < n and inner_depth > 0:
                            s2 = lines[j].split('#')[0]
                            inner_depth += s2.count('{') - s2.count('}')
                            j += 1
                        block_close = j - 1
                        blocks.append({'key': block_key, 'open': block_open, 'close': block_close})
                depth += opens - closes
                i += 1
            countries[tag] = {'start': country_start, 'end': i - 1, 'blocks': blocks}
        else:
            i += 1
    return countries


def extract_provinces(lines, block):
    provinces = set()
    for li in range(block['open'], block['close'] + 1):
        text = lines[li].split('#')[0]
        text = re.sub(r'\b\w+\s*=\s*\{', '', text)
        text = text.replace('}', '')
        for token in text.split():
            if token:
                provinces.add(token)
    return provinces


# ── parse mod_countries.txt ───────────────────────────────────────────────────

def parse_mod_countries(text):
    """
    Returns a list of (tag, full_block_text) in source order.
    full_block_text includes any preceding comment line(s).
    """
    lines = text.splitlines(keepends=True)
    results = []
    i = 0
    n = len(lines)
    while i < n:
        # Collect any comment lines immediately before a tag block
        comment_start = i
        while i < n and lines[i].strip().startswith('#'):
            i += 1
        m = re.match(r'^([A-Z0-9_]{2,4})\s*=\s*\{', lines[i]) if i < n else None
        if m:
            tag = m.group(1)
            block_start = comment_start
            depth = 1
            i += 1
            while i < n and depth > 0:
                stripped = lines[i].split('#')[0]
                depth += stripped.count('{') - stripped.count('}')
                i += 1
            block_end = i  # exclusive
            block_text = ''.join(lines[block_start:block_end])
            results.append((tag, block_text))
        else:
            i += 1
    return results


def extract_mod_own_control_cores(mod_entries):
    """Return the set of all provinces in own_control_core blocks across mod countries."""
    provinces = set()
    for tag, block_text in mod_entries:
        for m in re.finditer(r'\bown_control_core\s*=\s*\{([^}]*)\}', block_text, re.DOTALL):
            for token in m.group(1).split():
                if token:
                    provinces.add(token)
    return provinces


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    mod_text  = MOD_FILE.read_text(encoding='utf-8')
    main_text = MAIN_FILE.read_text(encoding='utf-8')
    main_lines = main_text.splitlines(keepends=True)

    print(f"Loaded {len(main_lines)} lines from {MAIN_FILE.name}")

    mod_entries = parse_mod_countries(mod_text)
    print(f"Parsed {len(mod_entries)} mod countries: {[t for t, _ in mod_entries]}")

    mod_provinces = extract_mod_own_control_cores(mod_entries)
    print(f"Mod own_control_core provinces ({len(mod_provinces)}): {sorted(mod_provinces)}")

    # ── Step 1: remove mod provinces from existing countries ─────────────────

    existing = parse_countries(main_lines)
    print(f"\nParsed {len(existing)} existing country blocks in 10_countries.txt")

    # Find which existing blocks contain mod provinces
    block_removals = defaultdict(set)  # (tag, block_open) -> provinces to remove
    removal_log = defaultdict(lambda: defaultdict(set))  # tag -> block_key -> provinces

    for tag, info in existing.items():
        for block in info['blocks']:
            provs = extract_provinces(main_lines, block)
            overlap = provs & mod_provinces
            if overlap:
                block_removals[(tag, block['open'])].update(overlap)
                removal_log[tag][block['key']].update(overlap)

    # Build block lookup
    block_by_open = {}
    for tag, info in existing.items():
        for block in info['blocks']:
            block_by_open[block['open']] = (tag, block)

    edits = {}  # line_index -> new_content

    for (tag, block_open), to_remove in block_removals.items():
        _, block = block_by_open[block_open]
        for li in range(block['open'] + 1, block['close']):
            original = main_lines[li]
            comment_match = re.search(r'(\s*#.*)$', original)
            comment = comment_match.group(1) if comment_match else ''
            code_part = original[:comment_match.start()] if comment_match else original
            tokens = code_part.split()
            remaining = [t for t in tokens if t not in to_remove]
            if remaining:
                ws = re.match(r'^(\s*)', original).group(1)
                new_line = ws + ' '.join(remaining) + comment + '\n'
            else:
                new_line = ''
            if new_line != original:
                edits[li] = new_line

    # ── Step 2: find insertion point (second-to-last '}' line) ───────────────
    # The file ends with:  \t}\n}\n  (inner countries close, outer countries close)
    # We insert before the last two closing braces.

    insert_before = None
    for li in range(len(main_lines) - 1, -1, -1):
        stripped = main_lines[li].strip()
        if stripped == '}':
            # keep going — we want the line BEFORE the outer '}'
            # The structure is: last line = '}', second-to-last = '\t}'
            # Insert before the '\t}' line (inner countries block close)
            insert_before = li
            break

    # Walk back one more to find the inner '}'
    for li in range(insert_before - 1, -1, -1):
        stripped = main_lines[li].strip()
        if stripped == '}':
            insert_before = li
            break

    print(f"\nInsertion point: before line {insert_before + 1} (0-indexed {insert_before})")

    # ── Step 3: build new lines list ─────────────────────────────────────────

    new_lines = []
    for li, line in enumerate(main_lines):
        if li == insert_before:
            # Insert mod country blocks (indented with one tab to sit inside inner countries = {)
            new_lines.append('\n')
            for tag, block_text in mod_entries:
                # Indent each line of the block by one tab
                indented = ''.join(
                    '\t' + l if l.strip() else l
                    for l in block_text.splitlines(keepends=True)
                )
                new_lines.append(indented)
                if not indented.endswith('\n'):
                    new_lines.append('\n')
            new_lines.append('\n')

        if li in edits:
            replacement = edits[li]
            if replacement != '':
                new_lines.append(replacement)
            # else: line deleted
        else:
            new_lines.append(line)

    # ── Step 4: write output ──────────────────────────────────────────────────

    output = ''.join(new_lines)
    MAIN_FILE.write_text(output, encoding='utf-8')
    print(f"Wrote {len(new_lines)} lines (was {len(main_lines)})")

    # ── Step 5: report ────────────────────────────────────────────────────────

    print("\n=== Inserted mod countries ===")
    for tag, _ in mod_entries:
        print(f"  {tag}")

    print("\n=== Removed mod provinces from existing countries ===")
    removed_total = 0
    for tag in sorted(removal_log):
        for block_key, provs in sorted(removal_log[tag].items()):
            print(f"  {tag} [{block_key}]: {sorted(provs)}")
            removed_total += len(provs)
    print(f"\nTotal province removals: {removed_total}")
    print("Done.")


if __name__ == '__main__':
    main()
