"""
create_country.py

Creates a new country in the mod by:
  1. Adding an own_control_core block in 10_countries.txt, removing the
     assigned locations from any other country that currently owns them.
  2. Appending a color/culture/religion entry to in_game/setup/countries/panda_express_map.txt.
  3. Appending name/adj entries to the localization file (UTF-8 BOM preserved).

Usage:
  python create_country.py --name "Toledo" --name-adj "Toledan" \\
      --region iberian --locations toledo talavera escalona \\
      [--tag IB3] [--provinces salamanca_province] \\
      [--color 180 120 30] [--culture castilian] [--religion catholic] \\
      [--rank rank_duchy]

  --tag is optional; if omitted a new tag is auto-generated.
  --provinces resolves province names to their constituent locations.
  Regions: iberian (castilian culture, Mediterranean includes)
           french  (french culture, western Europe includes)
"""

import argparse
import os
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
    load_dotenv(Path(__file__).parent.parent.parent / ".env.local", override=True)
except ImportError:
    pass

ROOT = Path(os.environ.get("EU5_MOD_PATH", Path(__file__).parent.parent.parent))
BASE_GAME = Path(os.environ.get("EU5_GAME_PATH", r"C:\Program Files (x86)\Steam\steamapps\common\Europa Universalis V\game"))

COUNTRIES_FILE    = ROOT / "main_menu/setup/start/10_countries.txt"
DEFINITIONS_FILE  = ROOT / "in_game/setup/countries/panda_express_map.txt"
LOCALIZATION_FILE = ROOT / "main_menu/localization/english/country_names_l_english.yml"
PROVINCE_MAP_FILE    = BASE_GAME / "in_game/map_data/definitions.txt"
LOCATION_TEMPLATES   = BASE_GAME / "in_game/map_data/location_templates.txt"

TAG_CHARS = '0123456789abcdefghijklmnopqrstuvwxyz'
REGION_PREFIXES = {'iberian': 'IB', 'french': 'FR'}

REGION_DEFAULTS = {
    'iberian': {
        'includes': ['expl_mediterranean', 'expl_silk_road_west', 'expl_silk_road_center', 
                     'expl_silk_road_east', 'expl_indian_trade_route', 'catholic_monarchy_not_present'],
        'culture':  'castilian',
    },
    'french': {
        'includes': ['expl_western_europe', 'catholic_monarchy_no_coast'],
        'culture':  'french',
    },
}

LOCATION_KEYS = {
    "own_control_core", "own_control_integrated", "own_control_conquered",
    "own_control_colony", "own_core", "own_conquered", "own_integrated",
    "own_colony", "control_core", "control", "our_cores_conquered_by_others",
}


# ── tag generation ───────────────────────────────────────────────────────────

def used_tags():
    """Returns set of all tags already in use across both mod files."""
    tags = set()
    for path in (COUNTRIES_FILE, DEFINITIONS_FILE):
        if path.exists():
            for m in re.finditer(r'^[ \t]*([A-Z0-9_]{2,6})\s*=\s*\{', path.read_text(encoding='utf-8'), re.MULTILINE):
                tags.add(m.group(1))
    return tags


def generate_tag(region: str) -> str:
    taken = used_tags()
    prefix = REGION_PREFIXES.get(region, 'XX')
    for c in TAG_CHARS:
        candidate = (prefix + c).upper()
        if candidate not in taken:
            return candidate
    # fallback: AAA, AAB, ...
    import itertools, string
    for combo in itertools.product(string.ascii_uppercase, repeat=3):
        candidate = ''.join(combo)
        if candidate not in taken:
            return candidate
    raise RuntimeError("No available tags found")


# ── province → locations ──────────────────────────────────────────────────────

def load_province_map() -> dict[str, list[str]]:
    """Returns {province_name: [locations]} from base game definitions.txt."""
    text = PROVINCE_MAP_FILE.read_text(encoding='utf-8')
    result = {}
    for m in re.finditer(r'(\w+)\s*=\s*\{([^{}]*)\}', text):
        content = m.group(2)
        if '=' not in content:
            result[m.group(1)] = content.split()
    return result


def resolve_provinces(province_names: list[str]) -> list[str]:
    pmap = load_province_map()
    locations = []
    for prov in province_names:
        if prov not in pmap:
            print(f"WARNING: province '{prov}' not found in definitions.txt", file=sys.stderr)
        else:
            locations.extend(pmap[prov])
    return locations


# ── location_templates.txt ───────────────────────────────────────────────────

def load_location_templates() -> dict[str, dict]:
    """Returns {location: {culture, religion, ...}} parsed from location_templates.txt."""
    text = LOCATION_TEMPLATES.read_text(encoding='utf-8')
    result = {}
    for m in re.finditer(r'(\w+)\s*=\s*\{([^{}]*)\}', text):
        name = m.group(1)
        attrs = {}
        for kv in re.finditer(r'(\w+)\s*=\s*(\S+)', m.group(2)):
            attrs[kv.group(1)] = kv.group(2)
        result[name] = attrs
    return result


