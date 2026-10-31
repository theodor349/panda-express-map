"""
build_wars.py — write the mod's 16_wars.txt.

Reads the base file on every run, so game updates carry over. Removes participants that are only
in a war as subjects, because the mod starts with no subjects, and removes the wars in DROP_WARS.

Usage:
    python scripts/helpers/build_wars.py
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
from setup_blocks import find_block_extent, strip_comments

_DEFAULT_GAME_PATH = r"E:\SteamLibrary\steamapps\common\Europa Universalis V\game"
_GAME_PATH = Path(os.environ.get("EU5_GAME_PATH", _DEFAULT_GAME_PATH))
_DEFAULT_MOD_PATH = Path(__file__).parent.parent.parent
_MOD_PATH = Path(os.environ.get("EU5_MOD_PATH", _DEFAULT_MOD_PATH))
BASE_FILE = _GAME_PATH / "main_menu/setup/1337/16_wars.txt"
DEFAULT_OUTPUT = _MOD_PATH / "main_menu/setup/1337/16_wars.txt"

# With its subjects gone, this war's scripted land demands have no valid targets.
DROP_WARS = {"SCALIGER_WAR_NAME"}

WAR_RE = re.compile(r"(?m)^\t(?:war|civil_war)\s*=\s*\{")
PARTICIPANT_RE = re.compile(r"(?m)^[ \t]*(?:attacker|defender)\s*=\s*\{")
SUBJECT_RE = re.compile(r"\breason\s*=\s*(?:Subject|Overlord)\b")


def remove_extent(text: str, start: int, end: int) -> str:
    """Remove text[start:end + 1] and its line break."""
    after = end + 1
    if text[after:after + 1] == "\n":
        after += 1
    return text[:start] + text[after:]


def strip_participants(war: str) -> tuple[str, int]:
    removed = 0
    matches = list(PARTICIPANT_RE.finditer(war))
    for match in reversed(matches):
        start, end = find_block_extent(war, match.end() - 1)
        if SUBJECT_RE.search(strip_comments(war[start:end + 1])):
            war = remove_extent(war, match.start(), end)
            removed += 1
    return war, removed


def validate(war: str) -> None:
    code = strip_comments(war)
    name = re.search(r'name\s*=\s*"(\w+)"', code)
    label = name.group(1) if name else "unnamed war"
    if not re.search(r"\battacker\s*=", code) or not re.search(r"\bdefender\s*=", code):
        sys.exit(f"ERROR: {label} would be left without a side")
    participants = set(re.findall(r"\bcountry\s*=\s*(\w+)", code))
    dangling = set(re.findall(r"\bcaller\s*=\s*(\w+)", code)) - participants
    if dangling:
        sys.exit(f"ERROR: {label} has callers that are no longer participants: {sorted(dangling)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Write the mod's 16_wars.txt.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path to write")
    args = parser.parse_args()

    if not BASE_FILE.exists():
        sys.exit(f"ERROR: file not found: {BASE_FILE}")

    text = BASE_FILE.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")
    matches = list(WAR_RE.finditer(text))
    if not matches:
        sys.exit("ERROR: no wars found in 16_wars.txt")

    participants = 0
    dropped: set[str] = set()
    for match in reversed(matches):
        start, end = find_block_extent(text, match.end() - 1)
        war = text[match.start():end + 1]
        name = re.search(r'name\s*=\s*"(\w+)"', strip_comments(war))
        if name and name.group(1) in DROP_WARS:
            dropped.add(name.group(1))
            text = remove_extent(text, match.start(), end)
            continue
        stripped, removed = strip_participants(war)
        validate(stripped)
        participants += removed
        text = text[:match.start()] + stripped + text[end + 1:]

    missing = DROP_WARS - dropped
    if missing:
        sys.exit(f"ERROR: wars to remove not found: {sorted(missing)}")

    code = strip_comments(text)
    if code.count("{") != code.count("}"):
        sys.exit("ERROR: unbalanced braces in the generated 16_wars.txt")

    write_text_with_retry(Path(args.output), text)
    print(f"Removed {participants} subject participant(s) and {len(dropped)} war(s); wrote {Path(args.output).name}.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        sys.exit(f"ERROR: {exc}")
