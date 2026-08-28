"""Tests for file_saver module.

Covers the boundary conditions around the 64KB buffer with multibyte
UTF-8 characters to prevent regressions of the segfault fixed in
issue #1720.
"""

import os
import tempfile

import pytest

from file_saver import BUFFER_SIZE, save_file


@pytest.fixture()
def tmp_path_file(tmp_path):
    """Return a path to a temporary file inside a temporary directory."""
    return str(tmp_path / "output.txt")


class TestSaveFileUTF8:
    """Verify that save_file handles multibyte UTF-8 around the 64KB boundary."""

    def test_small_ascii_file(self, tmp_path_file):
        """Control: small ASCII content saves correctly."""
        content = "hello world"
        save_file(tmp_path_file, content)
        assert open(tmp_path_file, "r", encoding="utf-8").read() == content

    def test_64kb_multibyte(self, tmp_path_file):
        """File at the 64KB boundary with multibyte chars should succeed."""
        # Each emoji is 4 bytes in UTF-8; 16384 emojis = 65536 bytes = 64KB
        content = "\U0001f600" * (BUFFER_SIZE // 4)
        save_file(tmp_path_file, content)
        result = open(tmp_path_file, "r", encoding="utf-8").read()
        assert result == content

    def test_65kb_multibyte(self, tmp_path_file):
        """File just over 64KB with multibyte chars should succeed."""
        content = "\U0001f600" * ((BUFFER_SIZE // 4) + 256)
        save_file(tmp_path_file, content)
        result = open(tmp_path_file, "r", encoding="utf-8").read()
        assert result == content

    def test_70kb_multibyte(self, tmp_path_file):
        """File well over 64KB with multibyte chars should succeed."""
        # ~70KB of emoji
        content = "\U0001f600" * (70 * 1024 // 4)
        save_file(tmp_path_file, content)
        result = open(tmp_path_file, "r", encoding="utf-8").read()
        assert result == content

    def test_multibyte_spanning_boundary(self, tmp_path_file):
        """A multibyte char at the exact 64KB byte offset must not be split."""
        # Fill with ASCII up to 1 byte before the buffer boundary, then
        # place a 4-byte emoji so it straddles the 64KB mark.
        ascii_part = "A" * (BUFFER_SIZE - 1)
        content = ascii_part + "\U0001f600" + "B" * 1024
        save_file(tmp_path_file, content)
        result = open(tmp_path_file, "r", encoding="utf-8").read()
        assert result == content

    def test_70kb_ascii_only(self, tmp_path_file):
        """Control: large ASCII-only file saves correctly."""
        content = "A" * (70 * 1024)
        save_file(tmp_path_file, content)
        result = open(tmp_path_file, "r", encoding="utf-8").read()
        assert result == content

    def test_cjk_characters(self, tmp_path_file):
        """CJK characters (3-byte UTF-8) over 64KB should succeed."""
        # Each CJK char is 3 bytes; need > 64KB = > 21846 chars
        content = "世" * 22000  # 66000 bytes
        save_file(tmp_path_file, content)
        result = open(tmp_path_file, "r", encoding="utf-8").read()
        assert result == content

    def test_mixed_ascii_and_emoji(self, tmp_path_file):
        """Mixed ASCII and multibyte content over 64KB should succeed."""
        # Alternate ASCII lines and emoji lines
        lines = []
        for i in range(2000):
            if i % 2 == 0:
                lines.append("A" * 40)
            else:
                lines.append("\U0001f600" * 10)
        content = "\n".join(lines)
        assert len(content.encode("utf-8")) > BUFFER_SIZE
        save_file(tmp_path_file, content)
        result = open(tmp_path_file, "r", encoding="utf-8").read()
        assert result == content

    def test_empty_file(self, tmp_path_file):
        """Edge case: empty content should save an empty file."""
        save_file(tmp_path_file, "")
        result = open(tmp_path_file, "r", encoding="utf-8").read()
        assert result == ""

    def test_atomic_write_no_partial(self, tmp_path):
        """On failure the original file should not be corrupted."""
        target = str(tmp_path / "existing.txt")
        save_file(target, "original content")

        # Attempt to save to a read-only directory to trigger an error
        ro_dir = str(tmp_path / "readonly")
        os.makedirs(ro_dir)
        bad_target = os.path.join(ro_dir, "file.txt")
        save_file(bad_target, "first write")

        os.chmod(ro_dir, 0o444)
        try:
            with pytest.raises(OSError):
                save_file(bad_target, "should fail")
        finally:
            os.chmod(ro_dir, 0o755)
