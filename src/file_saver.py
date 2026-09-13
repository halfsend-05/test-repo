"""File saving module with correct UTF-8 buffer handling.

Prior to v2.3.1, the save path allocated write buffers based on byte
length of the encoded content.  A regression in v2.3.1 switched to
character count, which under-allocates for multibyte UTF-8 sequences
(emoji, CJK, etc.) and causes a segmentation fault when the encoded
byte length exceeds the 64 KiB buffer boundary.

This module restores correct behavior by always sizing the buffer to
the *byte* length of the UTF-8-encoded content.
"""

# Default buffer size in bytes.
BUFFER_SIZE = 65536  # 64 KiB


def _encode_content(text: str) -> bytes:
    """Return UTF-8 encoded bytes for *text*."""
    return text.encode("utf-8")


def _allocate_buffer(data: bytes) -> bytearray:
    """Allocate a write buffer large enough for *data*.

    The buffer size is the larger of ``BUFFER_SIZE`` and the actual byte
    length of *data*, ensuring multibyte UTF-8 content never overflows.
    """
    size = max(BUFFER_SIZE, len(data))
    return bytearray(size)


def save_file(path: str, text: str) -> int:
    """Persist *text* to *path* and return the number of bytes written.

    The function encodes the text as UTF-8, allocates a buffer sized to
    the **byte** length (not the character count), and writes the
    content to disk.
    """
    data = _encode_content(text)
    buf = _allocate_buffer(data)
    buf[: len(data)] = data

    with open(path, "wb") as fh:
        fh.write(buf[: len(data)])

    return len(data)
