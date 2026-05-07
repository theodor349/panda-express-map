"""
apply_all.py — run all apply_* scripts in order.
"""
import subprocess
import sys
from pathlib import Path

scripts_dir = Path(__file__).parent

steps = [
    "apply_no_diplomacy.py",
    "apply_promote_cores_to_countries.py",
    "apply_new_countries.py",
    "apply_consolidations.py",
]

for script in steps:
    path = scripts_dir / script
    print(f"\n=== {script} ===")
    result = subprocess.run([sys.executable, str(path)])
    if result.returncode != 0:
        print(f"FAILED: {script} exited with code {result.returncode}")
        sys.exit(result.returncode)

print("\nAll steps completed successfully.")
