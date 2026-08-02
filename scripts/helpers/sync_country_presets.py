"""Synchronize generated country presets and capitals from new_countries.txt.

Usage:
    python scripts/helpers/sync_country_presets.py
    python scripts/helpers/sync_country_presets.py --spec mod_changes/new_countries.txt
"""

import argparse
import os
import re
import shlex
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
    load_dotenv(Path(__file__).parent.parent.parent / ".env.local", override=True)
except ImportError:
    pass

ROOT = Path(os.environ.get("EU5_MOD_PATH", Path(__file__).parent.parent.parent))
BASE_GAME = Path(os.environ.get(
    "EU5_GAME_PATH",
    r"E:\SteamLibrary\steamapps\common\Europa Universalis V\game",
))
DEFAULT_SPEC = ROOT / "mod_changes/new_countries.txt"
DEFAULT_COUNTRIES = ROOT / "main_menu/setup/start/10_countries.txt"
DEFAULT_DEFINITIONS = ROOT / "in_game/setup/countries/panda_express_map.txt"

sys.path.insert(0, str(Path(__file__).parent))
from create_country import IBERIAN_PRESETS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Synchronize generated country presets and capitals.")
    parser.add_argument("--spec", default=str(DEFAULT_SPEC))
    parser.add_argument("--countries", default=str(DEFAULT_COUNTRIES))
    parser.add_argument("--definitions", default=str(DEFAULT_DEFINITIONS))
    return parser.parse_args()


def parse_spec(path: Path) -> list[dict[str, str]]:
    entries = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.partition("#")[0].strip()
        if not line:
            continue
        tokens = shlex.split(line)
        values: dict[str, str] = {}
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token.startswith("--"):
                key = token[2:]
                i += 1
                collected = []
                while i < len(tokens) and not tokens[i].startswith("--"):
                    collected.append(tokens[i])
                    i += 1
                if collected:
                    values[key] = " ".join(collected)
            else:
                i += 1
        if values.get("region") == "iberian":
            if "name" not in values:
                sys.exit(f"ERROR: missing --name at {path}:{line_number}")
            entries.append(values)
    return entries


def name_to_tag(definitions: str) -> dict[str, str]:
    return {
        match.group(2).strip(): match.group(1)
        for match in re.finditer(r"^([A-Z0-9]{3})\s*=\s*\{\s*#\s*(.+?)\s*$", definitions, re.MULTILINE)
    }


def find_block(text: str, pattern: str) -> tuple[int, int] | None:
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        return None
    open_brace = text.index("{", match.start())
    depth = 0
    for index in range(open_brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return match.start(), index + 1
    sys.exit(f"ERROR: unmatched block beginning at character {match.start()}")


def update_country_block(block: str, preset: str, capital: str | None) -> str:
    template = IBERIAN_PRESETS[preset]
    block, replacements = re.subn(
        r'(?m)^\t\tinclude = "(?:catholic_monarchy_not_present|panda_iberian_[a-z_]+)"$',
        f'\t\tinclude = "{template}"',
        block,
        count=1,
    )
    if replacements != 1:
        sys.exit("ERROR: could not identify generated government include in country block")

    if capital:
        capital_line = f"\t\tcapital = {capital}"
        if re.search(r"(?m)^\t\tcapital\s*=", block):
            block = re.sub(r"(?m)^\t\tcapital\s*=.*$", capital_line, block, count=1)
        else:
            block = block[:-1].rstrip() + f"\n\n{capital_line}\n\t}}"
    return block


def update_definition_block(block: str, culture: str | None, religion: str | None) -> str:
    if culture:
        block, count = re.subn(
            r"(?m)^\tculture_definition\s*=\s*\w+\s*$",
            f"\tculture_definition = {culture}",
            block,
            count=1,
        )
        if count != 1:
            sys.exit("ERROR: country definition has no culture_definition")
    if religion:
        block, count = re.subn(
            r"(?m)^\treligion_definition\s*=\s*\w+\s*$",
            f"\treligion_definition = {religion}",
            block,
            count=1,
        )
        if count != 1:
            sys.exit("ERROR: country definition has no religion_definition")
    return block


def main() -> None:
    args = parse_args()
    spec_path = Path(args.spec)
    countries_path = Path(args.countries)
    definitions_path = Path(args.definitions)
    for path in (spec_path, countries_path, definitions_path):
        if not path.exists():
            sys.exit(f"ERROR: file not found: {path}")

    entries = parse_spec(spec_path)
    countries = countries_path.read_text(encoding="utf-8")
    definitions = definitions_path.read_text(encoding="utf-8")
    tags = name_to_tag(definitions)
    failures = []

    for entry in entries:
        name = entry["name"]
        tag = tags.get(name)
        if not tag:
            failures.append(f"{name}: no generated tag found")
            continue
        preset = entry.get("preset", "feudal")
        if preset not in IBERIAN_PRESETS:
            failures.append(f"{name}: unknown preset {preset!r}")
            continue

        country_extent = find_block(countries, rf"^\t{re.escape(tag)}\s*=\s*\{{")
        definition_extent = find_block(definitions, rf"^{re.escape(tag)}\s*=\s*\{{")
        if not country_extent or not definition_extent:
            failures.append(f"{name} ({tag}): country or definition block not found")
            continue

        start, end = country_extent
        updated = update_country_block(countries[start:end], preset, entry.get("capital"))
        countries = countries[:start] + updated + countries[end:]

        start, end = definition_extent
        updated = update_definition_block(
            definitions[start:end], entry.get("culture"), entry.get("religion")
        )
        definitions = definitions[:start] + updated + definitions[end:]
        print(f"  {tag} {name}: preset={preset}, capital={entry.get('capital', '(unchanged)')}")

    if failures:
        print("ERROR: preset synchronization failed:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        sys.exit(1)

    countries_path.write_text(countries, encoding="utf-8")
    definitions_path.write_text(definitions, encoding="utf-8")
    print(f"Synchronized {len(entries)} Iberian countries.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        sys.exit(f"ERROR: {exc}")
