"""Explicit canary guard for local persistence and export boundaries."""

import re
from collections.abc import Iterable

LOCAL_PATH_PATTERNS = (
    re.compile(rb"/Users/[^/\s]+/"),
    re.compile(rb"/home/[^/\s]+/"),
    re.compile(rb"[A-Za-z]:\\Users\\[^\\\s]+\\"),
)


class SensitiveDataError(ValueError):
    """Raised before a known secret or local path reaches persistent output."""


class SensitiveDataGuard:
    def __init__(self, forbidden_values: Iterable[str] = ()) -> None:
        self._forbidden_values = tuple(value for value in forbidden_values if value)

    def check_bytes(self, value: bytes) -> None:
        if any(pattern.search(value) for pattern in LOCAL_PATH_PATTERNS):
            raise SensitiveDataError("persistent output contains a local user path")
        for forbidden in self._forbidden_values:
            if forbidden.encode() in value:
                raise SensitiveDataError("persistent output contains a forbidden value")

    def check_text(self, value: str) -> None:
        self.check_bytes(value.encode())
