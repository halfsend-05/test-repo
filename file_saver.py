"""File saving utility with proper UTF-8 buffer handling.

Allocates write buffers based on byte length rather than character count
to prevent buffer overflows when saving content containing multibyte
UTF-8 characters (emoji, CJK, etc.).
"""

import os
import tempfile

# Default buffer size in bytes.
DEFAULT_BUFFER_SIZE = 65536  # 64KB


def _encode_content(content: str) -> bytes:
    """Encode string content to UTF-8 bytes."""
    return content.encode("utf-8")


def save_file(path: str, content: str, buffer_size: int = DEFAULT_BUFFER_SIZE) -> None:
    """Save content to a file, writing in chunks sized by byte length.

    Uses a temporary file and atomic rename to prevent data corruption
    on crash. Buffers are allocated based on the byte length of the
    encoded content, not the character count, to correctly handle
    multibyte UTF-8 characters.

    Args:
        path: Destination file path.
        content: The text content to save.
        buffer_size: Maximum number of bytes per write chunk.

    Raises:
        OSError: If the file cannot be written.
    """
    data = _encode_content(content)
    dir_name = os.path.dirname(os.path.abspath(path))

    # Write to a temporary file first, then atomically rename.
    fd, tmp_path = tempfile.mkstemp(dir=dir_name)
    try:
        offset = 0
        while offset < len(data):
            chunk = data[offset : offset + buffer_size]
            os.write(fd, chunk)
            offset += len(chunk)
        os.fsync(fd)
        os.close(fd)
        fd = -1  # Mark as closed so the finally block doesn't double-close.
        os.replace(tmp_path, path)
    except BaseException:
        # Clean up the temp file on failure.
        if fd >= 0:
            os.close(fd)
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
