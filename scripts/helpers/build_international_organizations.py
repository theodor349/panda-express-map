"""
build_international_organizations.py — write the mod's 15_international_organizations.txt.

Reads the base file on every run, so game updates carry over, and removes members the game would
drop on day 1 because they have no land. Adds mod countries split from HRE members to the HRE.
Also removes the Lordship of Ireland, which has no valid leader once The Pale has its own ruler.

Usage:
    python scripts/helpers/build_international_organizations.py
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
from setup_blocks import country_bodies, country_type, find_block_extent, owned_locations, strip_patterns

_DEFAULT_GAME_PATH = r"E:\SteamLibrary\steamapps\common\Europa Universalis V\game"
_GAME_PATH = Path(os.environ.get("EU5_GAME_PATH", _DEFAULT_GAME_PATH))
_DEFAULT_MOD_PATH = Path(__file__).parent.parent.parent
_MOD_PATH = Path(os.environ.get("EU5_MOD_PATH", _DEFAULT_MOD_PATH))
BASE_FILE = _GAME_PATH / "main_menu/setup/1337/15_international_organizations.txt"
COUNTRIES_FILE = _MOD_PATH / "main_menu/setup/1337/10_countries.txt"
DEFINITIONS_FILE = _MOD_PATH / "in_game/setup/countries/panda_express_map.txt"
DEFAULT_OUTPUT = _MOD_PATH / "main_menu/setup/1337/15_international_organizations.txt"

# Mod countries split from HRE members. New countries otherwise start outside the HRE.
HRE_NEW_MEMBERS = {"Rosenberg", "Hradec", "Eger"}
# Pop-based countries that fail the game's check even though their locations are unchanged.
ALWAYS_REMOVE = {"TVA", "DDI"}
# Lists other than members that name countries the game drops on day 1.
HRE_LISTS = {"imperial_prince": {"ORT", "GRK"}}
# The Lordship of Ireland's leader must be a scripted character, and it disbands without one. The mod
# gives The Pale a random ruler instead of Edward III.
REMOVE_ORGANIZATIONS = {"lordship_of_ireland"}


def remove_organizations(text: str) -> str:
    found: set[str] = set()
    for match in reversed(list(re.finditer(r"(?m)^[ \t]*add_international_organization\s*=\s*\{", text))):
        start, end = find_block_extent(text, match.end() - 1)
        kind = re.search(r"\btype\s*=\s*(\w+)", text[start:end])
        if kind and kind.group(1) in REMOVE_ORGANIZATIONS:
            found.add(kind.group(1))
            text = text[:match.start()] + text[end + 1:].lstrip("\n")
    missing = REMOVE_ORGANIZATIONS - found
    if missing:
        sys.exit(f"ERROR: organizations to remove not found: {sorted(missing)}")
    return text


def edit_named_blocks(text: str, name: str, tags: set[str]) -> tuple[str, int]:
    """Remove tags from every block with this name."""
    if not tags:
        return text, 0
    pattern = [re.compile(r"(?<![\w:.])(?:" + "|".join(sorted(tags)) + r")(?![\w:.])")]
    parts: list[str] = []
    cursor = 0
    removed = 0
    for match in re.finditer(rf"(?m)^[ \t]*{name}\s*=\s*\{{", text):
        start, end = find_block_extent(text, match.end() - 1)
        body = text[start + 1:end]
        removed += sum(len(pattern[0].findall(re.sub(r"#[^\n]*", "", line))) for line in body.split("\n"))
        parts.append(text[cursor:start + 1])
        parts.append(strip_patterns(body, pattern))
        cursor = end
    parts.append(text[cursor:])
    return "".join(parts), removed


def add_hre_members(text: str) -> str:
    definitions = DEFINITIONS_FILE.read_text(encoding="utf-8-sig")
    tags = {
        match.group(2).strip(): match.group(1)
        for match in re.finditer(r"(?m)^([A-Z0-9]{3})\s*=\s*\{\s*#\s*(.+?)\s*$", definitions)
    }
    missing = HRE_NEW_MEMBERS - set(tags)
    if missing:
        sys.exit(f"ERROR: no tag found for {sorted(missing)} in {DEFINITIONS_FILE.name}")
    organization = re.search(r"(?m)^[ \t]*type\s*=\s*hre\b", text)
    members = re.compile(r"(?m)^[ \t]*members\s*=\s*\{").search(text, organization.end()) if organization else None
    if not members:
        sys.exit("ERROR: could not find the HRE members block")
    new_members = " ".join(sorted(tags[name] for name in HRE_NEW_MEMBERS))
    return text[:members.end()] + f"\n\t\t\t{new_members}" + text[members.end():]


def main() -> None:
    parser = argparse.ArgumentParser(description="Write the mod's 15_international_organizations.txt.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path to write")
    args = parser.parse_args()

    for required in (BASE_FILE, COUNTRIES_FILE):
        if not required.exists():
            sys.exit(f"ERROR: file not found: {required}")

    countries = country_bodies(COUNTRIES_FILE.read_text(encoding="utf-8"))
    gone = {
        tag for tag, body in countries.items()
        if not owned_locations(body) and country_type(body) in (None, "army")
    } | ALWAYS_REMOVE

    text = BASE_FILE.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")
    text, members = edit_named_blocks(text, "members", gone)
    for name, tags in HRE_LISTS.items():
        text, _ = edit_named_blocks(text, name, tags)
    text = remove_organizations(text)
    text = add_hre_members(text)

    write_text_with_retry(Path(args.output), text)
    print(f"Removed {members} organization member(s) with no land; wrote {Path(args.output).name}.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        sys.exit(f"ERROR: {exc}")
