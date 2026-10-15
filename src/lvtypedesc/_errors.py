"""The error raised for descriptors and trees this library cannot read or write."""

from __future__ import annotations


class TypeDescError(ValueError):
    """Raised for a byte string that is not a type descriptor this library can parse,
    and for a tree that cannot be written back as one.

    Covers truncated input, an impossible length word, a name that runs past its
    descriptor, unknown or unsupported type codes, nesting deeper than ``MAX_DEPTH``,
    and values that do not fit the descriptor's fields. Messages name offsets, codes
    and limits, never the input itself. It subclasses :class:`ValueError`.

    >>> from lvtypedesc import TypeDescError, parse_type_descriptor
    >>> try:
    ...     parse_type_descriptor(bytes.fromhex("00040099"))
    ... except TypeDescError as exc:
    ...     print(exc)
    unknown type code 0x99 at offset 0
    """


TypeDescError.__module__ = "lvtypedesc"

_NAME_LIMIT = 40


def type_name(value: object) -> str:
    """The type name of ``value`` for a message, cut to 40 characters."""
    name = type(value).__name__
    return name if len(name) <= _NAME_LIMIT else name[:_NAME_LIMIT] + "..."
