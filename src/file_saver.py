"""File saver module with correct UTF-8 multibyte character handling.

This module provides file saving functionality that properly handles
UTF-8 encoded text of any size. The buffer allocation uses byte length
rather than character count to prevent buffer overflows when saving
files containing multibyte characters (e.g., emoji, CJK characters).
"""

import os
import tempfile

# Default buffer size in bytes.
DEFAULT_BUFFER_SIZE = 64 * 1024  # 64KB


def _byte_length(text):
    """Return the byte length of text when encoded as UTF-8."""
    if isinstance(text, bytes):
        return len(text)
    return len(text.encode("utf-8"))


def save_file(filepath, content):
    """Save content to a file with correct UTF-8 handling.

    Uses byte length (not character count) for buffer allocation to
    prevent overflows when content contains multibyte UTF-8 characters.

    The save is atomic: content is written to a temporary file first,
    then renamed to the target path. This prevents data loss if the
    process is interrupted during the write.

    Args:
        filepath: Path to the destination file.
        content: Text content to save. Accepts str or bytes.

    Raises:
        OSError: If the file cannot be written.
        TypeError: If content is not str or bytes.
    """
    if not isinstance(content, (str, bytes)):
        raise TypeError(
            f"content must be str or bytes, got {type(content).__name__}"
        )

    if isinstance(content, str):
        data = content.encode("utf-8")
    else:
        data = content

    dir_name = os.path.dirname(filepath) or "."

    # Write to a temporary file first, then rename for atomicity.
    fd, tmp_path = tempfile.mkstemp(dir=dir_name)
    try:
        offset = 0
        total = len(data)
        while offset < total:
            chunk_end = min(offset + DEFAULT_BUFFER_SIZE, total)
            os.write(fd, data[offset:chunk_end])
            offset = chunk_end
        os.close(fd)
        fd = -1
        os.replace(tmp_path, filepath)
    except BaseException:
        if fd >= 0:
            os.close(fd)
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def load_file(filepath):
    """Load and return the text content of a UTF-8 encoded file.

    Args:
        filepath: Path to the file to read.

    Returns:
        The file content as a string.

    Raises:
        FileNotFoundError: If the file does not exist.
        OSError: If the file cannot be read.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()
