"""Tests for file_handler: UTF-8 multibyte save at 64KB boundary."""

import os
import tempfile

import pytest

from src.file_handler import (
    DEFAULT_CHUNK_SIZE,
    _allocate_buffer,
    load_file,
    save_file,
)


@pytest.fixture
def tmp_path_file():
    """Yield a temporary file path, cleaned up after use."""
    fd, path = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


class TestSaveFileMultibyteUTF8:
    """Verify save works with multibyte UTF-8 at and above 64KB."""

    def test_save_65kb_emoji(self, tmp_path_file):
        """65KB of emoji characters saves successfully."""
        emoji_char = "\U0001F600"  # 4 bytes in UTF-8
        num_chars = (65 * 1024) // len(emoji_char.encode("utf-8")) + 1
        content = emoji_char * num_chars
        byte_len = len(content.encode("utf-8"))
        assert byte_len > 65 * 1024

        written = save_file(content, tmp_path_file)

        assert written == byte_len
        loaded = load_file(tmp_path_file)
        assert loaded == content

    def test_save_63kb_emoji(self, tmp_path_file):
        """63KB of emoji characters saves successfully (under boundary)."""
        emoji_char = "\U0001F600"
        num_chars = (63 * 1024) // len(emoji_char.encode("utf-8"))
        content = emoji_char * num_chars
        byte_len = len(content.encode("utf-8"))
        assert byte_len < 64 * 1024

        written = save_file(content, tmp_path_file)

        assert written == byte_len
        loaded = load_file(tmp_path_file)
        assert loaded == content

    def test_save_65kb_ascii(self, tmp_path_file):
        """65KB of ASCII-only content saves successfully."""
        content = "A" * (65 * 1024)
        byte_len = len(content.encode("utf-8"))

        written = save_file(content, tmp_path_file)

        assert written == byte_len
        loaded = load_file(tmp_path_file)
        assert loaded == content

    def test_save_128kb_mixed(self, tmp_path_file):
        """128KB mixed ASCII + multibyte content saves successfully."""
        ascii_part = "Hello World! " * 4000  # ~52KB ASCII
        cjk_part = "世界" * 15000  # ~90KB CJK (3 bytes each)
        content = ascii_part + cjk_part
        byte_len = len(content.encode("utf-8"))
        assert byte_len > 128 * 1024

        written = save_file(content, tmp_path_file)

        assert written == byte_len
        loaded = load_file(tmp_path_file)
        assert loaded == content

    def test_save_65kb_cjk(self, tmp_path_file):
        """65KB of CJK characters saves successfully."""
        cjk_char = "世"  # 3 bytes in UTF-8
        num_chars = (65 * 1024) // len(cjk_char.encode("utf-8")) + 1
        content = cjk_char * num_chars
        byte_len = len(content.encode("utf-8"))
        assert byte_len > 65 * 1024

        written = save_file(content, tmp_path_file)

        assert written == byte_len
        loaded = load_file(tmp_path_file)
        assert loaded == content

    def test_roundtrip_fidelity(self, tmp_path_file):
        """Byte-for-byte round-trip fidelity on reload."""
        content = "ASCII \U0001F4A9 CJK 世界 emoji \U0001F680" * 5000
        byte_len = len(content.encode("utf-8"))
        assert byte_len > DEFAULT_CHUNK_SIZE

        save_file(content, tmp_path_file)
        loaded = load_file(tmp_path_file)

        assert loaded == content
        assert loaded.encode("utf-8") == content.encode("utf-8")


class TestAllocateBuffer:
    """Verify buffer allocation uses byte length, not char count."""

    def test_ascii_byte_length_equals_char_count(self):
        """For ASCII, byte length equals character count."""
        content = "A" * 1000
        byte_len, _ = _allocate_buffer(content)
        assert byte_len == 1000

    def test_emoji_byte_length_exceeds_char_count(self):
        """For emoji, byte length is 4x the character count."""
        content = "\U0001F600" * 100
        byte_len, _ = _allocate_buffer(content)
        assert byte_len == 400  # 100 chars * 4 bytes each

    def test_cjk_byte_length_exceeds_char_count(self):
        """For CJK, byte length is 3x the character count."""
        content = "世" * 100
        byte_len, _ = _allocate_buffer(content)
        assert byte_len == 300  # 100 chars * 3 bytes each

    def test_num_chunks_accounts_for_byte_length(self):
        """Chunk count uses byte size, not character count."""
        # 20000 emoji chars = 80000 bytes > 64KB = 2 chunks needed
        content = "\U0001F600" * 20000
        _, num_chunks = _allocate_buffer(content)
        assert num_chunks == 2  # 80000 / 65536 -> 2 chunks

    def test_empty_content(self):
        """Empty content requires 0 bytes and 0 chunks."""
        byte_len, num_chunks = _allocate_buffer("")
        assert byte_len == 0
        assert num_chunks == 0
