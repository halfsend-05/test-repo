"""Tests for the chunked UTF-8 file save/load logic in src/file_io.py.

Covers the scenarios from issue #2053:
  - Saving a >64 KB file of emoji text succeeds (no crash).
  - Saving a >64 KB ASCII-only file succeeds (baseline).
  - A multibyte character straddling the 64 KB chunk boundary is
    handled correctly.
  - Reloaded content matches the original.
"""

import os
import sys
import tempfile

# Allow imports from the repo root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.file_io import CHUNK_SIZE, load_file, save_file


def _round_trip(content: str) -> str:
    """Save *content* to a temp file and load it back."""
    with tempfile.NamedTemporaryFile(
        suffix=".txt", delete=False
    ) as tmp:
        path = tmp.name
    try:
        save_file(path, content)
        return load_file(path)
    finally:
        os.unlink(path)


def test_large_ascii_file() -> None:
    """A >64 KB ASCII-only file saves and reloads correctly."""
    content = "A" * (CHUNK_SIZE + 1024)
    assert len(content.encode("utf-8")) > CHUNK_SIZE
    result = _round_trip(content)
    assert result == content


def test_large_emoji_file() -> None:
    """A >64 KB file of emoji text saves without crashing."""
    # Each emoji is 4 bytes in UTF-8; we need enough to exceed 64 KiB.
    emoji = "\U0001F600"  # grinning face
    count = (CHUNK_SIZE // len(emoji.encode("utf-8"))) + 256
    content = emoji * count
    assert len(content.encode("utf-8")) > CHUNK_SIZE
    result = _round_trip(content)
    assert result == content


def test_multibyte_straddles_chunk_boundary() -> None:
    """A multibyte character at the 64 KB boundary is not split."""
    # Fill up to exactly one byte before the chunk boundary with ASCII,
    # then place a 4-byte emoji right at the boundary.
    padding = "x" * (CHUNK_SIZE - 1)
    emoji = "\U0001F680"  # rocket
    content = padding + emoji + "y" * 1024
    assert len(content.encode("utf-8")) > CHUNK_SIZE
    result = _round_trip(content)
    assert result == content


def test_cjk_large_file() -> None:
    """A >64 KB file of CJK characters saves and reloads correctly."""
    # CJK characters are 3 bytes each in UTF-8.
    char = "世"  # 'world' in Chinese
    count = (CHUNK_SIZE // len(char.encode("utf-8"))) + 256
    content = char * count
    assert len(content.encode("utf-8")) > CHUNK_SIZE
    result = _round_trip(content)
    assert result == content


def test_empty_file() -> None:
    """An empty file saves and reloads correctly."""
    result = _round_trip("")
    assert result == ""


def test_small_file() -> None:
    """A small file under the chunk size works normally."""
    content = "Hello, world! \U0001F30D"
    result = _round_trip(content)
    assert result == content
