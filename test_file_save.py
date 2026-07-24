"""Tests for the file_save module.

Covers saving files at and beyond the 64KB boundary with ASCII,
multibyte UTF-8, and mixed content to prevent regression of the
segfault described in issue #1167.
"""

import os
import tempfile

from file_save import CHUNK_SIZE, save_file


def _round_trip(content: str) -> str:
    """Save *content* to a temp file and read it back."""
    fd, path = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    try:
        save_file(path, content)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    finally:
        os.unlink(path)


def test_ascii_under_chunk_size():
    """ASCII content smaller than one chunk saves correctly."""
    content = "a" * (CHUNK_SIZE - 1)
    assert _round_trip(content) == content


def test_ascii_over_chunk_size():
    """ASCII content larger than one chunk saves correctly."""
    content = "a" * (CHUNK_SIZE + 100)
    assert _round_trip(content) == content


def test_multibyte_utf8_under_chunk_size():
    """Multibyte UTF-8 content under 64KB saves correctly."""
    # Each emoji is 4 bytes; 10 000 emojis = 40 000 bytes < 64KB
    content = "\U0001f600" * 10_000
    assert _round_trip(content) == content


def test_multibyte_utf8_over_chunk_size():
    """Multibyte UTF-8 content over 64KB saves correctly (issue #1167)."""
    # 20 000 emojis * 4 bytes = 80 000 bytes > 64KB
    content = "\U0001f600" * 20_000
    assert _round_trip(content) == content


def test_mixed_content_over_chunk_size():
    """Mixed ASCII + CJK text over 64KB saves correctly."""
    # Build ~70KB of mixed content
    unit = "Hello 世界 "  # 12 bytes in UTF-8
    repeats = (70_000 // len(unit.encode("utf-8"))) + 1
    content = unit * repeats
    assert _round_trip(content) == content


def test_boundary_last_char_is_multibyte():
    """A 4-byte character straddling the 64KB boundary saves correctly."""
    # Fill up to exactly CHUNK_SIZE - 1 bytes with ASCII, then add a
    # 4-byte emoji so the sequence crosses the boundary.
    padding = "x" * (CHUNK_SIZE - 1)
    content = padding + "\U0001f680"  # rocket emoji, 4 bytes
    assert _round_trip(content) == content


def test_empty_file():
    """An empty string saves as an empty file."""
    assert _round_trip("") == ""


def test_exact_chunk_size_ascii():
    """A file whose byte length is exactly CHUNK_SIZE saves correctly."""
    content = "b" * CHUNK_SIZE
    assert _round_trip(content) == content


def test_large_multibyte_128kb():
    """128KB of mixed ASCII and multibyte chars saves correctly."""
    # Build ~128KB of mixed content
    unit = "abc\U0001f4a5defé"  # mix of 1, 2, and 4-byte chars
    target_bytes = 128 * 1024
    repeats = (target_bytes // len(unit.encode("utf-8"))) + 1
    content = unit * repeats
    assert _round_trip(content) == content
