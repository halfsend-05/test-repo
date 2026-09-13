"""Tests for the UTF-8 aware buffered file writer.

Covers the four scenarios from the triage analysis plus edge cases
around the 64 KiB buffer boundary.
"""

import os
import tempfile

import pytest

# Allow running from repo root (`python -m pytest tests/`).
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from file_writer import BUFFER_SIZE, _find_safe_split, save_file


# ---------------------------------------------------------------------------
# Unit tests for _find_safe_split
# ---------------------------------------------------------------------------

class TestFindSafeSplit:
    """Verify that the split finder never breaks a multibyte sequence."""

    def test_ascii_boundary(self):
        data = b"abcdef"
        assert _find_safe_split(data, 3) == 3

    def test_split_inside_2byte_char(self):
        # U+00E9 (é) = 0xC3 0xA9
        data = b"a" * 5 + b"\xc3\xa9"
        # Limit falls on the continuation byte (index 6).
        assert _find_safe_split(data, 6) == 5

    def test_split_inside_3byte_char(self):
        # U+4E16 (世) = 0xE4 0xB8 0x96
        data = b"a" * 5 + b"\xe4\xb8\x96"
        # Limit on first continuation byte.
        assert _find_safe_split(data, 6) == 5
        # Limit on second continuation byte.
        assert _find_safe_split(data, 7) == 5

    def test_split_inside_4byte_char(self):
        # U+1F600 (😀) = 0xF0 0x9F 0x98 0x80
        data = b"a" * 5 + b"\xf0\x9f\x98\x80"
        for cut in (6, 7, 8):
            assert _find_safe_split(data, cut) == 5

    def test_split_on_char_boundary(self):
        # U+1F600 (😀) = 4 bytes, placed so the boundary falls right
        # after the character.
        data = b"a" * 5 + b"\xf0\x9f\x98\x80" + b"z"
        assert _find_safe_split(data, 9) == 9

    def test_limit_beyond_data(self):
        data = b"hello"
        assert _find_safe_split(data, 100) == 5


# ---------------------------------------------------------------------------
# Integration tests for save_file
# ---------------------------------------------------------------------------

class TestSaveFile:
    """End-to-end tests matching the triage-proposed test matrix."""

    @pytest.fixture(autouse=True)
    def _tmpdir(self, tmp_path):
        self.out = str(tmp_path / "output.bin")

    # Triage case 1: 70 KB file with emoji characters.
    def test_large_file_with_emoji(self):
        emoji = "\U0001f600"  # 😀 — 4 bytes in UTF-8
        # Build content > 70 KB with emoji sprinkled throughout.
        chunk = ("hello " + emoji + " world ") * 1000  # ~17 KB
        content = chunk * 5  # ~85 KB
        assert len(content.encode("utf-8")) > 70_000

        save_file(self.out, content)

        with open(self.out, "rb") as f:
            assert f.read() == content.encode("utf-8")

    # Triage case 2: 4-byte emoji straddles byte offset 65536.
    def test_emoji_straddles_buffer_boundary(self):
        # Place a 4-byte emoji so it starts at byte 65534, straddling
        # the 65536-byte boundary.
        prefix = "a" * 65534
        emoji = "\U0001f600"  # 4 bytes
        suffix = "b" * 100
        content = prefix + emoji + suffix

        encoded = content.encode("utf-8")
        # Confirm the emoji actually straddles the boundary.
        assert encoded[65534:65538] == b"\xf0\x9f\x98\x80"

        save_file(self.out, content)

        with open(self.out, "rb") as f:
            assert f.read() == encoded

    # Triage case 3: 70 KB ASCII-only (regression guard).
    def test_large_ascii_file(self):
        content = "A" * 72_000
        save_file(self.out, content)

        with open(self.out, "rb") as f:
            assert f.read() == content.encode("utf-8")

    # Triage case 4: exactly 64 KB of multibyte characters.
    def test_64kb_multibyte_boundary(self):
        # U+4E16 (世) is 3 bytes.  21845 * 3 = 65535, just under 64 KiB.
        content = "世" * 21846  # 65538 bytes — just over the boundary
        save_file(self.out, content)

        with open(self.out, "rb") as f:
            assert f.read() == content.encode("utf-8")

    # Additional edge case: content exactly equal to buffer size.
    def test_exact_buffer_size_ascii(self):
        content = "x" * BUFFER_SIZE
        save_file(self.out, content)

        with open(self.out, "rb") as f:
            assert f.read() == content.encode("utf-8")

    # Additional edge case: empty file.
    def test_empty_file(self):
        save_file(self.out, "")

        with open(self.out, "rb") as f:
            assert f.read() == b""

    # Additional edge case: single multibyte character.
    def test_single_multibyte_char(self):
        content = "\U0001f4a9"  # 💩 — 4 bytes
        save_file(self.out, content)

        with open(self.out, "rb") as f:
            assert f.read() == content.encode("utf-8")
