"""
build_international_organizations.py — write the mod's 15_international_organizations.txt.

Reads the base file on every run, so game updates carry over, and removes members the game would
drop on day 1 because they have no land. Also removes Lordship of Ireland's open-ended term for
Edward III, because the mod gives The Pale its own ruler.

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
DEFAULT_OUTPUT = _MOD_PATH / "main_menu/setup/1337/15_international_organizations.txt"

# Pop-based countries that fail the game's check even though their locations are unchanged.
ALWAYS_REMOVE = {"TVA", "DDI"}
# Lists other than members that name countries the game drops on day 1.
HRE_LISTS = {"imperial_prince": {"ORT", "GRK"}}
OPEN_TERM = re.compile(r"(?m)^[ \t]*ruler_term\s*=\s*\{\s*character\s*=\s*eng_edward_iii\s+start_date\s*=\s*1327\.1\.25\s+regnal_number\s*=\s*3\s*\}[ \t]*\n")


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
    text, terms = OPEN_TERM.subn("", text)
    if terms != 1:
        sys.exit(f"ERROR: expected one open-ended Edward III term, found {terms}")

    write_text_with_retry(Path(args.output), text)
    print(f"Removed {members} organization member(s) with no land; wrote {Path(args.output).name}.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        sys.exit(f"ERROR: {exc}")
