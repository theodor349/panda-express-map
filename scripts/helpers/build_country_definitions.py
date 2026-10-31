"""
build_country_definitions.py — write the mod's copies of base country definition files.

Reads the base files on every run, so game updates carry over, then sets a country's culture
where its core locations no longer hold any of its base culture.

Usage:
    python scripts/helpers/build_country_definitions.py
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
from set_country_ruler import find_block_extent
from setup_blocks import rewrite_countries

_DEFAULT_GAME_PATH = r"E:\SteamLibrary\steamapps\common\Europa Universalis V\game"
_GAME_PATH = Path(os.environ.get("EU5_GAME_PATH", _DEFAULT_GAME_PATH))
_DEFAULT_MOD_PATH = Path(__file__).parent.parent.parent
_MOD_PATH = Path(os.environ.get("EU5_MOD_PATH", _DEFAULT_MOD_PATH))
BASE_DIR = _GAME_PATH / "in_game/setup/countries"
DEFAULT_OUTPUT = _MOD_PATH / "in_game/setup/countries"
COUNTRIES_FILE = _MOD_PATH / "main_menu/setup/1337/10_countries.txt"

CULTURES = {
    "british_isles.txt": {"CMS": "welsh"},
    "east_asia.txt": {"LNG": "yi_culture"},
    "indonesia.txt": {"KIM": "maguindanao_culture"},
}


def tag_block(text: str, tag: str, name: str) -> tuple[int, int]:
    match = re.search(rf"(?m)^{tag}\s*=\s*\{{", text)
    if not match:
        sys.exit(f"ERROR: {tag} not found in {name}")
    return find_block_extent(text, match.end() - 1)


def remove_from_tolerated(path: Path) -> None:
    """A country's new primary culture can't also be in its tolerated cultures."""
    new_cultures = {tag: culture for tags in CULTURES.values() for tag, culture in tags.items()}
    removed = 0

    def rewrite(tag: str, body: str) -> str:
        nonlocal removed
        if tag not in new_cultures:
            return body

        def strip_list(match: re.Match[str]) -> str:
            nonlocal removed
            inner, count = re.subn(rf"\b{new_cultures[tag]}\b", "", match.group(2))
            removed += count
            return match.group(1) + inner + match.group(3)

        return re.sub(r"(tolerated_cultures\s*=\s*\{)([^{}]*)(\})", strip_list, body)

    text = rewrite_countries(path.read_text(encoding="utf-8"), rewrite)
    write_text_with_retry(path, text)
    print(f"Removed {removed} primary culture(s) from tolerated cultures.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Write the mod's copies of base country definition files.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Directory to write to")
    parser.add_argument("--countries", default=str(COUNTRIES_FILE), help="Path to 10_countries.txt")
    args = parser.parse_args()

    for name in sorted(CULTURES):
        path = BASE_DIR / name
        if not path.exists():
            sys.exit(f"ERROR: file not found: {path}")
        text = path.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")

        for tag, culture in CULTURES[name].items():
            start, end = tag_block(text, tag, name)
            block, count = re.subn(r"\bculture_definition\s*=\s*\w+", f"culture_definition = {culture}", text[start:end])
            if count != 1:
                sys.exit(f"ERROR: expected one culture_definition on {tag} in {name}, found {count}")
            text = text[:start] + block + text[end:]

        write_bytes_with_retry(Path(args.output) / name, b"\xef\xbb\xbf" + text.encode("utf-8"))
        print(f"Wrote {name}")

    remove_from_tolerated(Path(args.countries))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        sys.exit(f"ERROR: {exc}")
