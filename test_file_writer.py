"""Tests for file_writer — UTF-8-safe buffered writes."""

import os
import tempfile
import unittest

from file_writer import BUFFER_SIZE, _utf8_safe_boundary, save_file


class TestUtf8SafeBoundary(unittest.TestCase):
    """Unit tests for _utf8_safe_boundary."""

    def test_boundary_on_ascii(self):
        """A boundary that falls on an ASCII byte needs no adjustment."""
        data = b"abcdef"
        self.assertEqual(_utf8_safe_boundary(data, 3), 3)

    def test_boundary_splits_two_byte_char(self):
        """Boundary inside a 2-byte character backs up to before it."""
        # U+00E9 (é) = 0xC3 0xA9
        data = b"aaa" + "é".encode("utf-8")  # b'aaa\xc3\xa9'
        # Splitting at offset 4 lands on the continuation byte 0xA9.
        self.assertEqual(_utf8_safe_boundary(data, 4), 3)

    def test_boundary_splits_three_byte_char(self):
        """Boundary inside a 3-byte character backs up to before it."""
        # U+4E16 (世) = 0xE4 0xB8 0x96
        data = b"aaa" + "世".encode("utf-8")
        # Splitting at offset 4 or 5 should back up to 3.
        self.assertEqual(_utf8_safe_boundary(data, 4), 3)
        self.assertEqual(_utf8_safe_boundary(data, 5), 3)

    def test_boundary_splits_four_byte_char(self):
        """Boundary inside a 4-byte emoji backs up to before it."""
        # U+1F600 (😀) = 0xF0 0x9F 0x98 0x80
        data = b"aaa" + "\U0001f600".encode("utf-8")
        for split in (4, 5, 6):
            self.assertEqual(_utf8_safe_boundary(data, split), 3)

    def test_boundary_at_char_start(self):
        """Boundary exactly at the start of a multibyte char is already safe."""
        # U+1F600 starts at offset 3.
        data = b"aaa" + "\U0001f600".encode("utf-8")
        self.assertEqual(_utf8_safe_boundary(data, 3), 3)

    def test_boundary_beyond_data(self):
        """Limit past end-of-data clamps to data length."""
        data = b"hello"
        self.assertEqual(_utf8_safe_boundary(data, 100), 5)


class TestSaveFile(unittest.TestCase):
    """Integration tests for save_file."""

    def _roundtrip(self, content: str) -> str:
        """Save *content* via save_file, read it back, and return the result."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
            path = tmp.name
        try:
            save_file(path, content)
            with open(path, "r", encoding="utf-8") as fh:
                return fh.read()
        finally:
            os.unlink(path)

    def test_save_exact_64kb_ending_with_emoji(self):
        """File of exactly 64 KB ending with a 4-byte emoji saves correctly."""
        emoji = "\U0001f600"  # 😀 — 4 bytes in UTF-8
        padding = "a" * (BUFFER_SIZE - 4)
        content = padding + emoji
        self.assertEqual(len(content.encode("utf-8")), BUFFER_SIZE)
        self.assertEqual(self._roundtrip(content), content)

    def test_save_64kb_plus_one_with_multibyte_at_boundary(self):
        """File of 64 KB + 1 byte with multibyte chars at boundary saves."""
        # Place a 4-byte emoji so it straddles the 64 KB mark.
        prefix = "a" * (BUFFER_SIZE - 2)  # 65534 ASCII bytes
        emoji = "\U0001f600"  # 4 bytes — spans offsets 65534..65537
        suffix = "b"
        content = prefix + emoji + suffix
        encoded = content.encode("utf-8")
        self.assertEqual(len(encoded), BUFFER_SIZE - 2 + 4 + 1)  # 65539
        self.assertEqual(self._roundtrip(content), content)

    def test_save_70kb_mixed_ascii_and_emoji(self):
        """~70 KB file with mixed ASCII and emoji round-trips without corruption."""
        block = "Hello \U0001f30d world! "  # mix of ASCII and 4-byte emoji
        repeats = (70 * 1024) // len(block.encode("utf-8")) + 1
        content = block * repeats
        self.assertGreaterEqual(len(content.encode("utf-8")), 70 * 1024)
        self.assertEqual(self._roundtrip(content), content)

    def test_save_64kb_ascii_only(self):
        """Control case: 64 KB of pure ASCII saves without error."""
        content = "x" * BUFFER_SIZE
        self.assertEqual(self._roundtrip(content), content)

    def test_save_large_file_cjk_characters(self):
        """Large file with 3-byte CJK characters saves correctly."""
        # U+4E16 (世) = 3 bytes
        content = "世" * (BUFFER_SIZE // 3 + 1000)
        self.assertEqual(self._roundtrip(content), content)

    def test_save_empty_file(self):
        """Edge case: empty content produces an empty file."""
        self.assertEqual(self._roundtrip(""), "")


if __name__ == "__main__":
    unittest.main()
