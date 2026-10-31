"""Apply generated country capitals and government/estate presets."""

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

ROOT = Path(os.environ.get("EU5_MOD_PATH", Path(__file__).parent.parent))
HELPER = Path(__file__).parent / "helpers/sync_country_presets.py"


def main() -> None:
    print("=== Synchronizing Iberian country presets ===")
    result = subprocess.run([sys.executable, str(HELPER)])
    failures = []
    if result.returncode != 0:
        failures.append(f"sync_country_presets.py (exit {result.returncode})")

    if failures:
        print("SUMMARY — the following preset operations failed:")
        for failure in failures:
            print(f"  {failure}")
        sys.exit(1)

    print("All country presets synchronized.")


if __name__ == "__main__":
    main()
