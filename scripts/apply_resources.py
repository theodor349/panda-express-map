"""
apply_resources.py — apply resource changes from mod_changes/resource_changes.txt.

Each non-blank, non-comment line has the format:
    <location_id> <resource>
"""

import os
import subprocess
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    load_dotenv(Path(__file__).parent.parent / ".env.local", override=True)
except ImportError:
    pass

ROOT       = Path(os.environ.get("EU5_MOD_PATH", Path(__file__).parent.parent))
INPUT_FILE = ROOT / "mod_changes/resource_changes.txt"
SCRIPT     = Path(__file__).parent / "helpers" / "set_resource.py"


def parse_entries(lines: list[str]) -> list[tuple[str, str]]:
    entries = []
    for line in lines:
        line = line.partition('#')[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2:
            sys.exit(f"ERROR: invalid line in {INPUT_FILE.name!r}: {line!r} (expected: <location> <resource>)")
        entries.append((parts[0], parts[1]))
    return entries


def main() -> None:
    if not INPUT_FILE.exists():
        sys.exit(f"ERROR: {INPUT_FILE} not found")

    entries = parse_entries(INPUT_FILE.read_text(encoding="utf-8").splitlines())

    if not entries:
        print("No resource changes defined.")
        return

    print(f"=== apply_resources: {len(entries)} change(s) ===\n")

    failures = []
    for location, resource in entries:
        print(f"  {location} -> {resource}")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), location, resource],
            capture_output=True, text=True,
        )
        print(result.stdout, end="")
        if result.returncode != 0:
            error = result.stderr.strip() or result.stdout.strip().splitlines()[-1]
            print(f"  FAILED: {error}")
            failures.append(f"{location} {resource}: {error}")

    if failures:
        print("\n" + "=" * 60)
        print(f"SUMMARY — {len(failures)} change(s) failed:")
        for f in failures:
            print(f"  {f}")
        sys.exit(1)
    else:
        print("\nAll resource changes applied.")


if __name__ == "__main__":
    main()
