"""File save module with chunked writing support.

Handles saving files of arbitrary size, including those containing
multibyte UTF-8 characters (emoji, CJK, etc.).
"""

CHUNK_SIZE = 65536  # 64KB


def save_file(path: str, content: str) -> None:
    """Save content to a file using chunked writes.

    Writes the content in chunks of up to CHUNK_SIZE bytes, ensuring
    that multibyte UTF-8 sequences are never split across chunk
    boundaries.

    Args:
        path: Destination file path.
        content: The text content to write.
    """
    encoded = content.encode("utf-8")
    with open(path, "wb") as f:
        offset = 0
        while offset < len(encoded):
            end = min(offset + CHUNK_SIZE, len(encoded))
            # Avoid splitting a multibyte UTF-8 sequence at the chunk
            # boundary.  If 'end' lands in the middle of a sequence,
            # back up to the start of that character.
            if end < len(encoded):
                while end > offset and (encoded[end] & 0xC0) == 0x80:
                    end -= 1
            f.write(encoded[offset:end])
            offset = end
