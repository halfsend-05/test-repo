"""Tests for file_handler: save files at and around the 64KB boundary
with both ASCII and multibyte UTF-8 content.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from file_handler import WRITE_BUFFER_SIZE, save_file, _safe_chunk_boundary


class TestSaveFileASCII:
    """ASCII-only files should save correctly at all sizes."""

    @pytest.mark.parametrize(
        "size",
        [
            WRITE_BUFFER_SIZE - 1024,   # 63KB — under boundary
            WRITE_BUFFER_SIZE,           # 64KB — exactly at boundary
            WRITE_BUFFER_SIZE + 1024,   # 65KB — over boundary
        ],
        ids=["63KB", "64KB", "65KB"],
    )
    def test_ascii_round_trip(self, size, tmp_path):
        content = "A" * size
        path = str(tmp_path / "ascii.txt")
        save_file(path, content)

        with open(path, "r", encoding="utf-8") as f:
            result = f.read()

        assert result == content


class TestSaveFileUTF8:
    """Multibyte UTF-8 files should save correctly at all sizes."""

    @pytest.mark.parametrize(
        "size",
        [
            WRITE_BUFFER_SIZE - 1024,   # under boundary
            WRITE_BUFFER_SIZE,           # at boundary
            WRITE_BUFFER_SIZE + 1024,   # over boundary
        ],
        ids=["under-64KB", "at-64KB", "over-64KB"],
    )
    def test_emoji_round_trip(self, size, tmp_path):
        # Each emoji is 4 bytes in UTF-8; fill to approximate byte size
        emoji = "\U0001F600"  # 😀
        repeat = size // len(emoji.encode("utf-8"))
        content = emoji * repeat
        path = str(tmp_path / "emoji.txt")
        save_file(path, content)

        with open(path, "r", encoding="utf-8") as f:
            result = f.read()

        assert result == content

    @pytest.mark.parametrize(
        "size",
        [
            WRITE_BUFFER_SIZE - 1024,
            WRITE_BUFFER_SIZE,
            WRITE_BUFFER_SIZE + 1024,
        ],
        ids=["under-64KB", "at-64KB", "over-64KB"],
    )
    def test_cjk_round_trip(self, size, tmp_path):
        # CJK characters are 3 bytes in UTF-8
        char = "世"  # 世
        repeat = size // len(char.encode("utf-8"))
        content = char * repeat
        path = str(tmp_path / "cjk.txt")
        save_file(path, content)

        with open(path, "r", encoding="utf-8") as f:
            result = f.read()

        assert result == content


class TestBoundaryCharSplit:
    """The 64KB byte boundary must not split a multibyte character."""

    def test_boundary_splits_multibyte_char(self, tmp_path):
        # Construct content so a multibyte character straddles the
        # exact 64KB boundary.  Fill with ASCII up to boundary - 2,
        # then add a 3-byte CJK character (bytes at positions
        # boundary-2, boundary-1, boundary).
        fill = "X" * (WRITE_BUFFER_SIZE - 2)
        content = fill + "世" + "Y" * 1024
        path = str(tmp_path / "split.txt")

        save_file(path, content)

        with open(path, "r", encoding="utf-8") as f:
            result = f.read()

        assert result == content

    def test_boundary_splits_4byte_char(self, tmp_path):
        # 4-byte emoji at offset boundary-1 straddles the boundary
        fill = "X" * (WRITE_BUFFER_SIZE - 1)
        content = fill + "\U0001F600" + "Y" * 1024
        path = str(tmp_path / "split4.txt")

        save_file(path, content)

        with open(path, "r", encoding="utf-8") as f:
            result = f.read()

        assert result == content


class TestSafeChunkBoundary:
    """Unit tests for the _safe_chunk_boundary helper."""

    def test_ascii_boundary(self):
        data = b"hello world"
        assert _safe_chunk_boundary(data, 5) == 5

    def test_continuation_byte_boundary(self):
        # 世 encodes as \xe4\xb8\x96 (3 bytes)
        data = b"AAA\xe4\xb8\x96BBB"
        # Position 4 is \xb8 (continuation byte) — should back up to 3
        assert _safe_chunk_boundary(data, 4) == 3

    def test_mid_4byte_sequence(self):
        # \U0001F600 encodes as \xf0\x9f\x98\x80
        data = b"AA\xf0\x9f\x98\x80BB"
        # Position 4 (\x98) is a continuation byte — back to 2
        assert _safe_chunk_boundary(data, 4) == 2

    def test_at_leading_byte(self):
        data = b"AA\xe4\xb8\x96"
        # Position 2 is the leading byte \xe4 — stays at 2
        assert _safe_chunk_boundary(data, 2) == 2
