"""
set_country_fields.py — set capitals and ranks in 10_countries.txt.

Reads lines of `<TAG> capital <location>` and `<TAG> rank <rank>` from mod_changes/country_fields.txt,
then gives every other country with land and no capital of its own its most populated location.

Usage:
    python scripts/helpers/set_country_fields.py [--spec PATH]
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
from setup_blocks import find_block_extent, owned_locations, rewrite_countries, strip_comments

_DEFAULT_GAME_PATH = r"E:\SteamLibrary\steamapps\common\Europa Universalis V\game"
_GAME_PATH = Path(os.environ.get("EU5_GAME_PATH", _DEFAULT_GAME_PATH))
_DEFAULT_MOD_PATH = Path(__file__).parent.parent.parent
_MOD_PATH = Path(os.environ.get("EU5_MOD_PATH", _DEFAULT_MOD_PATH))
POPS_FILE = _GAME_PATH / "main_menu/setup/1337/06_pops.txt"
COUNTRIES_FILE = _MOD_PATH / "main_menu/setup/1337/10_countries.txt"
DEFAULT_SPEC = Path(__file__).parent.parent.parent / "mod_changes/country_fields.txt"


def load_spec(path: Path) -> dict[str, dict[str, str]]:
    fields: dict[str, dict[str, str]] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.partition("#")[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 3 or parts[1] not in ("capital", "rank"):
            sys.exit(f"ERROR: bad line {number} in {path.name}: {raw}")
        fields.setdefault(parts[0], {})[parts[1]] = parts[2]
    return fields


def load_populations() -> dict[str, float]:
    text = strip_comments(POPS_FILE.read_bytes().decode("utf-8-sig"))
    sizes: dict[str, float] = {}
    for match in re.finditer(r"(?m)^[ \t]*(\w+)\s*=\s*\{\s*define_pop\b", text):
        start, end = find_block_extent(text, text.index("{", match.start()))
        sizes[match.group(1)] = sum(float(size) for size in re.findall(r"\bsize\s*=\s*([\d.]+)", text[start:end]))
    return sizes


def set_field(body: str, key: str, value: str) -> str:
    pattern = rf"(?m)^\t\t{key}\s*=.*$"
    if re.search(pattern, body):
        return re.sub(pattern, f"\t\t{key} = {value}", body, count=1)
    return body.rstrip() + f"\n\t\t{key} = {value}\n\t"


def main() -> None:
    parser = argparse.ArgumentParser(description="Set capitals and ranks in 10_countries.txt.")
    parser.add_argument("--spec", default=str(DEFAULT_SPEC), help="Path to the fields file")
    args = parser.parse_args()

    for required in (Path(args.spec), POPS_FILE, COUNTRIES_FILE):
        if not required.exists():
            sys.exit(f"ERROR: file not found: {required}")

    fields = load_spec(Path(args.spec))
    populations = load_populations()
    seen: set[str] = set()
    automatic: list[str] = []

    def rewrite(tag: str, body: str) -> str:
        owned = owned_locations(body)
        wanted = fields.get(tag, {})
        if wanted:
            seen.add(tag)
        if "capital" in wanted and wanted["capital"] not in owned:
            sys.exit(f"ERROR: {tag} does not own its capital {wanted['capital']}")
        for key, value in (("capital", wanted.get("capital")), ("country_rank", wanted.get("rank"))):
            if value:
                body = set_field(body, key, value)
        current = re.search(r"(?m)^\t\tcapital\s*=\s*(\w+)", strip_comments(body))
        if owned and "capital" not in wanted and (not current or current.group(1) not in owned):
            capital = max(sorted(owned), key=lambda location: populations.get(location, 0))
            body = set_field(body, "capital", capital)
            automatic.append(f"{tag}={capital}")
        return body

    text = rewrite_countries(COUNTRIES_FILE.read_text(encoding="utf-8"), rewrite)
    missing = sorted(set(fields) - seen)
    if missing:
        sys.exit(f"ERROR: tags not found in {COUNTRIES_FILE.name}: {missing}")
    write_text_with_retry(COUNTRIES_FILE, text)
    print(f"Set fields for {len(seen)} countries and {len(automatic)} automatic capitals: {' '.join(automatic)}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        sys.exit(f"ERROR: {exc}")
