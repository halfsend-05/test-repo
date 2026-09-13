"""Tests for file_saver module.

Covers the UTF-8 multibyte buffer handling fix for issue #1848:
- Files >64KB with multibyte UTF-8 characters save without error
- Boundary cases at exactly 64KB
- Mixed ASCII + multibyte content
- Saved content matches the original (no truncation or corruption)
"""

import os
import tempfile

import pytest

from file_saver import DEFAULT_BUFFER_SIZE, save_file


@pytest.fixture
def tmp_dir():
    """Provide a temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory() as d:
        yield d


def _make_path(tmp_dir: str, name: str = "output.txt") -> str:
    return os.path.join(tmp_dir, name)


class TestSaveFileUTF8:
    """Tests for saving files with multibyte UTF-8 content."""

    def test_large_multibyte_content_over_64kb(self, tmp_dir):
        """Save >64KB of multibyte UTF-8 content (emoji) without error."""
        # Each emoji is 4 bytes in UTF-8.  17000 emoji = 68KB of bytes,
        # but only 17000 characters.
        content = "\U0001F600" * 17000  # 68 000 bytes
        assert len(content.encode("utf-8")) > DEFAULT_BUFFER_SIZE

        path = _make_path(tmp_dir)
        save_file(path, content)

        with open(path, encoding="utf-8") as f:
            assert f.read() == content

    def test_exactly_64kb_multibyte(self, tmp_dir):
        """Save exactly 64KB of multibyte content (boundary case)."""
        # 16384 emoji * 4 bytes = 65536 bytes = 64KB exactly.
        content = "\U0001F600" * (DEFAULT_BUFFER_SIZE // 4)
        assert len(content.encode("utf-8")) == DEFAULT_BUFFER_SIZE

        path = _make_path(tmp_dir)
        save_file(path, content)

        with open(path, encoding="utf-8") as f:
            assert f.read() == content

    def test_char_count_under_64k_but_byte_length_over(self, tmp_dir):
        """Content where char count < 64K but byte length > 64KB."""
        # 20000 CJK characters, each 3 bytes in UTF-8 = 60000 bytes.
        # Add 2000 emoji (4 bytes each) = 8000 bytes.  Total = 68000 bytes.
        content = "世" * 20000 + "\U0001F600" * 2000
        byte_len = len(content.encode("utf-8"))
        assert len(content) < DEFAULT_BUFFER_SIZE  # char count < 64K
        assert byte_len > DEFAULT_BUFFER_SIZE       # byte length > 64KB

        path = _make_path(tmp_dir)
        save_file(path, content)

        with open(path, encoding="utf-8") as f:
            assert f.read() == content

    def test_mixed_ascii_and_multibyte_over_64kb(self, tmp_dir):
        """Save mixed ASCII + multibyte content totaling >64KB."""
        ascii_part = "Hello, world! " * 2000          # 28 000 bytes
        emoji_part = "\U0001F389\U0001F38A" * 5000     # 40 000 bytes
        content = ascii_part + emoji_part               # 68 000 bytes
        assert len(content.encode("utf-8")) > DEFAULT_BUFFER_SIZE

        path = _make_path(tmp_dir)
        save_file(path, content)

        with open(path, encoding="utf-8") as f:
            assert f.read() == content

    def test_content_integrity_no_truncation(self, tmp_dir):
        """Verify saved content matches original byte-for-byte."""
        # Build content that exercises multiple buffer chunks.
        content = ("éàü" * 8000          # 2-byte chars
                   + "世界" * 6000              # 3-byte chars
                   + "\U0001F600\U0001F680" * 4000)     # 4-byte chars
        path = _make_path(tmp_dir)
        save_file(path, content)

        with open(path, "rb") as f:
            raw = f.read()
        assert raw == content.encode("utf-8")


class TestSaveFileASCII:
    """Regression: ASCII-only saves must still work."""

    def test_large_ascii_file(self, tmp_dir):
        """Save >64KB of pure ASCII content."""
        content = "A" * (DEFAULT_BUFFER_SIZE + 1024)
        path = _make_path(tmp_dir)
        save_file(path, content)

        with open(path, encoding="utf-8") as f:
            assert f.read() == content

    def test_small_file(self, tmp_dir):
        """Save a small file (<64KB)."""
        content = "small file content"
        path = _make_path(tmp_dir)
        save_file(path, content)

        with open(path, encoding="utf-8") as f:
            assert f.read() == content

    def test_empty_file(self, tmp_dir):
        """Save an empty file."""
        path = _make_path(tmp_dir)
        save_file(path, "")

        with open(path, encoding="utf-8") as f:
            assert f.read() == ""
