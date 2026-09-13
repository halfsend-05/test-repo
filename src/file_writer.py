"""File writer module with UTF-8 aware buffered writing.

Fixes a segmentation-fault-class bug where a 64KB write buffer could
split multibyte UTF-8 sequences at the buffer boundary, corrupting
output and crashing the application.
"""

import os

# Buffer size in bytes.  The v2.3.1 regression used a hard 65536-byte
# boundary without checking whether a multibyte character straddled it.
BUFFER_SIZE = 65536  # 64 KiB


def _find_safe_split(data: bytes, limit: int) -> int:
    """Return the largest index <= *limit* that does not split a UTF-8 char.

    UTF-8 continuation bytes have the bit pattern 10xxxxxx (0x80..0xBF).
    Walking back from *limit* until we hit a non-continuation byte gives
    us the start of the last character.  If that character extends past
    *limit* we split before it; otherwise *limit* itself is safe.
    """
    if limit >= len(data):
        return len(data)

    # Already on a character boundary (next byte is a leading byte)?
    if (data[limit] & 0xC0) != 0x80:
        return limit

    # Walk backwards past continuation bytes to find the leading byte.
    pos = limit
    while pos > 0 and (data[pos] & 0xC0) == 0x80:
        pos -= 1

    # *pos* is now the leading byte.  Determine expected character length.
    lead = data[pos]
    if (lead & 0x80) == 0:
        char_len = 1
    elif (lead & 0xE0) == 0xC0:
        char_len = 2
    elif (lead & 0xF0) == 0xE0:
        char_len = 3
    elif (lead & 0xF8) == 0xF0:
        char_len = 4
    else:
        # Invalid leading byte — split before it to avoid corruption.
        return pos

    # Does the full character fit within *limit*?
    if pos + char_len <= limit:
        return limit
    # It doesn't — split before the character.
    return pos


def save_file(path: str, content: str) -> None:
    """Write *content* to *path* using a 64 KiB buffer.

    The buffer is flushed at UTF-8 character boundaries so multibyte
    sequences are never split across writes.
    """
    encoded = content.encode("utf-8")
    offset = 0

    with open(path, "wb") as fh:
        while offset < len(encoded):
            end = min(offset + BUFFER_SIZE, len(encoded))
            safe_end = _find_safe_split(encoded, end)
            # Defensive: if _find_safe_split returns the same offset
            # (e.g. a single character wider than the buffer — impossible
            # for valid UTF-8 but guard anyway), advance by one byte.
            if safe_end == offset:
                safe_end = end
            fh.write(encoded[offset:safe_end])
            offset = safe_end
