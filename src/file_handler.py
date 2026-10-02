"""File handler with chunked save support for large files.

Handles saving files in chunks, correctly accounting for UTF-8
multibyte character byte lengths when sizing buffers.
"""

# Default chunk size: 64KB
DEFAULT_CHUNK_SIZE = 65536


def save_file(content, path, chunk_size=DEFAULT_CHUNK_SIZE):
    """Save content to a file, writing in chunks.

    Splits the content into chunks based on byte size (not character
    count) to avoid buffer overflows with multibyte UTF-8 characters.

    Args:
        content: The string content to save.
        path: The file path to write to.
        chunk_size: Maximum byte size per chunk (default 64KB).

    Returns:
        The total number of bytes written.
    """
    encoded = content.encode("utf-8")
    total_bytes = len(encoded)

    with open(path, "wb") as f:
        offset = 0
        while offset < total_bytes:
            end = min(offset + chunk_size, total_bytes)
            f.write(encoded[offset:end])
            offset = end

    return total_bytes


def _allocate_buffer(content, chunk_size=DEFAULT_CHUNK_SIZE):
    """Calculate the required buffer size for a content chunk.

    Uses byte length of the UTF-8 encoded content rather than
    character count. Multibyte characters (emoji = 4 bytes,
    CJK = 3 bytes) can cause the byte count to exceed the
    character count significantly.

    Args:
        content: The string content to measure.
        chunk_size: The maximum chunk size in bytes.

    Returns:
        A tuple of (buffer_size, num_chunks) where buffer_size
        is the byte length and num_chunks is the number of chunks
        needed to write the content.
    """
    byte_length = len(content.encode("utf-8"))
    num_chunks = (byte_length + chunk_size - 1) // chunk_size
    return byte_length, num_chunks


def load_file(path):
    """Load a file and return its content as a string.

    Args:
        path: The file path to read from.

    Returns:
        The file content as a string.
    """
    with open(path, "rb") as f:
        data = f.read()
    return data.decode("utf-8")
