"""Tests for file_io module.

Covers saving and loading documents with various sizes and character
encodings, including the regression case for multibyte UTF-8 content
exceeding the 64KB buffer boundary.
"""

import os
import tempfile

import pytest

from src.file_io import BUFFER_SIZE, load_document, save_document


@pytest.fixture
def tmp_dir():
    """Provide a temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestSaveDocument:
    """Tests for save_document."""

    def test_save_small_ascii(self, tmp_dir):
        """Small ASCII-only document saves and round-trips correctly."""
        path = os.path.join(tmp_dir, "small.txt")
        content = "hello world"
        save_document(path, content)
        assert load_document(path) == content

    def test_save_large_ascii(self, tmp_dir):
        """ASCII document larger than 64KB saves correctly."""
        path = os.path.join(tmp_dir, "large_ascii.txt")
        content = "A" * (BUFFER_SIZE + 1024)
        save_document(path, content)
        assert load_document(path) == content

    def test_save_large_multibyte_utf8(self, tmp_dir):
        """Regression: document >64KB with multibyte UTF-8 must not crash.

        This is the primary regression test for issue #2303. The old code
        allocated a buffer based on character count instead of byte length,
        causing a buffer overflow when multibyte characters (2-4 bytes each)
        pushed the actual data past the 64KB boundary.
        """
        path = os.path.join(tmp_dir, "large_emoji.txt")
        # Each emoji is 4 bytes in UTF-8; 20000 chars = 80000 bytes > 64KB
        content = "\U0001f600" * 20000
        save_document(path, content)
        result = load_document(path)
        assert result == content
        assert len(content.encode("utf-8")) > BUFFER_SIZE

    def test_save_at_64kb_boundary_multibyte(self, tmp_dir):
        """Edge case: character count < 64K but byte count > 64K."""
        path = os.path.join(tmp_dir, "boundary.txt")
        # 3-byte CJK character U+4E16 ("世")
        # 22000 chars * 3 bytes = 66000 bytes > 64KB (65536)
        # but 22000 < 65536 so char-count allocation would under-allocate
        content = "世" * 22000
        char_count = len(content)
        byte_count = len(content.encode("utf-8"))
        assert char_count < BUFFER_SIZE
        assert byte_count > BUFFER_SIZE

        save_document(path, content)
        assert load_document(path) == content

    def test_save_mixed_ascii_and_multibyte(self, tmp_dir):
        """Mixed ASCII and multibyte content spanning the buffer boundary."""
        path = os.path.join(tmp_dir, "mixed.txt")
        ascii_part = "x" * (BUFFER_SIZE - 100)
        emoji_part = "\U0001f680" * 100  # 100 * 4 = 400 bytes
        content = ascii_part + emoji_part
        save_document(path, content)
        assert load_document(path) == content

    def test_save_creates_parent_directories(self, tmp_dir):
        """Saving to a nested path creates intermediate directories."""
        path = os.path.join(tmp_dir, "a", "b", "c", "doc.txt")
        save_document(path, "nested")
        assert load_document(path) == "nested"

    def test_save_rejects_non_string(self, tmp_dir):
        """Passing non-string content raises TypeError."""
        path = os.path.join(tmp_dir, "bad.txt")
        with pytest.raises(TypeError):
            save_document(path, 12345)

    def test_save_empty_document(self, tmp_dir):
        """Empty string saves and loads correctly."""
        path = os.path.join(tmp_dir, "empty.txt")
        save_document(path, "")
        assert load_document(path) == ""


class TestLoadDocument:
    """Tests for load_document."""

    def test_load_nonexistent_file(self, tmp_dir):
        """Loading a file that does not exist raises FileNotFoundError."""
        path = os.path.join(tmp_dir, "nope.txt")
        with pytest.raises(FileNotFoundError):
            load_document(path)
