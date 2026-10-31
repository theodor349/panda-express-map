"""
rename_base_countries.py — rename countries in the mod's localization file.

Reads lines of `<TAG> "New name"` from mod_changes/base_country_renames.txt. Used for dormant base
countries whose names would clash with mod countries.

Usage:
    python scripts/helpers/rename_base_countries.py [--spec PATH]
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

_DEFAULT_MOD_PATH = Path(__file__).parent.parent.parent
_MOD_PATH = Path(os.environ.get("EU5_MOD_PATH", _DEFAULT_MOD_PATH))
DEFAULT_SPEC = Path(__file__).parent.parent.parent / "mod_changes/base_country_renames.txt"
LOCALIZATION_FILE = _MOD_PATH / "main_menu/localization/english/country_names_l_english.yml"


def main() -> None:
    parser = argparse.ArgumentParser(description="Rename countries in the mod's localization file.")
    parser.add_argument("--spec", default=str(DEFAULT_SPEC), help="Path to the rename list")
    args = parser.parse_args()

    spec = Path(args.spec)
    for required in (spec, LOCALIZATION_FILE):
        if not required.exists():
            sys.exit(f"ERROR: file not found: {required}")

    data = LOCALIZATION_FILE.read_bytes()
    bom = b"\xef\xbb\xbf" if data.startswith(b"\xef\xbb\xbf") else b""
    text = data[len(bom):].decode("utf-8")

    renamed = 0
    for number, raw in enumerate(spec.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.partition("#")[0].strip()
        if not line:
            continue
        match = re.fullmatch(r'([A-Z0-9]{3})\s+"([^"]+)"', line)
        if not match:
            sys.exit(f"ERROR: {spec.name} line {number}: expected <TAG> \"Name\", got {line!r}")
        tag, name = match.groups()
        text, count = re.subn(rf'(?m)^( {tag}:\d*\s*)"[^"]*"', lambda m: f'{m.group(1)}"{name}"', text)
        if count != 1:
            sys.exit(f"ERROR: expected one localization line for {tag}, found {count}")
        renamed += 1

    write_bytes_with_retry(LOCALIZATION_FILE, bom + text.encode("utf-8"))
    print(f"Renamed {renamed} countries.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        sys.exit(f"ERROR: {exc}")
