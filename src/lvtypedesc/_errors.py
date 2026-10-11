"""The single error type raised for malformed or unsupported input."""

from __future__ import annotations


class TypeDescError(ValueError):
    """Raised when a byte string is not a type descriptor this library can parse.

    Covers truncated input, an impossible length word, and type codes that are
    unknown or outside the supported subset.
    """
