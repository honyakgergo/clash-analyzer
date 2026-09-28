"""Player / clan tag normalization.

Tags only use the characters ``0289CGJLPQRUVY``. Users often type the letter ``O``
for the digit ``0`` and forget or double the ``#``, so we normalize before validating.
"""

import re
from urllib.parse import quote

TAG_ALPHABET = "0289CGJLPQRUVY"
_TAG_RE = re.compile(rf"^[{TAG_ALPHABET}]{{3,15}}$")


class InvalidTagError(ValueError):
    pass


def normalize_tag(raw: str) -> str:
    """Return the canonical ``#TAG`` form, or raise :class:`InvalidTagError`."""
    tag = raw.strip().upper().replace("%23", "").lstrip("#").replace("O", "0")
    if not _TAG_RE.match(tag):
        raise InvalidTagError(f"Invalid tag {raw!r}: tags use only {TAG_ALPHABET}")
    return f"#{tag}"


def encode_tag(tag: str) -> str:
    """URL path segment for a tag: ``#ABC`` -> ``%23ABC``."""
    return quote(normalize_tag(tag), safe="")
