import subprocess
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    load_dotenv(Path(__file__).parent.parent / ".env.local", override=True)
except ImportError:
    pass

SCRIPTS_DIR = Path(__file__).parent
CONSOLIDATE = SCRIPTS_DIR / "helpers" / "consolidate_locations.py"


def run(tag: str, *args: str) -> bool:
    cmd = [sys.executable, str(CONSOLIDATE), tag, *args]
    print(f"=== {tag}: {' '.join(args)} ===")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout, end="")
    if result.returncode != 0:
        error_line = result.stderr.strip() or result.stdout.strip().splitlines()[-1]
        print(f"  FAILED: {error_line}")
    print()
    return result.returncode == 0


def main() -> None:
    failures = []

    if not run("ARA", "--tags", "CAT"):
        failures.append("ARA --tags CAT")

    if failures:
        print("=" * 60)
        print(f"SUMMARY — {len(failures)} consolidation(s) failed:")
        for f in failures:
            print(f"  {f}")
        sys.exit(1)
    else:
        print("All misc consolidations complete.")


if __name__ == "__main__":
    main()
