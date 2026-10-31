"""
ensure_random_rulers.py — add ruler = random to countries the mod gives land to that have no ruler.

Only countries with no land in the base game are changed. Base countries without a ruler line
can depend on a regent or other setup, and must stay as they are.

Usage:
    python scripts/helpers/ensure_random_rulers.py
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
from setup_blocks import INCLUDE_RE, country_bodies, owned_locations, read_template, rewrite_countries, strip_comments

_DEFAULT_GAME_PATH = r"E:\SteamLibrary\steamapps\common\Europa Universalis V\game"
_GAME_PATH = Path(os.environ.get("EU5_GAME_PATH", _DEFAULT_GAME_PATH))
_DEFAULT_MOD_PATH = Path(__file__).parent.parent.parent
_MOD_PATH = Path(os.environ.get("EU5_MOD_PATH", _DEFAULT_MOD_PATH))
DEFAULT_FILE = _MOD_PATH / "main_menu/setup/1337/10_countries.txt"
BASE_FILE = _GAME_PATH / "main_menu/setup/1337/10_countries.txt"
MOD_TEMPLATES = _MOD_PATH / "main_menu/setup/templates"
BASE_TEMPLATES = _GAME_PATH / "main_menu/setup/templates"


def main() -> None:
    parser = argparse.ArgumentParser(description="Add ruler = random to countries the mod gives land to.")
    parser.add_argument("--file", default=str(DEFAULT_FILE), help="Path to 10_countries.txt")
    args = parser.parse_args()

    path = Path(args.file)
    for required in (path, BASE_FILE):
        if not required.exists():
            sys.exit(f"ERROR: file not found: {required}")

    base = country_bodies(BASE_FILE.read_text(encoding="utf-8-sig"))
    added: list[str] = []

    def rewrite(tag: str, body: str) -> str:
        if not owned_locations(body) or owned_locations(base.get(tag, "")):
            return body
        if re.search(r"\bruler\s*=", strip_comments(body)):
            return body
        for match in INCLUDE_RE.finditer(strip_comments(body)):
            template = read_template(match.group(2), [MOD_TEMPLATES, BASE_TEMPLATES]) or ""
            if re.search(r"\bruler\s*=", strip_comments(template)):
                return body
        added.append(tag)
        body, count = re.subn(r"(?m)^(\t\tgovernment\s*=\s*\{)[ \t]*$", r"\1\n\t\t\truler = random", body, count=1)
        if count:
            return body
        return body.rstrip() + "\n\t\tgovernment = {\n\t\t\truler = random\n\t\t}\n\t"

    text = rewrite_countries(path.read_text(encoding="utf-8"), rewrite)
    write_text_with_retry(path, text)
    print(f"Added ruler = random to {len(added)} countries: {' '.join(sorted(added))}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        sys.exit(f"ERROR: {exc}")
