"""Tests for file_saver module.

Covers the fix for issue #2059: saving files larger than 64KB with
UTF-8 multibyte characters must succeed without crashing.
"""

import os
import shutil
import tempfile
import unittest

from src.file_saver import save_file


class _SaveFileTestBase(unittest.TestCase):
    """Shared setup and helpers for file saver tests."""

    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def _read(self, path: str) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()


class TestSaveFileBasic(_SaveFileTestBase):
    """Basic save and roundtrip tests."""

    def test_save_and_load_ascii(self):
        path = os.path.join(self._tmp_dir, "ascii.txt")
        content = "Hello, World!"
        save_file(path, content)
        self.assertEqual(self._read(path), content)

    def test_save_and_load_empty(self):
        path = os.path.join(self._tmp_dir, "empty.txt")
        save_file(path, "")
        self.assertEqual(self._read(path), "")

    def test_save_bytes(self):
        path = os.path.join(self._tmp_dir, "bytes.txt")
        content = "Hello UTF-8"
        save_file(path, content.encode("utf-8"))
        self.assertEqual(self._read(path), content)

    def test_rejects_invalid_type(self):
        path = os.path.join(self._tmp_dir, "bad.txt")
        with self.assertRaises(TypeError):
            save_file(path, 12345)


class TestSaveLargeUTF8(_SaveFileTestBase):
    """Regression tests for issue #2059.

    The bug: saving files >64KB with multibyte UTF-8 characters caused
    a segfault because buffer allocation used character count instead
    of byte length.
    """

    def _byte_len(self, text: str) -> int:
        return len(text.encode("utf-8"))

    def test_save_70kb_emoji(self):
        """Save ~70KB of emoji text (4 bytes/char UTF-8) — must succeed."""
        path = os.path.join(self._tmp_dir, "emoji_large.txt")
        # Each emoji is 4 bytes; 18000 emojis = 72000 bytes > 64KB
        content = "\U0001f600" * 18000
        self.assertGreater(self._byte_len(content), 64 * 1024)
        save_file(path, content)
        self.assertEqual(self._read(path), content)

    def test_save_64kb_cjk(self):
        """Save 64KB of CJK characters (3 bytes/char UTF-8) — must succeed."""
        path = os.path.join(self._tmp_dir, "cjk_large.txt")
        # 22000 CJK chars × 3 bytes = 66000 bytes > 64KB
        content = "世" * 22000
        self.assertGreater(self._byte_len(content), 64 * 1024)
        save_file(path, content)
        self.assertEqual(self._read(path), content)

    def test_save_mixed_ascii_multibyte_65kb(self):
        """Save mixed ASCII + multibyte at ~65KB byte size — must succeed."""
        path = os.path.join(self._tmp_dir, "mixed_large.txt")
        # 10000 emoji (40000 bytes) + 26000 ASCII chars = 66000 bytes
        # Character count = 36000, well under 64K
        content = "\U0001f600" * 10000 + "a" * 26000
        byte_size = self._byte_len(content)
        self.assertGreater(byte_size, 64 * 1024)
        self.assertLess(len(content), 64 * 1024)  # char count under 64K
        save_file(path, content)
        self.assertEqual(self._read(path), content)

    def test_roundtrip_preserves_content_exactly(self):
        """Verify roundtrip: saved content matches original exactly."""
        path = os.path.join(self._tmp_dir, "roundtrip.txt")
        content = (
            "ASCII text\n"
            + "éàü" * 5000  # 2-byte chars
            + "世界" * 5000         # 3-byte CJK
            + "\U0001f600\U0001f4a9" * 5000  # 4-byte emoji
        )
        self.assertGreater(self._byte_len(content), 64 * 1024)
        save_file(path, content)
        self.assertEqual(self._read(path), content)

    def test_edge_char_count_under_64k_byte_count_over(self):
        """Edge case: char count < 64K but byte count > 64K."""
        path = os.path.join(self._tmp_dir, "edge.txt")
        # 16384 emoji × 4 bytes = 65536 bytes, char count = 16384
        content = "\U0001f600" * 16384
        self.assertEqual(len(content), 16384)       # char count under 64K
        self.assertEqual(self._byte_len(content), 65536)  # byte count exactly 64K
        save_file(path, content)
        self.assertEqual(self._read(path), content)

    def test_ascii_over_64kb_still_works(self):
        """Files over 64KB with only ASCII should still save fine."""
        path = os.path.join(self._tmp_dir, "ascii_large.txt")
        content = "x" * (70 * 1024)
        save_file(path, content)
        self.assertEqual(self._read(path), content)


if __name__ == "__main__":
    unittest.main()
