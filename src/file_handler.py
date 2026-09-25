"""File handler module for saving documents.

Handles file saving with proper UTF-8 encoding support for files of
any size. Fixes the v2.3.1 regression where buffer allocation used
character count instead of byte count, causing a crash on files
larger than 64KB containing multibyte UTF-8 characters.
"""

# Buffer size in bytes (64KB)
WRITE_BUFFER_SIZE = 65536


def save_file(content: str, path: str) -> int:
    """Save content to a file with proper UTF-8 encoding.

    Writes content in buffered chunks, using byte length (not character
    count) to size the buffer. This ensures multibyte UTF-8 characters
    (emoji, CJK, accented characters) do not cause the actual byte
    length to exceed the allocated buffer size.

    Args:
        content: The text content to save.
        path: The file path to write to.

    Returns:
        The number of bytes written.

    Raises:
        OSError: If the file cannot be written.
    """
    encoded = content.encode("utf-8")
    bytes_written = 0

    with open(path, "wb") as f:
        offset = 0
        while offset < len(encoded):
            chunk = encoded[offset : offset + WRITE_BUFFER_SIZE]
            f.write(chunk)
            bytes_written += len(chunk)
            offset += WRITE_BUFFER_SIZE

    return bytes_written


def calculate_buffer_size(content: str) -> int:
    """Calculate the required buffer size in bytes for the given content.

    Uses byte length of the UTF-8 encoded content, not the character
    count. This is the fix for the v2.3.1 regression: the old code used
    len(content) (character count), which underestimates the byte size
    when multibyte characters are present.

    Args:
        content: The text content to measure.

    Returns:
        The number of bytes needed to store the UTF-8 encoded content.
    """
    return len(content.encode("utf-8"))
