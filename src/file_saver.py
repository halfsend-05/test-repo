"""File saver module with correct UTF-8 multibyte character handling.

Provides file saving functionality that properly handles UTF-8 encoded
text of any size.  Buffer allocation uses byte length rather than
character count to prevent buffer overflows when saving files containing
multibyte characters (e.g., emoji, CJK characters).
"""

import os

# Default buffer size in bytes.
DEFAULT_BUFFER_SIZE = 64 * 1024  # 64KB


def save_file(filepath: str, content: str | bytes) -> None:
    """Save *content* to *filepath* with correct UTF-8 handling.

    Uses byte length (not character count) for buffer allocation to
    prevent overflows when content contains multibyte UTF-8 characters.
    """
    if not isinstance(content, (str, bytes)):
        raise TypeError(
            f"content must be str or bytes, got {type(content).__name__}"
        )

    if isinstance(content, str):
        data = content.encode("utf-8")
    else:
        data = content

    with open(filepath, "wb") as f:
        offset = 0
        total = len(data)
        while offset < total:
            chunk_end = min(offset + DEFAULT_BUFFER_SIZE, total)
            f.write(data[offset:chunk_end])
            offset = chunk_end
