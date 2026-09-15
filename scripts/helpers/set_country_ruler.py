"""
set_country_ruler.py -- change a country's active ruler in 10_countries.txt.

Usage:
    python set_country_ruler.py NRM random
    python set_country_ruler.py FRA fra_philip_vi_valois --file path/to/10_countries.txt
    python set_country_ruler.py PRO random --clear-family
"""

import argparse
import os
import re
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
    load_dotenv(Path(__file__).parent.parent.parent / ".env.local", override=True)
except ImportError:
    pass

_DEFAULT_GAME_PATH = r"E:\SteamLibrary\steamapps\common\Europa Universalis V\game"
GAME_PATH = Path(os.environ.get("EU5_GAME_PATH", _DEFAULT_GAME_PATH))
_DEFAULT_MOD_PATH = Path(__file__).parent.parent.parent
MOD_PATH = Path(os.environ.get("EU5_MOD_PATH", _DEFAULT_MOD_PATH))
DEFAULT_COUNTRIES_FILE = MOD_PATH / "main_menu" / "setup" / "start" / "10_countries.txt"

_TAG_RE = re.compile(r"^[A-Z0-9]{3}$")
_RULER_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Set a country's active ruler in 10_countries.txt."
    )
    parser.add_argument("tag", help="Country tag (for example, NRM)")
    parser.add_argument("ruler", help="Character ID or 'random'")
    parser.add_argument(
        "--file",
        default=str(DEFAULT_COUNTRIES_FILE),
        help="Path to 10_countries.txt",
    )
    parser.add_argument(
        "--clear-family",
        action="store_true",
        help="Remove direct heir and consort assignments from the government block",
    )
    return parser.parse_args()


def _code_before_comment(line: str) -> str:
    """Return line content before an unquoted # comment."""
    in_quote = False
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            escaped = False
        elif char == "\\" and in_quote:
            escaped = True
        elif char == '"':
            in_quote = not in_quote
        elif char == "#" and not in_quote:
            return line[:index]
    return line


def find_block_extent(text: str, open_brace: int) -> tuple[int, int]:
    """Return the opening and closing brace offsets, ignoring comments/strings."""
    depth = 0
    in_quote = False
    in_comment = False
    escaped = False

    for index in range(open_brace, len(text)):
        char = text[index]
        if in_comment:
            if char == "\n":
                in_comment = False
            continue
        if escaped:
            escaped = False
            continue
        if char == "\\" and in_quote:
            escaped = True
            continue
        if char == '"':
            in_quote = not in_quote
            continue
        if char == "#" and not in_quote:
            in_comment = True
            continue
        if in_quote:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return open_brace, index

    raise ValueError(f"unmatched brace at offset {open_brace}")


def find_named_block(
    text: str, name: str, search_start: int, search_end: int
) -> tuple[int, int] | None:
    pattern = re.compile(
        r"^[ \t]*" + re.escape(name) + r"\s*=\s*\{",
        re.MULTILINE,
    )
    match = pattern.search(text, search_start, search_end)
    if not match:
        return None
    open_brace = text.index("{", match.start(), match.end())
    block = find_block_extent(text, open_brace)
    if block[1] > search_end:
        return None
    return block


def find_active_ruler_line(
    text: str, government_open: int, government_close: int
) -> tuple[int, int, re.Match[str]]:
    """Find the sole direct ruler assignment inside a government block."""
    line_re = re.compile(
        r"^(?P<prefix>[ \t]*ruler\s*=\s*)"
        r"(?P<ruler>[A-Za-z0-9_.:-]+)"
        r"(?P<suffix>[ \t]*(?:#.*)?)$"
    )
    matches: list[tuple[int, int, re.Match[str]]] = []
    depth = 0
    cursor = government_open + 1

    while cursor < government_close:
        newline = text.find("\n", cursor, government_close)
        line_end = government_close if newline == -1 else newline
        line = text[cursor:line_end].rstrip("\r")

        if depth == 0:
            match = line_re.match(line)
            if match:
                matches.append((cursor, line_end, match))

        code = _code_before_comment(line)
        code = re.sub(r'"(?:\\.|[^"\\])*"', "", code)
        depth += code.count("{") - code.count("}")
        cursor = line_end + (1 if newline != -1 else 0)

    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one active ruler assignment; found {len(matches)}"
        )
    return matches[0]


