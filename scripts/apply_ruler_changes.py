"""
apply_ruler_changes.py -- apply ruler changes from mod_changes/ruler_changes.txt.

Each non-blank, non-comment line has the format:
    <country_tag> <ruler_character_or_random>
"""

import os
import re
import subprocess
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    load_dotenv(Path(__file__).parent.parent / ".env.local", override=True)
except ImportError:
    pass

ROOT = Path(os.environ.get("EU5_MOD_PATH", Path(__file__).parent.parent))
INPUT_FILE = ROOT / "mod_changes" / "ruler_changes.txt"
COUNTRIES_FILE = ROOT / "main_menu" / "setup" / "start" / "10_countries.txt"
HELPER = Path(__file__).parent / "helpers" / "set_country_ruler.py"

_TAG_RE = re.compile(r"^[A-Z0-9]{3}$")
_RULER_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")


def parse_entries(lines: list[str]) -> tuple[list[tuple[str, str]], list[str]]:
    entries: list[tuple[str, str]] = []
    errors: list[str] = []
    seen_tags: set[str] = set()

    for line_number, raw_line in enumerate(lines, 1):
        line = raw_line.partition("#")[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2:
            errors.append(
                f"line {line_number}: expected '<country_tag> <ruler>', got {line!r}"
            )
            continue

        tag, ruler = parts[0].upper(), parts[1]
        if not _TAG_RE.fullmatch(tag):
            errors.append(f"line {line_number}: invalid country tag {parts[0]!r}")
            continue
        if not _RULER_RE.fullmatch(ruler):
            errors.append(f"line {line_number}: invalid ruler value {ruler!r}")
            continue
        if tag in seen_tags:
            errors.append(f"line {line_number}: duplicate country tag {tag!r}")
            continue

        seen_tags.add(tag)
        entries.append((tag, ruler))

    return entries, errors


def print_failure_summary(failures: list[str]) -> None:
    print("\nSUMMARY -- ruler changes failed:")
    for failure in failures:
        print(f"  {failure}")


def main() -> None:
    preflight_failures: list[str] = []
    if not INPUT_FILE.exists():
        preflight_failures.append(f"input file not found: {INPUT_FILE}")
    if not COUNTRIES_FILE.exists():
        preflight_failures.append(f"countries file not found: {COUNTRIES_FILE}")
    if not HELPER.exists():
        preflight_failures.append(f"helper script not found: {HELPER}")
    if preflight_failures:
        print_failure_summary(preflight_failures)
        sys.exit(1)

    try:
        input_lines = INPUT_FILE.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        print_failure_summary([f"could not read {INPUT_FILE}: {exc}"])
        sys.exit(1)

    entries, parse_errors = parse_entries(input_lines)
    if parse_errors:
        print_failure_summary(parse_errors)
        sys.exit(1)

    print(f"=== Ruler changes: {len(entries)} change(s) ===")
    if not entries:
        print("No ruler changes defined.")
        return

    failures: list[str] = []
    for tag, ruler in entries:
        print(f"=== {tag}: {ruler} ===")
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(HELPER),
                    tag,
                    ruler,
                    "--file",
                    str(COUNTRIES_FILE),
                ],
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            error = f"could not launch helper: {exc}"
            print(f"FAILED: {error}")
            failures.append(f"{tag} {ruler}: {error}")
            continue
        print(result.stdout, end="")
        if result.returncode != 0:
            error = result.stderr.strip() or "helper exited without an error message"
            print(f"FAILED: {error}")
            failures.append(f"{tag} {ruler}: {error}")

    if failures:
        print_failure_summary(failures)
        sys.exit(1)

    print("All ruler changes applied.")


if __name__ == "__main__":
    main()
