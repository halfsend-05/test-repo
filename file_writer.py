"""Buffered file writer with UTF-8-aware chunking.

Writes data in chunks up to BUFFER_SIZE bytes, ensuring that chunk
boundaries never split a multibyte UTF-8 character.  Previous versions
used a naive byte-offset split, which produced invalid byte sequences
at the boundary and caused crashes when the downstream consumer
validated the encoding.
"""

BUFFER_SIZE = 65536  # 64 KiB


def _utf8_safe_boundary(data: bytes, limit: int) -> int:
    """Return the largest offset <= *limit* that does not split a UTF-8 character.

    UTF-8 continuation bytes have the bit pattern 10xxxxxx (0x80..0xBF).
    Walking backwards from *limit* until we hit a non-continuation byte
    gives us the start of the (possibly multibyte) character that
    straddles the boundary.  If that character fits entirely within
    *limit* we keep it; otherwise we split just before it.
    """
    if limit >= len(data):
        return len(data)

    # If the byte at `limit` is not a continuation byte, we are already
    # on a character boundary.
    if data[limit] & 0xC0 != 0x80:
        return limit

    # Walk back to find the leading byte of the character that spans
    # the boundary (at most 3 continuation bytes in valid UTF-8).
    pos = limit
    while pos > 0 and data[pos] & 0xC0 == 0x80:
        pos -= 1

    # `pos` now points at the leading byte.  The entire character
    # starts at `pos`, so we split just before it.
    return pos


def save_file(path: str, content: str) -> None:
    """Write *content* to *path* using buffered, UTF-8-safe chunking."""
    data = content.encode("utf-8")

    with open(path, "wb") as fh:
        offset = 0
        while offset < len(data):
            end = min(offset + BUFFER_SIZE, len(data))
            end = _utf8_safe_boundary(data, end)
            fh.write(data[offset:end])
            offset = end
