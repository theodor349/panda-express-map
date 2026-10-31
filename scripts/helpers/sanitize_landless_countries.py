"""
sanitize_landless_countries.py — make countries with no land at start valid in 10_countries.txt.

  1. Removes laws, privileges and reforms that need land from their blocks, and points their
     includes at generated panda_landless_<template> copies without those entries.
  2. Gives countries with no land and no cores their base-game land as cores.
  3. Sets a capital on countries that only have cores and no capital.

Run this after every step that changes land, on a build started from fresh base files.

Usage:
    python scripts/helpers/sanitize_landless_countries.py
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
from create_country import write_bytes_with_retry, write_text_with_retry
from setup_blocks import (
    INCLUDE_RE,
    core_locations,
    country_bodies,
    country_type,
    find_block_extent,
    owned_locations,
    read_template,
    rewrite_countries,
    strip_comments,
    strip_patterns,
)
from strip_unownable_locations import DEFAULT_MAP, load_unownable

_DEFAULT_GAME_PATH = r"E:\SteamLibrary\steamapps\common\Europa Universalis V\game"
_GAME_PATH = Path(os.environ.get("EU5_GAME_PATH", _DEFAULT_GAME_PATH))
_DEFAULT_MOD_PATH = Path(__file__).parent.parent.parent
_MOD_PATH = Path(os.environ.get("EU5_MOD_PATH", _DEFAULT_MOD_PATH))
DEFAULT_FILE = _MOD_PATH / "main_menu/setup/1337/10_countries.txt"
BASE_FILE = _GAME_PATH / "main_menu/setup/1337/10_countries.txt"
MOD_TEMPLATES = _MOD_PATH / "main_menu/setup/templates"
BASE_TEMPLATES = _GAME_PATH / "main_menu/setup/templates"
COUNTRY_DEFINITIONS = _GAME_PATH / "in_game/setup/countries"

VARIANT_PREFIX = "panda_landless_"

# Countries the base game keeps dormant and the mod replaces with its own: their cores would
# overlap several mod countries.
SKIP_CORES = {"ALV", "ATU", "JAE", "TOL"}

NEEDS_LAND = [
    re.compile(r"\beducation_masses_law\s*=\s*\w+"),
    re.compile(r"\bdistribution_of_power_law\s*=\s*dop_law_english_parliament\b"),
    re.compile(
        r"\b(?:sponsor_maritime_contracts|noble_sponsored_navy|shipwright_contracts|jain_banking_rights"
        r"|jain_scholars|dharmic_dhimmi_communities|wayfinders_reform|iron_ring_reform"
        r"|french_ducal_vassal_reform)\b"
    ),
]


def historic_tags() -> set[str]:
    """Return tags defined with is_historic = yes, which need no cores."""
    tags: set[str] = set()
    for path in COUNTRY_DEFINITIONS.rglob("*.txt"):
        text = strip_comments(path.read_text(encoding="utf-8-sig", errors="replace"))
        for match in re.finditer(r"(?m)^(\w{3})\s*=\s*\{", text):
            start, end = find_block_extent(text, match.end() - 1)
            if re.search(r"\bis_historic\s*=\s*yes\b", text[start:end]):
                tags.add(match.group(1))
    return tags


class TemplateVariants:
    """Generates panda_landless_ copies of templates that contain land-only entries."""

    def __init__(self) -> None:
        self.directories = [MOD_TEMPLATES, BASE_TEMPLATES]
        self.needs_variant: dict[str, bool] = {}
        self.generated: set[str] = set()

    def has_land_entries(self, name: str) -> bool:
        if name not in self.needs_variant:
            self.needs_variant[name] = False
            text = read_template(name, self.directories)
            if text is not None:
                self.needs_variant[name] = strip_patterns(text, NEEDS_LAND) != text or any(
                    self.has_land_entries(m.group(2)) for m in INCLUDE_RE.finditer(strip_comments(text))
                )
        return self.needs_variant[name]

    def redirect_includes(self, text: str) -> str:
        def replace(match: re.Match[str]) -> str:
            name = match.group(2)
            if not self.has_land_entries(name):
                return match.group(0)
            self.generate(name)
            return f'{match.group(1)}"{VARIANT_PREFIX}{name}"'

        return INCLUDE_RE.sub(replace, text)

    def generate(self, name: str) -> None:
        if name in self.generated:
            return
        self.generated.add(name)
        text = read_template(name, self.directories)
        output = self.redirect_includes(strip_patterns(text, NEEDS_LAND))
        write_bytes_with_retry(MOD_TEMPLATES / f"{VARIANT_PREFIX}{name}.txt", b"\xef\xbb\xbf" + output.encode("utf-8"))


def insert_before_end(body: str, line: str) -> str:
    return body.rstrip() + f"\n\t\t{line}\n\t"


def set_cores(body: str, locations: list[str]) -> str:
    block = f"our_cores_conquered_by_others = {{\n\t\t\t{' '.join(locations)}\n\t\t}}"
    body, count = re.subn(r"(?m)^\t\tour_cores_conquered_by_others\s*=\s*\{[^{}]*\}", "\t\t" + block, body, count=1)
    return body if count else insert_before_end(body, block)


def main() -> None:
    parser = argparse.ArgumentParser(description="Make countries with no land at start valid.")
    parser.add_argument("--file", default=str(DEFAULT_FILE), help="Path to 10_countries.txt")
    args = parser.parse_args()

    path = Path(args.file)
    for required in (path, BASE_FILE, BASE_TEMPLATES, COUNTRY_DEFINITIONS, DEFAULT_MAP):
        if not required.exists():
            sys.exit(f"ERROR: not found: {required}")

    text = path.read_text(encoding="utf-8")
    base = country_bodies(BASE_FILE.read_text(encoding="utf-8-sig"))
    unownable = load_unownable(DEFAULT_MAP)
    historic = historic_tags()
    variants = TemplateVariants()
    stats = {"stripped": 0, "cores": 0, "capitals": 0}
    no_source: list[str] = []

    def rewrite(tag: str, body: str) -> str:
        if owned_locations(body):
            return body
        kind = country_type(body)

        if kind != "building":
            cleaned = variants.redirect_includes(strip_patterns(body, NEEDS_LAND))
            stats["stripped"] += cleaned != body
            body = cleaned

        if kind is None and not core_locations(body) and tag not in historic and tag not in SKIP_CORES:
            source = owned_locations(base.get(tag, "")) or core_locations(base.get(tag, ""))
            cores = sorted(source - unownable)
            if cores:
                body = set_cores(body, cores)
                stats["cores"] += 1
            else:
                no_source.append(tag)

        if core_locations(body) and not re.search(r"(?m)^\t\tcapital\s*=", strip_comments(body)):
            candidates = sorted(core_locations(body) - unownable)
            if candidates:
                body = insert_before_end(body, f"capital = {candidates[0]}")
                stats["capitals"] += 1
        return body

    output = rewrite_countries(text, rewrite)
    write_text_with_retry(path, output)

    referenced = {m.group(2) for m in INCLUDE_RE.finditer(output)}
    for existing in MOD_TEMPLATES.glob(f"{VARIANT_PREFIX}*.txt"):
        if existing.stem not in referenced and existing.stem[len(VARIANT_PREFIX):] not in variants.generated:
            existing.unlink()

    print(f"Landless countries stripped of land-only entries: {stats['stripped']}")
    print(f"Generated templates: {len(variants.generated)}")
    print(f"Cores restored: {stats['cores']}; capitals set: {stats['capitals']}")
    if no_source:
        print(f"No base land or cores to restore for: {' '.join(sorted(no_source))}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        sys.exit(f"ERROR: {exc}")
