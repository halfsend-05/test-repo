"""File save handler with chunked write support.

Handles saving files of arbitrary size using a chunked write buffer.
Correctly accounts for UTF-8 multibyte character boundaries to avoid
buffer overflows at chunk boundaries.
"""

# Default write buffer size: 64KB
WRITE_BUFFER_SIZE = 65536


def save_file(path: str, content: str) -> None:
    """Save content to a file using chunked writes.

    Writes the content in chunks of WRITE_BUFFER_SIZE bytes,
    ensuring that UTF-8 multibyte characters are never split
    across chunk boundaries.

    Args:
        path: Destination file path.
        content: String content to write.

    Raises:
        OSError: If the file cannot be written.
    """
    encoded = content.encode("utf-8")
    total_bytes = len(encoded)

    with open(path, "wb") as f:
        offset = 0
        while offset < total_bytes:
            end = min(offset + WRITE_BUFFER_SIZE, total_bytes)

            # If we're not at the end of the data, avoid splitting a
            # multibyte UTF-8 character at the chunk boundary.
            if end < total_bytes:
                end = _safe_chunk_boundary(encoded, end)

            f.write(encoded[offset:end])
            offset = end


def _safe_chunk_boundary(data: bytes, pos: int) -> int:
    """Adjust pos backward so it does not fall inside a multibyte sequence.

    UTF-8 continuation bytes have the form 10xxxxxx (0x80..0xBF).
    If pos lands on a continuation byte, move backward until we reach
    the leading byte or a single-byte character.

    Args:
        data: The full encoded byte string.
        pos: Proposed split position.

    Returns:
        Adjusted position that does not split a multibyte character.
    """
    # Walk backward past any continuation bytes (10xxxxxx)
    while pos > 0 and (data[pos] & 0xC0) == 0x80:
        pos -= 1
    return pos
