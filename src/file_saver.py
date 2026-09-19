"""File saver module with correct UTF-8 multibyte character handling.

Provides file saving functionality that properly handles UTF-8 encoded
text of any size.  Buffer allocation uses byte length rather than
character count to prevent buffer overflows when saving files containing
multibyte characters (e.g., emoji, CJK characters).
"""

import os
import stat
import tempfile

# Default buffer size in bytes.
DEFAULT_BUFFER_SIZE = 64 * 1024  # 64KB


def _byte_length(text: str | bytes) -> int:
    """Return the byte length of *text* when encoded as UTF-8."""
    if isinstance(text, bytes):
        return len(text)
    return len(text.encode("utf-8"))


def save_file(filepath: str, content: str | bytes) -> None:
    """Save *content* to *filepath* with correct UTF-8 handling.

    Uses byte length (not character count) for buffer allocation to
    prevent overflows when content contains multibyte UTF-8 characters.

    The save is atomic: content is written to a temporary file first,
    then renamed to the target path.  If the target file already exists,
    its permission bits are preserved on the new file.
    """
    if not isinstance(content, (str, bytes)):
        raise TypeError(
            f"content must be str or bytes, got {type(content).__name__}"
        )

    if isinstance(content, str):
        data = content.encode("utf-8")
    else:
        data = content

    dir_name = os.path.dirname(filepath) or "."

    # Capture the original file's permissions before replacing it.
    original_mode: int | None = None
    try:
        original_mode = stat.S_IMODE(os.stat(filepath).st_mode)
    except FileNotFoundError:
        pass

    # Write to a temporary file first, then rename for atomicity.
    fd, tmp_path = tempfile.mkstemp(dir=dir_name)
    try:
        offset = 0
        total = len(data)
        while offset < total:
            chunk_end = min(offset + DEFAULT_BUFFER_SIZE, total)
            os.write(fd, data[offset:chunk_end])
            offset = chunk_end
        os.close(fd)
        fd = -1

        if original_mode is not None:
            os.chmod(tmp_path, original_mode)

        os.replace(tmp_path, filepath)
    except BaseException:
        try:
            if fd >= 0:
                os.close(fd)
        except OSError:
            pass
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