def validate_locations(locations: set[str], templates: dict[str, dict]):
    """Exits with error if any location is not in location_templates.txt."""
    unknown = [loc for loc in sorted(locations) if loc not in templates]
    if unknown:
        sys.exit(f"ERROR: unknown location(s) not found in location_templates.txt: {', '.join(unknown)}")


def infer_culture_religion(first_location: str, templates: dict[str, dict]) -> tuple[str, str]:
    """Returns (culture, religion) from the first location's template entry."""
    attrs = templates.get(first_location, {})
    culture  = attrs.get('culture',  'castilian')
    religion = attrs.get('religion', 'catholic')
    return culture, religion


# ── parser (shared with promote_cores) ───────────────────────────────────────

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


def extract_locations(lines, block):
    locations = set()
    for li in range(block['open'], block['close'] + 1):
        text = lines[li].split('#')[0]
        text = re.sub(r'\b\w+\s*=\s*\{', '', text)
        text = text.replace('}', '')
        for token in text.split():
            if token:
                locations.add(token)
    return locations


# ── 10_countries.txt ──────────────────────────────────────────────────────────

def update_countries_file(tag, locations, rank, includes):
    text = COUNTRIES_FILE.read_text(encoding='utf-8')
    lines = text.splitlines(keepends=True)

    print(f"Loaded {len(lines)} lines from {COUNTRIES_FILE.name}")

    countries = parse_countries(lines)
    print(f"Parsed {len(countries)} country blocks")

    if tag in countries:
        print(f"ERROR: tag {tag} already exists in {COUNTRIES_FILE.name}", file=sys.stderr)
        sys.exit(1)

    # Find which locations are currently owned by other countries
    removal_map = defaultdict(list)  # location -> [(owner_tag, block)]
    for owner_tag, info in countries.items():
        for block in info['blocks']:
            owned = extract_locations(lines, block)
            for loc in owned & locations:
                removal_map[loc].append((owner_tag, block))

    # Build removal edits (back-to-front safe via dict)
    edits = {}

    block_removals = defaultdict(set)
    for loc, entries in removal_map.items():
        for owner_tag, block in entries:
            block_removals[(owner_tag, block['open'])].add(loc)

    block_by_open = {}
    for owner_tag, info in countries.items():
        for block in info['blocks']:
            block_by_open[block['open']] = (owner_tag, block)

    for (owner_tag, block_open), to_remove in block_removals.items():
        _, block = block_by_open[block_open]
        for li in range(block['open'] + 1, block['close']):
            original = lines[li]
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

    # Build the new country block
    loc_line = '\t\t\t' + ' '.join(sorted(locations)) + '\n'
    include_lines = ''.join(f'\t\tinclude = "{inc}"\n' for inc in includes)
    new_block = (
        f'\n'
        f'\t#{tag}\n'
        f'\t{tag} = {{\n'
        f'\t\town_control_core = {{\n'
        f'{loc_line}'
        f'\t\t}}\n'
        f'\n'
        f'\t\tstarting_technology_level = 3\n'
        f'{include_lines}'
        f'\n'
        f'\t\tgovernment = {{\n'
        f'\t\t\ttype = monarchy\n'
        f'\t\t\their_selection = cognatic_primogeniture\n'
        f'\t\t}}\n'
        f'\n'
        f'\t\tcountry_rank = {rank}\n'
        f'\t}}\n'
    )

    # Insert before the inner closing brace of 'countries = { countries = { ... } }'.
    # The file ends with two unindented '}' lines. We want the second-to-last
    # so that both closing braces remain after the new block.
    unindented_closes = [li for li, l in enumerate(lines) if l.rstrip('\n\r') == '}']
    if len(unindented_closes) < 2:
        print("ERROR: could not find two unindented closing braces in countries file", file=sys.stderr)
        sys.exit(1)
    insert_at = unindented_closes[-2]

    # Apply edits
    new_lines = []
    for li, line in enumerate(lines):
        if li == insert_at:
            new_lines.append(new_block)
        if li in edits:
            if edits[li] != '':
                new_lines.append(edits[li])
        else:
            new_lines.append(line)

    COUNTRIES_FILE.write_text(''.join(new_lines), encoding='utf-8')
    print(f"Updated {COUNTRIES_FILE.name}: added {tag}, removed {len(removal_map)} locations from other countries")
    for loc, entries in removal_map.items():
        for owner_tag, _ in entries:
            print(f"  removed '{loc}' from {owner_tag}")


# ── panda_express_map.txt (country definitions) ───────────────────────────────

