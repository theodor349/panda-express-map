"""
apply_strip_unownable.py — remove impassable mountains and lakes from country location blocks.

Runs after every step that assigns land, because those steps assign whole areas and provinces.
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

HELPER = Path(__file__).parent / "helpers" / "strip_unownable_locations.py"


def main() -> None:
    print("=== Stripping impassable mountains and lakes ===")
    result = subprocess.run([sys.executable, str(HELPER)])
    if result.returncode != 0:
        print("SUMMARY — strip_unownable_locations.py failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
