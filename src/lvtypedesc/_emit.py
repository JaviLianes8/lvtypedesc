"""Write a typed tree back as a canonical nested type descriptor."""

from __future__ import annotations

from ._check import check_tree
from ._errors import TypeDescError
from ._model import HAS_LABEL, VARIABLE, Array, Cluster, LVString, TypeDesc
from ._nodes import LVEnum, PhysicalQuantity
from ._readers import U32_VARIABLE
from ._values import OPAQUE, pstr

_MAX_LENGTH = 0xFFFF


def to_bytes(node: TypeDesc) -> bytes:
    """Write ``node`` as a nested type descriptor, the inverse of parsing.

    ``parse_type_descriptor(to_bytes(node)) == node`` for every valid tree, and
    ``to_bytes`` reproduces any descriptor LabVIEW wrote in its canonical form: names
    as Pascal strings at an even offset, zero padding, nothing after the fields.
    Raises :class:`TypeError` for a malformed tree and :class:`TypeDescError` for one
    that cannot be written (a code that does not match the node's class, a name that
    does not match the code, a value out of range, more than 65535 bytes).

    >>> from lvtypedesc import Cluster, Scalar, to_bytes
    >>> tree = Cluster(0x50, "Cluster", fields=(Scalar(0x03, "I32", label="n"),))
    >>> to_bytes(tree).hex(" ", -2)
    '000c 0050 0001 0006 4003 016e'
    """
    check_tree(node)
    return _emit(node)


def _emit(node: TypeDesc) -> bytes:
    body = _body(node)
    flags = node.flags
    if node.label is not None:
        body += b"\x00" * (len(body) % 2) + pstr(node.label, "label")
        flags |= HAS_LABEL
    if not isinstance(node, OPAQUE):  # opaque payloads are kept exactly as read
        body += b"\x00" * (len(body) % 2)  # a type string is a sequence of 16-bit words
    length = 4 + len(body)
    if length > _MAX_LENGTH:
        raise TypeDescError(f"descriptor of {length} bytes does not fit the 16-bit length")
    return _u16(length) + bytes((flags, node.code)) + body


def _body(node: TypeDesc) -> bytes:
    if isinstance(node, LVString):
        return _size(node.size)
    if isinstance(node, Array):
        dims = b"".join(_size(d) for d in node.dimensions)
        return _u16(node.rank) + dims + _emit(node.element)
    if isinstance(node, Cluster):
        return _u16(len(node.fields)) + b"".join(_emit(f) for f in node.fields)
    if isinstance(node, LVEnum):
        return _u16(len(node.items)) + b"".join(pstr(item, "item") for item in node.items)
    if isinstance(node, PhysicalQuantity):
        pairs = (_u16(base) + exp.to_bytes(2, "big", signed=True) for base, exp in node.units)
        return _u16(len(node.units)) + b"".join(pairs)
    if isinstance(node, OPAQUE):
        return node.payload
    return b""


def _u16(value: int) -> bytes:
    return value.to_bytes(2, "big")


def _size(value: int) -> bytes:
    return (U32_VARIABLE if value == VARIABLE else value).to_bytes(4, "big")