def update_definitions_file(tag, name, color_rgb, culture, religion):
    r, g, b = color_rgb
    entry = (
        f'\n'
        f'{tag} = {{ # {name}\n'
        f'\tcolor = rgb {{ {r} {g} {b} }}\n'
        f'\n'
        f'\tculture_definition = {culture}\n'
        f'\treligion_definition = {religion}\n'
        f'}}\n'
    )
    if not DEFINITIONS_FILE.exists():
        DEFINITIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        DEFINITIONS_FILE.write_text('', encoding='utf-8')
        print(f"Created {DEFINITIONS_FILE.name}")
    existing = DEFINITIONS_FILE.read_text(encoding='utf-8')
    if re.search(rf'^{tag}\s*=', existing, re.MULTILINE):
        print(f"ERROR: tag {tag} already exists in {DEFINITIONS_FILE.name}", file=sys.stderr)
        sys.exit(1)
    DEFINITIONS_FILE.write_text(existing.rstrip() + entry, encoding='utf-8')
    print(f"Updated {DEFINITIONS_FILE.name}: added {tag}")


# ── country_names_l_english.yml ───────────────────────────────────────────────

def update_localization_file(tag, name, adj):
    # Read raw bytes to detect BOM
    raw = LOCALIZATION_FILE.read_bytes()
    has_bom = raw.startswith(b'\xef\xbb\xbf')
    text = raw[3:].decode('utf-8') if has_bom else raw.decode('utf-8')

    if re.search(rf'^ {tag}:', text, re.MULTILINE):
        print(f"ERROR: tag {tag} already exists in {LOCALIZATION_FILE.name}", file=sys.stderr)
        sys.exit(1)
    if re.search(rf':\s*"{re.escape(name)}"', text):
        print(f"ERROR: name \"{name}\" already exists in {LOCALIZATION_FILE.name}", file=sys.stderr)
        sys.exit(1)

    entry = f' {tag}: "{name}"\n {tag}_ADJ: "{adj}"\n'
    updated = text.rstrip() + '\n' + entry

    out_bytes = (b'\xef\xbb\xbf' if has_bom else b'') + updated.encode('utf-8')
    LOCALIZATION_FILE.write_bytes(out_bytes)
    print(f"Updated {LOCALIZATION_FILE.name}: added {tag} / {tag}_ADJ")


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Create a new country in the Panda Express Map mod.")
    p.add_argument('--tag',       default=None, help='Country tag (auto-generated if omitted)')
    p.add_argument('--name',      required=True, help='Country name, e.g. "Toledo"')
    p.add_argument('--name-adj',  required=True, dest='adj', help='Country adjective, e.g. "Toledan"')
    p.add_argument('--locations', nargs='+', default=[], help='Individual location names to assign')
    p.add_argument('--provinces', nargs='+', default=[], help='Province names (resolved to locations)')
    p.add_argument('--color',     nargs=3, type=int, metavar=('R', 'G', 'B'),
                   default=None, help='Map color as R G B (default: random)')
    p.add_argument('--region',    required=True, choices=['iberian', 'french'],
                   help='Region preset: iberian or french')
    p.add_argument('--culture',   default=None, help='Culture definition (overrides inferred value from first location)')
    p.add_argument('--religion',  default=None, dest='religion_explicit',
                   help='Religion definition (default: inferred from first location)')
    p.add_argument('--rank',      default='rank_duchy',
                   choices=['rank_county', 'rank_duchy', 'rank_kingdom', 'rank_empire'],
                   help='Country rank (default: rank_duchy)')
    p.add_argument('--includes',  nargs='+', default=None,
                   help='Include templates (overrides region default)')
    return p.parse_args()


def main():
    args = parse_args()
    tag       = (args.tag.upper() if args.tag else generate_tag(args.region))
    color     = args.color if args.color is not None else [random.randint(0, 255) for _ in range(3)]
    locations = set(args.locations) | set(resolve_provinces(args.provinces))
    if not locations:
        print("ERROR: no locations specified (use --locations and/or --provinces)", file=sys.stderr)
        sys.exit(1)
    region    = REGION_DEFAULTS[args.region]
    includes  = args.includes if args.includes is not None else region['includes']

    templates = load_location_templates()
    validate_locations(locations, templates)

    # Infer culture/religion from the first explicit location (or first resolved location)
    first_location = (args.locations or sorted(locations))[0]
    inferred_culture, inferred_religion = infer_culture_religion(first_location, templates)
    culture  = args.culture   if args.culture  is not None else inferred_culture
    religion = args.religion_explicit if args.religion_explicit is not None else inferred_religion

    print(f"\n=== Creating country {tag} ({args.name}) ===")
    print(f"Region    : {args.region}")
    print(f"Locations : {sorted(locations)}")
    print(f"Rank      : {args.rank}")
    print(f"Color     : rgb {color}")
    print(f"Culture   : {culture} (from {first_location})")
    print(f"Religion  : {religion} (from {first_location})\n")

    update_countries_file(tag, locations, args.rank, includes)
    update_definitions_file(tag, args.name, color, culture, religion)
    update_localization_file(tag, args.name, args.adj)

    print(f"\nDone. Remember to reload the mod fully in the launcher before testing.")


if __name__ == '__main__':
    main()
