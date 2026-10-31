"""
apply_startup_fixes.py — clear errors the game logs at start because of the mod's map changes.

Runs last, because these helpers depend on the final land assignments.
"""
import subprocess
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    load_dotenv(Path(__file__).parent.parent / ".env.local", override=True)
except ImportError:
    pass

HELPERS_DIR = Path(__file__).parent / "helpers"
HELPERS = [
    "strip_subject_reforms.py",
    "strip_lost_cores.py",
    "sanitize_landless_countries.py",
    "ensure_random_rulers.py",
    "set_country_fields.py",
    "build_international_organizations.py",
    "build_wars.py",
    "build_cities_and_buildings.py",
    "build_country_definitions.py",
]


def main() -> None:
    failures: list[str] = []
    for helper in HELPERS:
        print(f"=== {helper} ===")
        result = subprocess.run([sys.executable, str(HELPERS_DIR / helper)])
        if result.returncode != 0:
            failures.append(f"{helper} (exit {result.returncode})")

    if failures:
        print("\nSUMMARY — the following helpers failed:")
        for failure in failures:
            print(f"  {failure}")
        sys.exit(1)


if __name__ == "__main__":
    main()
