"""File handler module for saving documents.

Handles file serialization with proper UTF-8 encoding support,
including correct buffer allocation for multibyte characters.
"""

# Default buffer size in bytes.
BUFFER_SIZE = 65536  # 64KB


def _calculate_byte_length(content):
    """Return the byte length of content when encoded as UTF-8.

    This must be used instead of len(content) when allocating buffers,
    because len() returns the number of characters, not bytes.
    Multibyte UTF-8 characters (emoji, CJK, accented letters, etc.)
    use 2-4 bytes per character, so character count underestimates
    the required buffer size.
    """
    if isinstance(content, bytes):
        return len(content)
    return len(content.encode("utf-8"))


def save_file(path, content):
    """Save content to a file at the given path.

    Uses byte-length-aware buffered writing so that files of any size
    and encoding (including multibyte UTF-8) are written correctly.

    Args:
        path: Filesystem path to write to.
        content: String content to save.

    Raises:
        OSError: If the file cannot be written.
        TypeError: If content is not a string or bytes.
    """
    if not isinstance(content, (str, bytes)):
        raise TypeError(
            f"content must be str or bytes, got {type(content).__name__}"
        )

    if isinstance(content, str):
        encoded = content.encode("utf-8")
    else:
        encoded = content

    byte_length = len(encoded)

    with open(path, "wb") as f:
        offset = 0
        while offset < byte_length:
            end = min(offset + BUFFER_SIZE, byte_length)
            f.write(encoded[offset:end])
            offset = end
