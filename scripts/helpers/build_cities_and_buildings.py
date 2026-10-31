"""
build_cities_and_buildings.py — write the mod's 07_cities_and_buildings.txt.

Reads the base file on every run, so game updates carry over, and removes buildings the game
rejects at start because the mod removes the subject link or capital they need.

Usage:
    python scripts/helpers/build_cities_and_buildings.py
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
from create_country import write_bytes_with_retry

_DEFAULT_GAME_PATH = r"E:\SteamLibrary\steamapps\common\Europa Universalis V\game"
_GAME_PATH = Path(os.environ.get("EU5_GAME_PATH", _DEFAULT_GAME_PATH))
_DEFAULT_MOD_PATH = Path(__file__).parent.parent.parent
_MOD_PATH = Path(os.environ.get("EU5_MOD_PATH", _DEFAULT_MOD_PATH))
BASE_FILE = _GAME_PATH / "main_menu/setup/1337/07_cities_and_buildings.txt"
DEFAULT_OUTPUT = _MOD_PATH / "main_menu/setup/1337/07_cities_and_buildings.txt"

REMOVE = [
    ("hanseatic_shipwright_guild", "hamburg"),
    ("hanseatic_shipwright_guild", "lubeck"),
    ("calmecac", "tenochtitlan"),
    ("telpochcalli", "tenochtitlan"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Write the mod's 07_cities_and_buildings.txt.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path to write")
    args = parser.parse_args()

    if not BASE_FILE.exists():
        sys.exit(f"ERROR: file not found: {BASE_FILE}")

    data = BASE_FILE.read_bytes()
    bom = b"\xef\xbb\xbf" if data.startswith(b"\xef\xbb\xbf") else b""
    text = data[len(bom):].decode("utf-8")

    for building, location in REMOVE:
        pattern = rf"(?m)^[ \t]*{building}\s*=\s*\{{[^{{}}]*\blocation\s*=\s*{location}\b[^{{}}]*\}}[ \t]*\r?\n"
        text, count = re.subn(pattern, "", text)
        if count != 1:
            sys.exit(f"ERROR: expected one {building} at {location}, found {count}")

    write_bytes_with_retry(Path(args.output), bom + text.encode("utf-8"))
    print(f"Removed {len(REMOVE)} building(s); wrote {Path(args.output).name}.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        sys.exit(f"ERROR: {exc}")