def find_direct_family_lines(
    text: str, government_open: int, government_close: int
) -> list[tuple[int, int, str]]:
    """Find direct heir and consort assignment lines, ignoring nested blocks."""
    line_re = re.compile(
        r"^[ \t]*(heir|consort)\s*=\s*[A-Za-z0-9_.:-]+[ \t]*(?:#.*)?$"
    )
    matches: list[tuple[int, int, str]] = []
    depth = 0
    cursor = government_open + 1

    while cursor < government_close:
        newline = text.find("\n", cursor, government_close)
        line_end = government_close if newline == -1 else newline
        line = text[cursor:line_end].rstrip("\r")
        match = line_re.match(line) if depth == 0 else None
        if match:
            matches.append((cursor, line_end + (newline != -1), match.group(1)))

        code = _code_before_comment(line)
        code = re.sub(r'"(?:\\.|[^"\\])*"', "", code)
        depth += code.count("{") - code.count("}")
        cursor = line_end + (1 if newline != -1 else 0)

    return matches


def set_country_ruler(
    path: Path, tag: str, ruler: str, clear_family: bool = False
) -> None:
    if not path.exists():
        sys.exit(f"ERROR: file not found: {path}")

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        sys.exit(f"ERROR: could not read {path}: {exc}")

    try:
        country = find_named_block(text, tag, 0, len(text))
    except ValueError as exc:
        sys.exit(f"ERROR: malformed country block for '{tag}': {exc}")
    if country is None:
        sys.exit(f"ERROR: country tag '{tag}' not found in {path.name}")

    try:
        government = find_named_block(
            text, "government", country[0] + 1, country[1]
        )
    except ValueError as exc:
        sys.exit(f"ERROR: malformed government block for '{tag}': {exc}")
    if government is None:
        sys.exit(f"ERROR: government block not found for '{tag}' in {path.name}")

    try:
        line_start, line_end, match = find_active_ruler_line(text, *government)
    except ValueError as exc:
        sys.exit(f"ERROR: {tag}: {exc}")

    old_ruler = match.group("ruler")
    replacement = f'{match.group("prefix")}{ruler}{match.group("suffix")}'
    updated = text[:line_start] + replacement + text[line_end:]
    cleared: list[str] = []
    if clear_family:
        try:
            updated_country = find_named_block(updated, tag, 0, len(updated))
        except ValueError as exc:
            sys.exit(f"ERROR: malformed country block for '{tag}' after ruler edit: {exc}")
        if updated_country is None:
            sys.exit(f"ERROR: country tag '{tag}' disappeared after ruler edit")
        try:
            updated_government = find_named_block(
                updated, "government", updated_country[0] + 1, updated_country[1]
            )
        except ValueError as exc:
            sys.exit(f"ERROR: malformed government block for '{tag}' after ruler edit: {exc}")
        if updated_government is None:
            sys.exit(f"ERROR: government block for '{tag}' disappeared after ruler edit")
        family_lines = find_direct_family_lines(updated, *updated_government)
        for start, end, field in reversed(family_lines):
            updated = updated[:start] + updated[end:]
            cleared.append(field)

    if updated == text:
        print(f"[{tag}] ruler already set to {ruler} -- unchanged.")
        return

    try:
        path.write_text(updated, encoding="utf-8")
    except OSError as exc:
        sys.exit(f"ERROR: could not write {path}: {exc}")
    if old_ruler != ruler:
        print(f"[{tag}] ruler: {old_ruler} -> {ruler}")
    if cleared:
        print(f"[{tag}] cleared: {', '.join(sorted(cleared))}")


def main() -> None:
    args = parse_args()
    tag = args.tag.upper()
    ruler = args.ruler

    if not _TAG_RE.fullmatch(tag):
        sys.exit(f"ERROR: invalid country tag: {args.tag!r}")
    if not _RULER_RE.fullmatch(ruler):
        sys.exit(f"ERROR: invalid ruler value: {ruler!r}")

    set_country_ruler(Path(args.file), tag, ruler, args.clear_family)


if __name__ == "__main__":
    main()
