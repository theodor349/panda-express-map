"""
strip_subject_reforms.py — remove reforms that need a subject link from 10_countries.txt.

The mod starts with no subjects, so the game rejects these at start. Gafsa also gets a copy of
the Hafsid template without the entries reserved for Hafsid governors.

Usage:
    python scripts/helpers/strip_subject_reforms.py
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
from setup_blocks import read_template, rewrite_countries, strip_patterns

_DEFAULT_GAME_PATH = r"E:\SteamLibrary\steamapps\common\Europa Universalis V\game"
_GAME_PATH = Path(os.environ.get("EU5_GAME_PATH", _DEFAULT_GAME_PATH))
_DEFAULT_MOD_PATH = Path(__file__).parent.parent.parent
_MOD_PATH = Path(os.environ.get("EU5_MOD_PATH", _DEFAULT_MOD_PATH))
DEFAULT_FILE = _MOD_PATH / "main_menu/setup/1337/10_countries.txt"
MOD_TEMPLATES = _MOD_PATH / "main_menu/setup/templates"
BASE_TEMPLATES = _GAME_PATH / "main_menu/setup/templates"

SUBJECT_REFORMS = re.compile(r"(?m)^[ \t]*(?:french_appanage_reform|french_ducal_vassal_reform|son_in_law_rule)[ \t]*\n")
GOVERNOR_ENTRIES = [re.compile(r"\b(?:tun_strong_familial_governors|tun_arab_bedouins)\b")]
INDEPENDENT_TEMPLATE = "panda_hafsid_independent"
INDEPENDENT_TAG = "GFS"


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove reforms that need a subject link.")
    parser.add_argument("--file", default=str(DEFAULT_FILE), help="Path to 10_countries.txt")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        sys.exit(f"ERROR: file not found: {path}")

    template = read_template("hafsid_state", [BASE_TEMPLATES])
    if template is None:
        sys.exit("ERROR: template hafsid_state not found in the base game")
    independent = strip_patterns(template, GOVERNOR_ENTRIES)
    write_bytes_with_retry(MOD_TEMPLATES / f"{INDEPENDENT_TEMPLATE}.txt", b"\xef\xbb\xbf" + independent.encode("utf-8"))

    text = path.read_text(encoding="utf-8")
    text, removed = SUBJECT_REFORMS.subn("", text)

    redirected = 0

    def rewrite(tag: str, body: str) -> str:
        nonlocal redirected
        if tag != INDEPENDENT_TAG:
            return body
        body, redirected = re.subn(r'include\s*=\s*"hafsid_state"', f'include = "{INDEPENDENT_TEMPLATE}"', body)
        return body

    text = rewrite_countries(text, rewrite)
    if redirected != 1:
        sys.exit(f"ERROR: expected one hafsid_state include on {INDEPENDENT_TAG}, found {redirected}")

    write_text_with_retry(path, text)
    print(f"Removed {removed} subject reform(s); {INDEPENDENT_TAG} now uses {INDEPENDENT_TEMPLATE}.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        sys.exit(f"ERROR: {exc}")
