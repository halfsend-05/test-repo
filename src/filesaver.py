"""File saving module with proper UTF-8 buffer handling.

This module provides file-saving functionality that correctly handles
UTF-8 multibyte characters by sizing buffers based on byte length
rather than character count.

Fixed in v2.3.2: Prior to this fix (v2.3.1), the buffer was allocated
using character count (len(text)), which underallocated for multibyte
UTF-8 characters and caused a segmentation fault on files larger than
64KB containing emoji or CJK characters.
"""

# Default buffer size in bytes
BUFFER_SIZE = 65536  # 64KB


def _compute_byte_length(text: str) -> int:
    """Return the byte length of a string when encoded as UTF-8.

    This must be used instead of len(text), which returns the character
    count. For multibyte UTF-8 characters (emoji, CJK, accented chars),
    the byte length can be up to 4x the character count.
    """
    return len(text.encode("utf-8"))


def save_file(filepath: str, content: str) -> int:
    """Save content to a file, handling UTF-8 multibyte characters correctly.

    Writes the content in chunks sized by byte length (not character count)
    to avoid buffer overflows when content contains multibyte UTF-8
    characters.

    Args:
        filepath: Path to the output file.
        content: Text content to save.

    Returns:
        The number of bytes written.

    Raises:
        OSError: If the file cannot be written.
    """
    encoded = content.encode("utf-8")
    total_bytes = len(encoded)

    bytes_written = 0
    with open(filepath, "wb") as f:
        while bytes_written < total_bytes:
            end = min(bytes_written + BUFFER_SIZE, total_bytes)
            chunk = encoded[bytes_written:end]
            f.write(chunk)
            bytes_written += len(chunk)

    return bytes_written


def validate_saved_file(filepath: str, original_content: str) -> bool:
    """Verify that a saved file matches the original content byte-for-byte.

    Args:
        filepath: Path to the saved file.
        original_content: The original text content that was saved.

    Returns:
        True if the file content matches the original, False otherwise.
    """
    with open(filepath, "rb") as f:
        saved_bytes = f.read()

    expected_bytes = original_content.encode("utf-8")
    return saved_bytes == expected_bytes
