"""
run_consolidations.py — batch-run consolidate_locations.py from country_consolidations.txt.

Each line in country_consolidations.txt has the format:
    TAG --areas <a> ... --provinces <p> ... --locations <l> ...
Lines starting with # or blank are ignored.
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

SCRIPTS_DIR = Path(__file__).parent
CONSOLIDATE = SCRIPTS_DIR / "helpers" / "consolidate_locations.py"
CONSOLIDATIONS_FILE = SCRIPTS_DIR.parent / "mod_changes" / "country_consolidations.txt"


def main() -> None:
    lines = CONSOLIDATIONS_FILE.read_text(encoding="utf-8").splitlines()

    entries = [l.partition("#")[0].strip() for l in lines if l.strip() and not l.strip().startswith("#")]
    entries = [e for e in entries if e]

    if not entries:
        print("No consolidation entries found.")
        return

    print(f"Running {len(entries)} consolidation(s)...\n")

    failures: list[str] = []

    for entry in entries:
        parts = entry.split()
        tag = parts[0]
        args = parts[1:]
        cmd = [sys.executable, str(CONSOLIDATE), tag] + args
        print(f"=== {tag}: {' '.join(args)} ===")
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout, end="")
        if result.returncode != 0:
            error_line = result.stderr.strip() or result.stdout.strip().splitlines()[-1]
            failures.append(f"  {tag}: {error_line}")
            print(f"  FAILED: {error_line}")
        print()

    if failures:
        print("=" * 60)
        print(f"SUMMARY — {len(failures)} consolidation(s) failed:")
        for f in failures:
            print(f)
        sys.exit(1)
    else:
        print("All consolidations complete.")


if __name__ == "__main__":
    main()
