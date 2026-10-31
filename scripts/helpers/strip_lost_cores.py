"""
strip_lost_cores.py — remove cores that countries keep on land the mod split away from them.

consolidate_locations.py gives a source country cores on the land it loses. A country with land that
owned a location in the base game and no longer owns it loses its core there, so it has no cheap
casus belli to take it back. Countries with no land keep their cores, so they can still be released.

Usage:
    python scripts/helpers/strip_lost_cores.py
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
from setup_blocks import core_locations, country_bodies, find_block_extent, owned_locations, rewrite_countries

_DEFAULT_GAME_PATH = r"E:\SteamLibrary\steamapps\common\Europa Universalis V\game"
_GAME_PATH = Path(os.environ.get("EU5_GAME_PATH", _DEFAULT_GAME_PATH))
_DEFAULT_MOD_PATH = Path(__file__).parent.parent.parent
_MOD_PATH = Path(os.environ.get("EU5_MOD_PATH", _DEFAULT_MOD_PATH))
BASE_FILE = _GAME_PATH / "main_menu/setup/1337/10_countries.txt"
DEFAULT_FILE = _MOD_PATH / "main_menu/setup/1337/10_countries.txt"


def remove_locations(body: str, locations: set[str]) -> str:
    pattern = re.compile(r"(?<![\w#])(?:" + "|".join(sorted(locations)) + r")(?!\w)")
    parts: list[str] = []
    cursor = 0
    for match in re.finditer(r"(?m)^[ \t]*our_cores_conquered_by_others\s*=\s*\{", body):
        start, end = find_block_extent(body, match.end() - 1)
        parts.append(body[cursor:start])
        parts.append(pattern.sub("", body[start:end]))
        cursor = end
    parts.append(body[cursor:])
    return "".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove cores on land the mod split away from a country.")
    parser.add_argument("--file", default=str(DEFAULT_FILE), help="Path to 10_countries.txt")
    args = parser.parse_args()

    path = Path(args.file)
    for required in (path, BASE_FILE):
        if not required.exists():
            sys.exit(f"ERROR: file not found: {required}")

    base = country_bodies(BASE_FILE.read_bytes().decode("utf-8-sig").replace("\r\n", "\n"))
    removed: dict[str, int] = {}

    def rewrite(tag: str, body: str) -> str:
        owned = owned_locations(body)
        if not owned:
            return body
        lost = (core_locations(body) & owned_locations(base.get(tag, ""))) - owned
        if not lost:
            return body
        removed[tag] = len(lost)
        return remove_locations(body, lost)

    write_text_with_retry(path, rewrite_countries(path.read_text(encoding="utf-8"), rewrite))
    summary = " ".join(f"{tag}={count}" for tag, count in sorted(removed.items()))
    print(f"Removed {sum(removed.values())} cores on lost land from {len(removed)} countries: {summary}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        sys.exit(f"ERROR: {exc}")
