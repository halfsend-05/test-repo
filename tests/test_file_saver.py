"""Tests for file_saver module.

Covers the fix for issue #2059: saving files larger than 64KB with
UTF-8 multibyte characters must succeed without crashing.
"""

import os
import tempfile

import pytest

from src.file_saver import save_file, load_file, _byte_length


@pytest.fixture
def tmp_dir():
    """Provide a temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestByteLength:
    """Verify _byte_length correctly computes UTF-8 byte sizes."""

    def test_ascii(self):
        assert _byte_length("hello") == 5

    def test_emoji(self):
        # Each emoji is 4 bytes in UTF-8.
        assert _byte_length("\U0001f600") == 4

    def test_cjk(self):
        # CJK characters are 3 bytes in UTF-8.
        assert _byte_length("世") == 3

    def test_bytes_input(self):
        assert _byte_length(b"hello") == 5

    def test_empty(self):
        assert _byte_length("") == 0


class TestSaveFileBasic:
    """Basic save and roundtrip tests."""

    def test_save_and_load_ascii(self, tmp_dir):
        path = os.path.join(tmp_dir, "ascii.txt")
        content = "Hello, World!"
        save_file(path, content)
        assert load_file(path) == content

    def test_save_and_load_empty(self, tmp_dir):
        path = os.path.join(tmp_dir, "empty.txt")
        save_file(path, "")
        assert load_file(path) == ""

    def test_save_bytes(self, tmp_dir):
        path = os.path.join(tmp_dir, "bytes.txt")
        content = "Hello UTF-8"
        save_file(path, content.encode("utf-8"))
        assert load_file(path) == content

    def test_rejects_invalid_type(self, tmp_dir):
        path = os.path.join(tmp_dir, "bad.txt")
        with pytest.raises(TypeError):
            save_file(path, 12345)


class TestSaveLargeUTF8:
    """Regression tests for issue #2059.

    The bug: saving files >64KB with multibyte UTF-8 characters caused
    a segfault because buffer allocation used character count instead
    of byte length.
    """

    def test_save_70kb_emoji(self, tmp_dir):
        """Save ~70KB of emoji text (4 bytes/char UTF-8) — must succeed."""
        path = os.path.join(tmp_dir, "emoji_large.txt")
        # Each emoji is 4 bytes; 18000 emojis = 72000 bytes > 64KB
        content = "\U0001f600" * 18000
        assert _byte_length(content) > 64 * 1024
        save_file(path, content)
        assert load_file(path) == content

    def test_save_64kb_cjk(self, tmp_dir):
        """Save 64KB of CJK characters (3 bytes/char UTF-8) — must succeed."""
        path = os.path.join(tmp_dir, "cjk_large.txt")
        # 22000 CJK chars × 3 bytes = 66000 bytes > 64KB
        content = "世" * 22000
        assert _byte_length(content) > 64 * 1024
        save_file(path, content)
        assert load_file(path) == content

    def test_save_mixed_ascii_multibyte_65kb(self, tmp_dir):
        """Save mixed ASCII + multibyte at ~65KB byte size — must succeed."""
        path = os.path.join(tmp_dir, "mixed_large.txt")
        # Build content where char count < 64K but byte count > 64K
        # 10000 emoji (40000 bytes) + 26000 ASCII chars (26000 bytes) = 66000 bytes
        # Character count = 36000, well under 64K
        content = "\U0001f600" * 10000 + "a" * 26000
        byte_size = _byte_length(content)
        assert byte_size > 64 * 1024
        assert len(content) < 64 * 1024  # char count under 64K
        save_file(path, content)
        assert load_file(path) == content

    def test_roundtrip_preserves_content_exactly(self, tmp_dir):
        """Verify roundtrip: saved content matches original exactly."""
        path = os.path.join(tmp_dir, "roundtrip.txt")
        # Mix of different multibyte character widths
        content = (
            "ASCII text\n"
            + "éàü" * 5000  # 2-byte chars
            + "世界" * 5000         # 3-byte CJK
            + "\U0001f600\U0001f4a9" * 5000  # 4-byte emoji
        )
        assert _byte_length(content) > 64 * 1024
        save_file(path, content)
        result = load_file(path)
        assert result == content

    def test_edge_char_count_under_64k_byte_count_over(self, tmp_dir):
        """Edge case: char count < 64K but byte count > 64K."""
        path = os.path.join(tmp_dir, "edge.txt")
        # 16384 emoji × 4 bytes = 65536 bytes, char count = 16384
        content = "\U0001f600" * 16384
        assert len(content) == 16384       # char count under 64K
        assert _byte_length(content) == 65536  # byte count exactly 64K
        save_file(path, content)
        assert load_file(path) == content

    def test_ascii_over_64kb_still_works(self, tmp_dir):
        """Files over 64KB with only ASCII should still save fine."""
        path = os.path.join(tmp_dir, "ascii_large.txt")
        content = "x" * (70 * 1024)
        save_file(path, content)
        assert load_file(path) == content
