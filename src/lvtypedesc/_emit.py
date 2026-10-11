"""Re-emit a typed tree as a canonical short-form type descriptor.

``to_bytes`` is the inverse of :func:`parse_type_descriptor` for every node type
this library models. It writes the short-form descriptor (16-bit length) and
raises :class:`TypeDescError` when a tree is too large for that form, rather than
guessing the long-form layout.
"""

from __future__ import annotations

from ._errors import TypeDescError
from ._model import (
    VARIABLE,
    Array,
    Boolean,
    Cluster,
    FixedPoint,
    LVString,
    Refnum,
    Scalar,
    TypeDesc,
)

_HEADER = 4
_U32_VARIABLE = 0xFFFFFFFF
_MAX_LENGTH = 0xFFFF


def to_bytes(node: TypeDesc) -> bytes:
    """Serialise ``node`` back into a canonical short-form type descriptor."""
    body = _body(node)
    length = _HEADER + len(body)
    if length > _MAX_LENGTH:
        raise TypeDescError(f"descriptor of {length} bytes is too large for the short form")
    return _u16(length) + _u16(node.code & 0xFFFF) + body


def _body(node: TypeDesc) -> bytes:
    if isinstance(node, (Scalar, Boolean)):
        return b""
    if isinstance(node, LVString):
        size = _U32_VARIABLE if node.size == VARIABLE else node.size
        return _u32(size)
    if isinstance(node, Array):
        dims = b"".join(_u32(_U32_VARIABLE if d == VARIABLE else d) for d in node.dimensions)
        return _u16(node.rank) + dims + to_bytes(node.element)
    if isinstance(node, Cluster):
        return _u16(len(node.fields)) + b"".join(to_bytes(f) for f in node.fields)
    if isinstance(node, (FixedPoint, Refnum)):
        return node.payload
    raise TypeDescError(f"cannot serialise node of type {type(node).__name__}")


def _u16(value: int) -> bytes:
    return int(value).to_bytes(2, "big")


def _u32(value: int) -> bytes:
    return int(value).to_bytes(4, "big")
