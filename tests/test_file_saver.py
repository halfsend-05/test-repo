"""Tests for the file-saving module.

Covers the regression where multibyte UTF-8 content larger than the
64 KiB default buffer caused a buffer overflow / segfault (issue #1863).
"""

import os
import tempfile

from src.file_saver import BUFFER_SIZE, _allocate_buffer, _encode_content, save_file


# ---------------------------------------------------------------------------
# Unit tests — encoding and buffer allocation
# ---------------------------------------------------------------------------


class TestEncodeContent:
    def test_ascii_byte_length_equals_char_count(self):
        text = "hello"
        assert len(_encode_content(text)) == len(text)

    def test_multibyte_byte_length_exceeds_char_count(self):
        text = "\U0001f600"  # 😀 — 4 bytes in UTF-8
        encoded = _encode_content(text)
        assert len(encoded) == 4
        assert len(encoded) > len(text)


class TestAllocateBuffer:
    def test_small_content_uses_default_buffer(self):
        data = b"small"
        buf = _allocate_buffer(data)
        assert len(buf) == BUFFER_SIZE

    def test_large_content_grows_buffer(self):
        data = b"x" * (BUFFER_SIZE + 1)
        buf = _allocate_buffer(data)
        assert len(buf) == BUFFER_SIZE + 1

    def test_exact_boundary(self):
        data = b"x" * BUFFER_SIZE
        buf = _allocate_buffer(data)
        assert len(buf) == BUFFER_SIZE


# ---------------------------------------------------------------------------
# Integration tests — save_file round-trip
# ---------------------------------------------------------------------------


class TestSaveFile:
    def test_ascii_small_file(self, tmp_path):
        path = str(tmp_path / "ascii_small.txt")
        text = "Hello, world!"
        written = save_file(path, text)
        assert written == len(text.encode("utf-8"))
        assert open(path, "rb").read() == text.encode("utf-8")

    def test_multibyte_small_file(self, tmp_path):
        path = str(tmp_path / "multibyte_small.txt")
        text = "Hello 😀🎉🚀"
        written = save_file(path, text)
        expected = text.encode("utf-8")
        assert written == len(expected)
        assert open(path, "rb").read() == expected

    def test_large_ascii_file(self, tmp_path):
        """Files >64 KiB with ASCII only should save correctly."""
        path = str(tmp_path / "large_ascii.txt")
        text = "A" * (BUFFER_SIZE + 1024)
        written = save_file(path, text)
        expected = text.encode("utf-8")
        assert written == len(expected)
        assert open(path, "rb").read() == expected

    def test_large_multibyte_file(self, tmp_path):
        """Regression: files >64 KiB with multibyte chars must not crash."""
        path = str(tmp_path / "large_multibyte.txt")
        # Each emoji is 4 bytes; ~18k emojis → ~72 KiB > 64 KiB
        emoji_count = (BUFFER_SIZE // 4) + 256
        text = "\U0001f600" * emoji_count
        written = save_file(path, text)
        expected = text.encode("utf-8")
        assert written == len(expected)
        assert open(path, "rb").read() == expected

    def test_exact_64kb_boundary_with_multibyte(self, tmp_path):
        """Edge case: multibyte content whose byte length is exactly 64 KiB."""
        path = str(tmp_path / "exact_boundary.txt")
        # 4-byte emoji; need BUFFER_SIZE / 4 of them for exactly 64 KiB
        text = "\U0001f600" * (BUFFER_SIZE // 4)
        assert len(text.encode("utf-8")) == BUFFER_SIZE
        written = save_file(path, text)
        assert written == BUFFER_SIZE
        assert open(path, "rb").read() == text.encode("utf-8")

    def test_mixed_ascii_and_multibyte_at_boundary(self, tmp_path):
        """Mixed content that crosses the 64 KiB boundary."""
        path = str(tmp_path / "mixed_boundary.txt")
        # ASCII prefix just under 64 KiB, then multibyte chars push over
        ascii_part = "A" * (BUFFER_SIZE - 100)
        multibyte_part = "\U0001f600" * 50  # 200 bytes
        text = ascii_part + multibyte_part
        written = save_file(path, text)
        expected = text.encode("utf-8")
        assert written == len(expected)
        assert open(path, "rb").read() == expected

    def test_cjk_large_file(self, tmp_path):
        """CJK characters (3 bytes each in UTF-8) above 64 KiB."""
        path = str(tmp_path / "cjk_large.txt")
        # 3-byte CJK char; need > BUFFER_SIZE / 3 chars
        text = "世" * ((BUFFER_SIZE // 3) + 512)  # 世
        written = save_file(path, text)
        expected = text.encode("utf-8")
        assert written == len(expected)
        assert open(path, "rb").read() == expected
