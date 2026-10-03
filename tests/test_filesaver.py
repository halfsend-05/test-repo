"""Tests for the file saver module.

Covers the UTF-8 multibyte buffer-handling fix for issue #2345:
the application crashed with a segfault when saving files larger than
64KB containing multibyte UTF-8 characters, because the write buffer
was sized by character count instead of byte length.
"""

import os
import tempfile

from src.filesaver import BUFFER_SIZE, save_file, validate_saved_file


class TestSaveFileASCII:
    """Verify basic ASCII saves still work correctly."""

    def test_small_ascii_file(self):
        content = "Hello, world!"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            written = save_file(path, content)
            assert written == len(content)
            assert validate_saved_file(path, content)
        finally:
            os.unlink(path)

    def test_ascii_file_over_64kb(self):
        """ASCII files larger than the buffer save correctly."""
        content = "A" * (BUFFER_SIZE + 1024)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            written = save_file(path, content)
            assert written == len(content)
            assert validate_saved_file(path, content)
        finally:
            os.unlink(path)

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            written = save_file(path, "")
            assert written == 0
            assert validate_saved_file(path, "")
        finally:
            os.unlink(path)


class TestSaveFileMultibyteUTF8:
    """Regression tests for issue #2345.

    The v2.3.1 bug caused a segfault when the byte length of the
    content exceeded 64KB due to multibyte UTF-8 characters, even
    when the character count was below that threshold.
    """

    def test_emoji_content_over_64kb(self):
        """4-byte emoji characters that push byte length past 64KB."""
        emoji = "\U0001f600"  # 😀 — 4 bytes in UTF-8
        # 18000 emojis × 4 bytes = 72000 bytes > 64KB
        num_chars = 18000
        content = emoji * num_chars

        byte_len = len(content.encode("utf-8"))
        assert byte_len == num_chars * 4
        assert byte_len > BUFFER_SIZE

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            written = save_file(path, content)
            assert written == byte_len
            assert validate_saved_file(path, content)
        finally:
            os.unlink(path)

    def test_cjk_content_over_64kb(self):
        """3-byte CJK characters that push byte length past 64KB."""
        cjk = "世"  # 3 bytes in UTF-8
        num_chars = 22000  # 22000 × 3 = 66000 bytes > 64KB
        content = cjk * num_chars

        byte_len = len(content.encode("utf-8"))
        assert byte_len > BUFFER_SIZE

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            written = save_file(path, content)
            assert written == byte_len
            assert validate_saved_file(path, content)
        finally:
            os.unlink(path)

    def test_mixed_ascii_and_emoji_over_64kb(self):
        """Mixed ASCII and multibyte content exceeding 64KB."""
        line = "Hello \U0001f30d World \U0001f680\n"
        line_bytes = len(line.encode("utf-8"))
        num_lines = (BUFFER_SIZE // line_bytes) + 100
        content = line * num_lines

        byte_len = len(content.encode("utf-8"))
        assert byte_len > BUFFER_SIZE

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            written = save_file(path, content)
            assert written == byte_len
            assert validate_saved_file(path, content)
        finally:
            os.unlink(path)

    def test_exact_buffer_boundary_with_emoji(self):
        """Content whose byte length is exactly the buffer size."""
        emoji = "\U0001f600"  # 4 bytes each
        num_chars = BUFFER_SIZE // 4  # exactly 65536 bytes
        content = emoji * num_chars

        byte_len = len(content.encode("utf-8"))
        assert byte_len == BUFFER_SIZE

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            written = save_file(path, content)
            assert written == BUFFER_SIZE
            assert validate_saved_file(path, content)
        finally:
            os.unlink(path)

    def test_one_byte_over_buffer_boundary(self):
        """Content one byte over the buffer boundary."""
        emoji = "\U0001f600"  # 4 bytes
        num_chars = BUFFER_SIZE // 4
        # Add one ASCII char to go 1 byte over
        content = (emoji * num_chars) + "x"

        byte_len = len(content.encode("utf-8"))
        assert byte_len == BUFFER_SIZE + 1

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            written = save_file(path, content)
            assert written == byte_len
            assert validate_saved_file(path, content)
        finally:
            os.unlink(path)

    def test_two_byte_characters_over_64kb(self):
        """2-byte UTF-8 characters (e.g. accented) over 64KB."""
        char = "é"  # é — 2 bytes in UTF-8
        num_chars = 33000  # 33000 × 2 = 66000 bytes > 64KB
        content = char * num_chars

        byte_len = len(content.encode("utf-8"))
        assert byte_len > BUFFER_SIZE

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            written = save_file(path, content)
            assert written == byte_len
            assert validate_saved_file(path, content)
        finally:
            os.unlink(path)


class TestValidateSavedFile:
    """Tests for validate_saved_file."""

    def test_matching_content(self):
        content = "Test \U0001f4dd content"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            save_file(path, content)
            assert validate_saved_file(path, content) is True
        finally:
            os.unlink(path)

    def test_mismatched_content(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
            f.write(b"Different content")
        try:
            assert validate_saved_file(path, "Original content") is False
        finally:
            os.unlink(path)
