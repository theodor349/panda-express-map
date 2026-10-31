"""
strip_subject_reforms.py — remove setup entries that need a subject link or membership the mod removes.

Removes reforms from 10_countries.txt, and gives a few countries a copy of a template without the
entries that need the link. Also removes locations from pop-based countries where the location's
owner would be left with no pops.

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

# variant template: (base template, entries to leave out, countries that use it)
TEMPLATE_VARIANTS = {
    # Gafsa is no longer a Hafsid governor.
    "panda_hafsid_independent": ("hafsid_state", r"\b(?:tun_strong_familial_governors|tun_arab_bedouins)\b", {"GFS"}),
    # These two are no longer in the HRE.
    "panda_german_principality_no_hre": ("german_principality", r"\bmagdeburg_rights\b", {"ORT", "GRK"}),
    # The Hansa has no peasants once its shipwright guilds are gone, and this law needs them.
    "panda_hansa_no_education": ("hansa", r"\beducation_masses_law\s*=\s*\w+", {"HSA"}),
}
POP_COUNTRY_LOCATIONS = {"CEW": {"msinja"}, "YII": {"huichuan_dechang", "puge"}}


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove setup entries that need a link the mod removes.")
    parser.add_argument("--file", default=str(DEFAULT_FILE), help="Path to 10_countries.txt")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        sys.exit(f"ERROR: file not found: {path}")

    redirects: dict[str, tuple[str, str]] = {}
    for variant, (template, entries, tags) in TEMPLATE_VARIANTS.items():
        text = read_template(template, [BASE_TEMPLATES])
        if text is None:
            sys.exit(f"ERROR: template {template} not found in the base game")
        output = strip_patterns(text, [re.compile(entries)])
        write_bytes_with_retry(MOD_TEMPLATES / f"{variant}.txt", b"\xef\xbb\xbf" + output.encode("utf-8"))
        redirects.update({tag: (template, variant) for tag in tags})

    text = path.read_text(encoding="utf-8")
    text, removed = SUBJECT_REFORMS.subn("", text)

    redirected: set[str] = set()
    pops_removed = 0

    def rewrite(tag: str, body: str) -> str:
        nonlocal pops_removed
        if tag in redirects:
            template, variant = redirects[tag]
            body, count = re.subn(rf'include\s*=\s*"{template}"', f'include = "{variant}"', body)
            if count == 1:
                redirected.add(tag)
        if tag in POP_COUNTRY_LOCATIONS:
            names = "|".join(sorted(POP_COUNTRY_LOCATIONS[tag]))

            def strip_list(match: re.Match[str]) -> str:
                nonlocal pops_removed
                inner, count = re.subn(rf"\b(?:{names})\b", "", match.group(2))
                pops_removed += count
                return match.group(1) + inner + match.group(3)

            body = re.sub(r"(add_pops_from_locations\s*=\s*\{)([^{}]*)(\})", strip_list, body)
        return body

    text = rewrite_countries(text, rewrite)
    missing = set(redirects) - redirected
    if missing:
        sys.exit(f"ERROR: expected template includes not found on: {sorted(missing)}")
    expected_pops = sum(len(names) for names in POP_COUNTRY_LOCATIONS.values())
    if pops_removed != expected_pops:
        sys.exit(f"ERROR: expected to remove {expected_pops} pop location(s), removed {pops_removed}")

    write_text_with_retry(path, text)
    print(f"Removed {removed} subject reform(s) and {pops_removed} pop location(s); redirected {len(redirected)} include(s).")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        sys.exit(f"ERROR: {exc}")
