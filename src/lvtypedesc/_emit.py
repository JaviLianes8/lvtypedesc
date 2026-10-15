"""Write a typed tree back as a canonical nested type descriptor."""

from __future__ import annotations

from ._check import check_tree, type_name
from ._codes import Category, classify
from ._errors import TypeDescError
from ._model import HAS_LABEL, VARIABLE, Array, Boolean, Cluster, LVString, Scalar, TypeDesc
from ._nodes import FixedPoint, LVEnum, LVVariant, PhysicalQuantity, Refnum, Waveform
from ._readers import U32_VARIABLE

_MAX_LENGTH = 0xFFFF
_CATEGORY: tuple[tuple[type[TypeDesc], Category], ...] = (
    (Scalar, Category.SCALAR),
    (Boolean, Category.BOOLEAN),
    (LVString, Category.STRING),
    (Array, Category.ARRAY),
    (Cluster, Category.CLUSTER),
    (LVEnum, Category.ENUM),
    (PhysicalQuantity, Category.QUANTITY),
    (LVVariant, Category.VARIANT),
    (FixedPoint, Category.FXP),
    (Refnum, Category.REFNUM),
    (Waveform, Category.WAVEFORM),
)
_OPAQUE = (FixedPoint, Refnum, Waveform)


def to_bytes(node: TypeDesc) -> bytes:
    """Write ``node`` as a nested type descriptor, the inverse of parsing.

    ``parse_type_descriptor(to_bytes(node)) == node`` for every valid tree, and
    ``to_bytes`` reproduces any descriptor LabVIEW wrote in its canonical form: names
    as Pascal strings at an even offset, zero padding, nothing after the fields.
    Raises :class:`TypeError` for a malformed tree and :class:`TypeDescError` for one
    that cannot be written (a code that does not match the node's class, a value out of
    range, more than 65535 bytes).

    >>> from lvtypedesc import Cluster, Scalar, to_bytes
    >>> tree = Cluster(0x50, "Cluster", fields=(Scalar(0x03, "I32", label="n"),))
    >>> to_bytes(tree).hex(" ", -2)
    '000c 0050 0001 0006 4003 016e'
    """
    check_tree(node)
    return _emit(node)


def _emit(node: TypeDesc) -> bytes:
    category = _category(node)
    kind = classify(node.code) if 0 <= node.code <= 0xFF else None
    if kind is None or kind[0] is not category:
        raise TypeDescError(f"code {_code(node.code)} does not fit a {type_name(node)} node")
    if not 0 <= node.flags <= 0xFF:
        raise TypeDescError(f"flags {_code(node.flags)} do not fit in one byte")
    body = _body(node)
    flags = node.flags
    if node.label is not None:
        if isinstance(node, _OPAQUE):
            raise TypeDescError(f"a {type_name(node)} keeps its name inside payload")
        body += b"\x00" * (len(body) % 2) + _pstr(node.label, "label")
        flags |= HAS_LABEL
    if not isinstance(node, _OPAQUE):  # opaque payloads are kept exactly as read
        body += b"\x00" * (len(body) % 2)  # a type string is a sequence of 16-bit words
    length = 4 + len(body)
    if length > _MAX_LENGTH:
        raise TypeDescError(f"descriptor of {length} bytes does not fit the 16-bit length")
    return _u16(length) + bytes((flags, node.code)) + body


def _category(node: TypeDesc) -> Category:
    for cls, category in _CATEGORY:
        if isinstance(node, cls):
            return category
    raise TypeDescError(f"cannot write a node of type {type_name(node)}")


def _body(node: TypeDesc) -> bytes:
    if isinstance(node, LVString):
        return _size(node.size, "size")
    if isinstance(node, Array):
        dims = b"".join(_size(d, "dimension") for d in node.dimensions)
        return _count(node.rank, "dimensions") + dims + _emit(node.element)
    if isinstance(node, Cluster):
        inner = b"".join(_emit(f) for f in node.fields)
        return _count(len(node.fields), "fields") + inner
    if isinstance(node, LVEnum):
        items = b"".join(_pstr(item, "item") for item in node.items)
        return _count(len(node.items), "items") + items
    if isinstance(node, PhysicalQuantity):
        pairs = b"".join(_unit(base, exp) for base, exp in node.units)
        return _count(len(node.units), "units") + pairs
    if isinstance(node, _OPAQUE):
        return node.payload
    return b""


def _code(value: int) -> str:
    return f"0x{value:02x}" if 0 <= value <= 0xFFFF else "out of range"


def _u16(value: int) -> bytes:
    return value.to_bytes(2, "big")


def _count(value: int, what: str) -> bytes:
    if value > 0xFFFF:
        raise TypeDescError(f"{value} {what} do not fit the 16-bit count")
    return _u16(value)


def _size(value: int, what: str) -> bytes:
    if value == VARIABLE:
        return U32_VARIABLE.to_bytes(4, "big")
    if not 0 <= value < U32_VARIABLE:
        raise TypeDescError(f"{what} must be VARIABLE or 0 to {U32_VARIABLE - 1}")
    return value.to_bytes(4, "big")


def _unit(base: int, exponent: int) -> bytes:
    if not 0 <= base <= 0xFFFF or not -0x8000 <= exponent <= 0x7FFF:
        raise TypeDescError("unit base must be 0 to 65535 and exponent -32768 to 32767")
    return _u16(base) + exponent.to_bytes(2, "big", signed=True)


def _pstr(text: str, what: str) -> bytes:
    try:
        raw = text.encode("latin-1")
    except UnicodeEncodeError:
        raise TypeDescError(f"{what} holds a character outside Latin-1") from None
    if len(raw) > 0xFF:
        raise TypeDescError(f"{what} of {len(raw)} bytes is longer than 255")
    return bytes((len(raw),)) + raw
