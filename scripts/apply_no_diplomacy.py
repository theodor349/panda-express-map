import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    load_dotenv(Path(__file__).parent.parent / ".env.local", override=True)
except ImportError:
    pass

ROOT = Path(os.environ.get("EU5_MOD_PATH", Path(__file__).parent.parent))
DIPLOMACY_PATH = ROOT / "main_menu" / "setup" / "start" / "12_diplomacy.txt"


def main() -> None:
    DIPLOMACY_PATH.parent.mkdir(parents=True, exist_ok=True)
    DIPLOMACY_PATH.write_text("diplomacy_manager = {\n\n}\n", encoding="utf-8")
    print(f"Written: {DIPLOMACY_PATH}")


if __name__ == "__main__":
    main()
