"""File save module with correct UTF-8 buffer handling.

Fixes segmentation fault when saving files larger than 64KB that contain
UTF-8 multibyte characters. The previous implementation used character
count for buffer capacity checks instead of byte length, causing buffer
overflows when multibyte characters pushed the byte size beyond the
allocated buffer while the character count remained under the limit.
"""

import os
import tempfile

BUFFER_SIZE = 65536  # 64KB buffer


def save_file(path, content):
    """Save content to a file using chunked writes with byte-aware buffering.

    Splits content into chunks based on byte length (not character count)
    to prevent buffer overflows with multibyte UTF-8 characters. Uses
    atomic write (write to temp file, then rename) to prevent data loss
    on failure.

    Args:
        path: Destination file path.
        content: String content to save.

    Raises:
        OSError: If the file cannot be written.
    """
    encoded = content.encode("utf-8")
    dir_name = os.path.dirname(os.path.abspath(path))

    fd, tmp_path = tempfile.mkstemp(dir=dir_name)
    try:
        offset = 0
        while offset < len(encoded):
            end = min(offset + BUFFER_SIZE, len(encoded))
            # Avoid splitting a multibyte UTF-8 sequence at the chunk
            # boundary.  Walk back from the tentative end until we land
            # on a byte that is NOT a continuation byte (0x80..0xBF).
            if end < len(encoded):
                while end > offset and (encoded[end] & 0xC0) == 0x80:
                    end -= 1
            os.write(fd, encoded[offset:end])
            offset = end
    except Exception:
        os.close(fd)
        os.unlink(tmp_path)
        raise
    else:
        os.close(fd)
        os.replace(tmp_path, path)
