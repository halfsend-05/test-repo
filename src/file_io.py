"""File I/O module for saving documents.

Handles writing document content to disk with proper UTF-8 support.
Buffer allocation uses byte length (not character count) to correctly
handle multibyte UTF-8 characters such as emoji and CJK text.
"""

import os
import tempfile

# Default buffer size: 64KB
BUFFER_SIZE = 65536


def save_document(path, content):
    """Save document content to the given file path.

    Uses byte length for buffer allocation to correctly handle UTF-8
    multibyte characters. Writes atomically via a temporary file to
    avoid partial writes on failure.

    Args:
        path: Destination file path.
        content: String content to save.

    Raises:
        OSError: If the file cannot be written.
        TypeError: If content is not a string.
    """
    if not isinstance(content, str):
        raise TypeError("content must be a string")

    encoded = content.encode("utf-8")
    byte_length = len(encoded)

    dir_name = os.path.dirname(os.path.abspath(path))
    os.makedirs(dir_name, exist_ok=True)

    # Write via temporary file for atomicity
    fd, tmp_path = tempfile.mkstemp(dir=dir_name)
    try:
        offset = 0
        while offset < byte_length:
            chunk = encoded[offset : offset + BUFFER_SIZE]
            os.write(fd, chunk)
            offset += len(chunk)
        os.close(fd)
        fd = -1
        os.replace(tmp_path, path)
    except BaseException:
        if fd >= 0:
            os.close(fd)
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def load_document(path):
    """Load document content from the given file path.

    Args:
        path: Source file path.

    Returns:
        The file contents as a string.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
