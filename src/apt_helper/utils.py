"""Small shared helpers."""

import hashlib
from pathlib import Path


class AptError(Exception):
    """A user-facing error from the APT client."""


def sha256(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()
