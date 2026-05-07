"""
apply_all.py — run all apply_* scripts in order.

Before running steps:
  1. Copies required base-game files into the mod if not already present.
  2. Validates that all mod_changes/ input files exist.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    load_dotenv(Path(__file__).parent.parent / ".env.local", override=True)
except ImportError:
    pass

ROOT        = Path(os.environ.get("EU5_MOD_PATH",  Path(__file__).parent.parent))
SCRIPTS_DIR = Path(__file__).parent
BASE_GAME   = Path(os.environ.get("EU5_GAME_PATH", r"C:\Program Files (x86)\Steam\steamapps\common\Europa Universalis V\game"))

# Files to copy from base game if absent in the mod (src relative to BASE_GAME,
# dst relative to ROOT — paths are identical by convention).
BASE_GAME_COPIES = [
    "main_menu/setup/start/10_countries.txt",
    "main_menu/localization/english/country_names_l_english.yml",
]

# mod_changes/ files that must exist before any step runs.
REQUIRED_MOD_CHANGES = [
    "mod_changes/new_countries.txt",
    "mod_changes/country_consolidations.txt",
]

STEPS = [
    "apply_no_diplomacy.py",
    "apply_promote_cores_to_countries.py",
    "apply_new_countries.py",
    "apply_consolidations.py",
]


def ensure_base_game_files() -> list[str]:
    """Copy base-game files into the mod if missing. Returns list of error messages."""
    errors = []
    for rel in BASE_GAME_COPIES:
        dst = ROOT / rel
        if dst.exists():
            continue
        src = BASE_GAME / rel
        if not src.exists():
            errors.append(f"Base game file not found: {src}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"Copied from base game: {rel}")
    return errors


def check_mod_changes_inputs() -> list[str]:
    """Verify required mod_changes/ inputs exist. Returns list of error messages."""
    errors = []
    for rel in REQUIRED_MOD_CHANGES:
        path = ROOT / rel
        if not path.exists():
            errors.append(f"Missing input file: {rel}")
    return errors


def main() -> None:
    failures: list[str] = []

    print("=== Preflight ===")
    failures += ensure_base_game_files()
    failures += check_mod_changes_inputs()

    if failures:
        print("\nPreflight failed — cannot continue:")
        for msg in failures:
            print(f"  {msg}")
        sys.exit(1)

    print("Preflight OK\n")

    step_failures: list[str] = []
    for script in STEPS:
        path = SCRIPTS_DIR / script
        print(f"\n=== {script} ===")
        result = subprocess.run([sys.executable, str(path)])
        if result.returncode != 0:
            step_failures.append(f"{script} (exit {result.returncode})")

    print()
    if step_failures:
        print("SUMMARY — the following steps failed:")
        for msg in step_failures:
            print(f"  {msg}")
        sys.exit(1)
    else:
        print("All steps completed successfully.")


if __name__ == "__main__":
    main()
