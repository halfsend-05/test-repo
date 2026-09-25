"""Tests for file_handler module.

Covers the regression case from issue #2186: saving files larger than
64KB with multibyte UTF-8 characters should not crash.
"""

import os
import tempfile

from src.file_handler import WRITE_BUFFER_SIZE, calculate_buffer_size, save_file


class TestCalculateBufferSize:
    """Tests for calculate_buffer_size using byte count, not char count."""

    def test_ascii_byte_count_equals_char_count(self):
        text = "hello world"
        assert calculate_buffer_size(text) == len(text)

    def test_emoji_byte_count_exceeds_char_count(self):
        # Each emoji is 4 bytes in UTF-8
        text = "\U0001f600" * 10  # 10 emoji characters
        assert calculate_buffer_size(text) == 40
        assert len(text) == 10  # char count is only 10

    def test_cjk_byte_count_exceeds_char_count(self):
        # Each CJK character is 3 bytes in UTF-8
        text = "世界" * 10  # 20 CJK characters
        assert calculate_buffer_size(text) == 60
        assert len(text) == 20

    def test_mixed_content(self):
        text = "hello \U0001f600 世界"  # ASCII + emoji + CJK
        expected = 6 + 4 + 1 + 6  # "hello " + emoji + " " + 2 CJK chars
        assert calculate_buffer_size(text) == expected

    def test_empty_string(self):
        assert calculate_buffer_size("") == 0


class TestSaveFile:
    """Tests for save_file with proper UTF-8 handling."""

    def test_save_small_ascii_file(self):
        content = "Hello, world!"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            bytes_written = save_file(content, path)
            assert bytes_written == len(content)
            with open(path, "rb") as f:
                assert f.read() == content.encode("utf-8")
        finally:
            os.unlink(path)

    def test_save_under_64kb_with_emoji(self):
        """Save 60KB file with emoji - should succeed (under boundary)."""
        # Each emoji is 4 bytes; 15000 emoji = 60KB
        content = "\U0001f600" * 15000
        byte_size = len(content.encode("utf-8"))
        assert byte_size == 60000  # under 64KB
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            bytes_written = save_file(content, path)
            assert bytes_written == byte_size
            with open(path, "rb") as f:
                saved = f.read()
            assert saved.decode("utf-8") == content
        finally:
            os.unlink(path)

    def test_save_over_64kb_ascii_only(self):
        """Save 70KB file with ASCII only - should succeed."""
        content = "A" * 71680  # 70KB of ASCII
        byte_size = len(content.encode("utf-8"))
        assert byte_size > WRITE_BUFFER_SIZE
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            bytes_written = save_file(content, path)
            assert bytes_written == byte_size
            with open(path, "rb") as f:
                saved = f.read()
            assert saved.decode("utf-8") == content
        finally:
            os.unlink(path)

    def test_save_over_64kb_with_emoji(self):
        """Save 70KB+ file with emoji - the regression case from #2186."""
        # Each emoji is 4 bytes; 18000 emoji = 72000 bytes > 64KB
        content = "\U0001f600" * 18000
        byte_size = len(content.encode("utf-8"))
        assert byte_size > WRITE_BUFFER_SIZE
        # Character count is much less than byte count
        assert len(content) < WRITE_BUFFER_SIZE
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            bytes_written = save_file(content, path)
            assert bytes_written == byte_size
            with open(path, "rb") as f:
                saved = f.read()
            assert saved.decode("utf-8") == content
        finally:
            os.unlink(path)

    def test_save_over_64kb_with_cjk(self):
        """Save 70KB+ file with CJK characters."""
        # Each CJK char is 3 bytes; 24000 CJK chars = 72000 bytes > 64KB
        content = "世" * 24000
        byte_size = len(content.encode("utf-8"))
        assert byte_size > WRITE_BUFFER_SIZE
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            bytes_written = save_file(content, path)
            assert bytes_written == byte_size
            with open(path, "rb") as f:
                saved = f.read()
            assert saved.decode("utf-8") == content
        finally:
            os.unlink(path)

    def test_save_over_64kb_mixed_content(self):
        """Save 70KB+ file with mixed ASCII + multibyte characters."""
        # Mix ASCII with emoji to exceed 64KB in bytes
        ascii_part = "A" * 30000  # 30KB ASCII
        emoji_part = "\U0001f600" * 11000  # 44KB of emoji
        content = ascii_part + emoji_part
        byte_size = len(content.encode("utf-8"))
        assert byte_size > WRITE_BUFFER_SIZE
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            bytes_written = save_file(content, path)
            assert bytes_written == byte_size
            with open(path, "rb") as f:
                saved = f.read()
            assert saved.decode("utf-8") == content
        finally:
            os.unlink(path)

    def test_save_exactly_64kb_with_trailing_emoji(self):
        """Boundary test: exactly 64KB file with a trailing emoji."""
        # 65536 - 4 = 65532 bytes of ASCII, then one 4-byte emoji
        ascii_part = "A" * 65532
        emoji_part = "\U0001f600"
        content = ascii_part + emoji_part
        byte_size = len(content.encode("utf-8"))
        assert byte_size == WRITE_BUFFER_SIZE  # exactly 64KB
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            bytes_written = save_file(content, path)
            assert bytes_written == byte_size
            with open(path, "rb") as f:
                saved = f.read()
            assert saved.decode("utf-8") == content
        finally:
            os.unlink(path)

    def test_save_empty_file(self):
        """Save an empty file."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            path = f.name
        try:
            bytes_written = save_file("", path)
            assert bytes_written == 0
            with open(path, "rb") as f:
                assert f.read() == b""
        finally:
            os.unlink(path)
