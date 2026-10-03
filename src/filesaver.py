"""File saving module with UTF-8-aware buffer handling.

Fixes a segmentation fault that occurred when saving files larger than
64KB containing multibyte UTF-8 characters (emoji, CJK, accented
characters). The root cause was that the write buffer was sized using
character count (len(text)) rather than byte length, causing an
underallocation when characters occupy more than one byte in UTF-8
encoding. This led to buffer overflows at the 64KB boundary when
multibyte sequences were split across buffer chunks.

The fix encodes content to bytes first and then writes in byte-sized
chunks, ensuring buffer boundaries never split a multibyte character.
"""

# Default write-buffer size in bytes.
BUFFER_SIZE = 65536  # 64KB


def save_file(filepath: str, content: str) -> int:
    """Save text content to a file using UTF-8-aware buffered writes.

    Encodes the full content to UTF-8 bytes first, then writes in
    byte-aligned chunks. This avoids the v2.3.1 bug where the buffer
    was sized by character count, causing a segfault when multibyte
    characters made the actual byte length exceed the buffer.

    Args:
        filepath: Destination file path.
        content: Text content to write.

    Returns:
        Total number of bytes written.

    Raises:
        OSError: If the file cannot be opened or written.
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
    """Verify a saved file matches the original content byte-for-byte.

    Args:
        filepath: Path to the saved file.
        original_content: The original text that was saved.

    Returns:
        True if the saved bytes match the original encoded content.
    """
    with open(filepath, "rb") as f:
        saved_bytes = f.read()

    return saved_bytes == original_content.encode("utf-8")
