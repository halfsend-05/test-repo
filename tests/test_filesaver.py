"""Tests for the file saver module.

Covers the UTF-8 multibyte buffer handling fix for issue #2317:
application crashed with segfault when saving files >64KB containing
multibyte UTF-8 characters because the buffer was sized by character
count instead of byte length.
"""

import os
import tempfile

from src.filesaver import (
    BUFFER_SIZE,
    _compute_byte_length,
    save_file,
    validate_saved_file,
)


class TestComputeByteLength:
    """Tests for _compute_byte_length."""

    def test_ascii_only(self):
        """ASCII characters are 1 byte each."""
        text = "hello world"
        assert _compute_byte_length(text) == len(text)

    def test_multibyte_emoji(self):
        """Emoji characters are 4 bytes each in UTF-8."""
        text = "\U0001f600"  # 😀
        assert _compute_byte_length(text) == 4
        assert len(text) == 1  # but only 1 character

    def test_cjk_characters(self):
        """CJK characters are 3 bytes each in UTF-8."""
        text = "世界"  # 世界
        assert _compute_byte_length(text) == 6
        assert len(text) == 2  # but only 2 characters

    def test_mixed_content(self):
        """Mixed ASCII and multibyte content."""
        text = "Hello \U0001f30d"  # Hello 🌍
        # 'Hello ' = 6 bytes, 🌍 = 4 bytes
        assert _compute_byte_length(text) == 10
        assert len(text) == 7  # 6 chars + 1 emoji

    def test_empty_string(self):
        assert _compute_byte_length("") == 0


class TestSaveFile:
    """Tests for save_file."""

    def test_save_small_ascii_file(self):
        """Small ASCII files save correctly."""
        content = "Hello, world!"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            filepath = f.name

        try:
            bytes_written = save_file(filepath, content)
            assert bytes_written == len(content)
            assert validate_saved_file(filepath, content)
        finally:
            os.unlink(filepath)

    def test_save_large_ascii_file_over_64kb(self):
        """ASCII files over 64KB save correctly (regression check)."""
        # Create content larger than the 64KB buffer
        content = "A" * (BUFFER_SIZE + 1024)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            filepath = f.name

        try:
            bytes_written = save_file(filepath, content)
            assert bytes_written == len(content)
            assert validate_saved_file(filepath, content)
        finally:
            os.unlink(filepath)

    def test_save_large_file_with_multibyte_utf8(self):
        """Files >64KB with multibyte UTF-8 characters save without crash.

        This is the primary regression test for issue #2317.
        The old code used len(text) (character count) for buffer sizing,
        which caused a segfault when multibyte characters made the actual
        byte length exceed the buffer.
        """
        # Create ~70KB of emoji content (each emoji is 4 bytes UTF-8)
        emoji_char = "\U0001f600"  # 😀
        # We need enough characters so byte length exceeds 64KB
        # 4 bytes per emoji, so 18000 emojis = 72000 bytes > 64KB
        num_chars = 18000
        content = emoji_char * num_chars

        # Verify our test data is structured correctly
        assert len(content) == num_chars  # character count
        assert _compute_byte_length(content) == num_chars * 4  # byte length
        assert _compute_byte_length(content) > BUFFER_SIZE

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            filepath = f.name

        try:
            bytes_written = save_file(filepath, content)
            assert bytes_written == num_chars * 4
            assert validate_saved_file(filepath, content)
        finally:
            os.unlink(filepath)

    def test_save_multibyte_at_exact_64kb_boundary(self):
        """Multibyte characters spanning the 64KB buffer boundary.

        Edge case: content is exactly at the buffer size boundary
        in bytes.
        """
        emoji_char = "\U0001f600"  # 4 bytes each
        # BUFFER_SIZE / 4 = exactly 16384 emojis = exactly 65536 bytes
        num_chars = BUFFER_SIZE // 4
        content = emoji_char * num_chars

        assert _compute_byte_length(content) == BUFFER_SIZE

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            filepath = f.name

        try:
            bytes_written = save_file(filepath, content)
            assert bytes_written == BUFFER_SIZE
            assert validate_saved_file(filepath, content)
        finally:
            os.unlink(filepath)

    def test_save_cjk_content_over_64kb(self):
        """CJK characters (3 bytes each) over 64KB save correctly."""
        cjk_char = "世"  # 世 - 3 bytes in UTF-8
        # Need > 64KB in bytes: 65536 / 3 ≈ 21846 chars for exact,
        # use 22000 to be safely over
        num_chars = 22000
        content = cjk_char * num_chars

        assert _compute_byte_length(content) > BUFFER_SIZE

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            filepath = f.name

        try:
            bytes_written = save_file(filepath, content)
            assert bytes_written == num_chars * 3
            assert validate_saved_file(filepath, content)
        finally:
            os.unlink(filepath)

    def test_save_mixed_ascii_and_multibyte_over_64kb(self):
        """Mixed ASCII and multibyte content over 64KB saves correctly."""
        # Mix of ASCII and emoji to create >64KB
        line = "Hello \U0001f30d World \U0001f680\n"
        # Each line: 'Hello ' (6) + 🌍 (4) + ' World ' (7) + 🚀 (4) + '\n' (1) = 22 bytes
        line_bytes = _compute_byte_length(line)
        num_lines = (BUFFER_SIZE // line_bytes) + 100
        content = line * num_lines

        assert _compute_byte_length(content) > BUFFER_SIZE

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            filepath = f.name

        try:
            bytes_written = save_file(filepath, content)
            assert bytes_written == _compute_byte_length(content)
            assert validate_saved_file(filepath, content)
        finally:
            os.unlink(filepath)

    def test_save_empty_file(self):
        """Empty content saves correctly."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            filepath = f.name

        try:
            bytes_written = save_file(filepath, "")
            assert bytes_written == 0
            assert validate_saved_file(filepath, "")
        finally:
            os.unlink(filepath)


class TestValidateSavedFile:
    """Tests for validate_saved_file."""

    def test_validates_matching_content(self):
        content = "Test \U0001f4dd content"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            filepath = f.name

        try:
            save_file(filepath, content)
            assert validate_saved_file(filepath, content) is True
        finally:
            os.unlink(filepath)

    def test_detects_mismatched_content(self):
        content = "Original content"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            filepath = f.name
            f.write(b"Different content")

        try:
            assert validate_saved_file(filepath, content) is False
        finally:
            os.unlink(filepath)
