"""
setup_blocks.py — shared parsing for setup files, imported by the startup fix helpers.

Usage:
    from setup_blocks import rewrite_countries, owned_locations
"""

import re
import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).parent))
from set_country_ruler import find_block_extent

COUNTRY_RE = re.compile(r"^\t([A-Za-z0-9_]{3})\s*=\s*\{", re.MULTILINE)
INCLUDE_RE = re.compile(r'^([ \t]*include\s*=\s*)"?(\w+)"?', re.MULTILINE)


def strip_comments(text: str) -> str:
    return re.sub(r"#[^\n]*", "", text)


def country_extents(text: str) -> dict[str, tuple[int, int]]:
    """Return {tag: (open_brace, close_brace)} for every country block, in file order."""
    extents: dict[str, tuple[int, int]] = {}
    for match in COUNTRY_RE.finditer(text):
        extents[match.group(1)] = find_block_extent(text, match.end() - 1)
    return extents


def country_bodies(text: str) -> dict[str, str]:
    return {tag: text[start + 1:end] for tag, (start, end) in country_extents(text).items()}


def rewrite_countries(text: str, rewrite: Callable[[str, str], str]) -> str:
    """Apply rewrite(tag, body) to every country block."""
    parts: list[str] = []
    cursor = 0
    for tag, (start, end) in country_extents(text).items():
        parts.append(text[cursor:start + 1])
        parts.append(rewrite(tag, text[start + 1:end]))
        cursor = end
    parts.append(text[cursor:])
    return "".join(parts)


def _locations(body: str, key_pattern: str) -> set[str]:
    found: set[str] = set()
    # Base files are not consistently indented, so don't rely on the tab depth.
    for match in re.finditer(rf"(?m)^[ \t]*({key_pattern})\s*=\s*\{{([^{{}}]*)\}}", strip_comments(body)):
        found.update(match.group(2).split())
    return found


def owned_locations(body: str) -> set[str]:
    return _locations(body, r"own_\w+")


def core_locations(body: str) -> set[str]:
    return _locations(body, r"our_cores_conquered_by_others")


def country_type(body: str) -> str | None:
    match = re.search(r"(?m)^\t\ttype\s*=\s*(\w+)", strip_comments(body))
    return match.group(1) if match else None


def strip_patterns(text: str, patterns: list[re.Pattern[str]]) -> str:
    """Remove pattern matches outside comments, dropping lines left with nothing on them."""
    lines: list[str] = []
    for line in text.split("\n"):
        code, hash_mark, comment = line.partition("#")
        stripped = code
        for pattern in patterns:
            stripped = pattern.sub("", stripped)
        if stripped == code:
            lines.append(line)
        elif stripped.strip() or hash_mark:
            lines.append(stripped.rstrip() + (" " + hash_mark + comment if stripped.strip() and hash_mark else hash_mark + comment))
    return "\n".join(lines)


def read_template(name: str, directories: list[Path]) -> str | None:
    """Return a setup template's text from the first directory that has it."""
    for directory in directories:
        path = directory / f"{name}.txt"
        if path.exists():
            return path.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")
    return None
