"""File I/O module with chunked write support for UTF-8 content.

Handles saving files of arbitrary size, correctly accounting for
multibyte UTF-8 characters when splitting content into chunks.
"""

import os

# Default chunk size in bytes (64 KiB).
CHUNK_SIZE = 65536


def save_file(path: str, content: str) -> None:
    """Save text content to a file using chunked writes.

    Encodes *content* to UTF-8 **first**, then writes the resulting
    bytes in fixed-size chunks.  This avoids the buffer-overflow
    scenario where a chunk boundary falls inside a multibyte character
    sequence.

    Args:
        path: Destination file path.
        content: The text to write.

    Raises:
        OSError: If the file cannot be opened or written.
    """
    encoded = content.encode("utf-8")
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "wb") as fh:
            for offset in range(0, len(encoded), CHUNK_SIZE):
                fh.write(encoded[offset : offset + CHUNK_SIZE])
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        # Clean up the temp file on any failure.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def load_file(path: str) -> str:
    """Load a UTF-8 text file and return its content as a string.

    Args:
        path: Source file path.

    Returns:
        The decoded text content.

    Raises:
        OSError: If the file cannot be read.
        UnicodeDecodeError: If the file is not valid UTF-8.
    """
    with open(path, "rb") as fh:
        return fh.read().decode("utf-8")
