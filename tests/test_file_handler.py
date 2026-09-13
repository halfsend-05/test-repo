"""Tests for the file handler module.

Covers the UTF-8 multibyte buffer-overflow bug reported in issue #1711:
files larger than 64KB containing multibyte characters must save without
error and round-trip their content intact.
"""

import os
import tempfile

import pytest

from src.file_handler import BUFFER_SIZE, _calculate_byte_length, save_file


class TestCalculateByteLength:
    """Tests for _calculate_byte_length helper."""

    def test_ascii_string(self):
        assert _calculate_byte_length("hello") == 5

    def test_emoji_string(self):
        # Each emoji is 4 bytes in UTF-8.
        emoji = "\U0001f600"  # grinning face
        assert _calculate_byte_length(emoji) == 4

    def test_cjk_string(self):
        # CJK characters are 3 bytes each in UTF-8.
        cjk = "世界"  # "world" in Chinese
        assert _calculate_byte_length(cjk) == 6

    def test_bytes_input(self):
        data = b"hello"
        assert _calculate_byte_length(data) == 5

    def test_empty_string(self):
        assert _calculate_byte_length("") == 0

    def test_mixed_ascii_and_multibyte(self):
        # "hi" (2 bytes) + emoji (4 bytes)
        mixed = "hi\U0001f600"
        assert _calculate_byte_length(mixed) == 6


class TestSaveFile:
    """Tests for save_file, focusing on the 64KB multibyte boundary."""

    def _round_trip(self, content):
        """Save content to a temp file, read it back, and return it."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            save_file(path, content)
            with open(path, "rb") as f:
                return f.read().decode("utf-8")
        finally:
            os.unlink(path)

    def test_small_ascii_file(self):
        content = "hello world"
        assert self._round_trip(content) == content

    def test_small_multibyte_file(self):
        content = "\U0001f600" * 100  # 400 bytes of emoji
        assert self._round_trip(content) == content

    def test_large_ascii_file_over_64kb(self):
        # 70KB of ASCII — one byte per char.
        content = "A" * (70 * 1024)
        assert self._round_trip(content) == content

    def test_large_multibyte_file_over_64kb(self):
        """Regression test for issue #1711.

        ~70KB of emoji text must save without crashing.
        Each emoji is 4 bytes, so 17920 emojis = 71680 bytes > 64KB.
        """
        content = "\U0001f600" * 17920  # 71680 bytes
        result = self._round_trip(content)
        assert result == content

    def test_exact_64kb_with_trailing_multibyte(self):
        """Edge case: file exactly at 64KB with a trailing multibyte char
        that spans the buffer boundary.
        """
        # Fill up to 64KB - 1 byte with ASCII, then add a 4-byte emoji.
        ascii_part = "A" * (BUFFER_SIZE - 1)
        content = ascii_part + "\U0001f600"
        result = self._round_trip(content)
        assert result == content

    def test_mixed_ascii_and_multibyte_over_64kb(self):
        """Mixed content crossing the 64KB boundary."""
        # Alternate ASCII and emoji to cross the boundary.
        unit = "hello\U0001f600"  # 5 + 4 = 9 bytes per unit
        repeat_count = (70 * 1024) // 9 + 1
        content = unit * repeat_count
        result = self._round_trip(content)
        assert result == content

    def test_entirely_4byte_emoji_at_64kb(self):
        """File composed entirely of 4-byte emoji chars = 64KB exactly."""
        # 64KB / 4 bytes = 16384 emoji characters.
        content = "\U0001f600" * (BUFFER_SIZE // 4)
        result = self._round_trip(content)
        assert result == content

    def test_cjk_content_over_64kb(self):
        """CJK (3-byte) characters exceeding 64KB."""
        # 70KB / 3 bytes per char ~ 23894 chars.
        content = "世" * 23894
        result = self._round_trip(content)
        assert result == content

    def test_bytes_input(self):
        content = "hello \U0001f600"
        encoded = content.encode("utf-8")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            save_file(path, encoded)
            with open(path, "rb") as f:
                assert f.read() == encoded
        finally:
            os.unlink(path)

    def test_invalid_content_type(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            with pytest.raises(TypeError):
                save_file(path, 12345)
        finally:
            os.unlink(path)

    def test_empty_content(self):
        result = self._round_trip("")
        assert result == ""
