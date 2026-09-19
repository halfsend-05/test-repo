"""File saver module with correct UTF-8 multibyte character handling.

Provides file saving functionality that properly handles UTF-8 encoded
text of any size by encoding to bytes before writing, ensuring byte
length (not character count) determines the write size.
"""


def save_file(filepath: str, content: str) -> None:
    """Save *content* to *filepath* with correct UTF-8 handling.

    Encodes content to UTF-8 bytes before writing so that the full
    byte length is written regardless of multibyte character count.
    """
    if not isinstance(content, str):
        raise TypeError(
            f"content must be str, got {type(content).__name__}"
        )

    data = content.encode("utf-8")

    with open(filepath, "wb") as f:
        f.write(data)
