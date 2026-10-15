"""Recursive descent over a LabVIEW type descriptor in its nested (type string) form.

Layout, all big-endian, as NI documents it for Variant To Flattened String:

- header: a 16-bit length (of the whole descriptor, header included) and a 16-bit
  type-code word; the low byte is the type code, the high byte is reserved by LabVIEW
  (bit 0x40 marks an appended name).
- string, path, picture: a 32-bit size word (0xFFFFFFFF = variable).
- array: a 16-bit dimension count, one 32-bit size per dimension, the element descriptor.
- cluster: a 16-bit element count, then the element descriptors in order.
- enum: a 16-bit item count, then the item names as Pascal strings.
- physical quantity: a 16-bit count, then (16-bit base index, signed 16-bit exponent).
- fixed-point, refnum, waveform: version-specific bytes, kept verbatim.
- name: a Pascal string at the next even offset, padded to an even length.
"""

from __future__ import annotations

from dataclasses import replace

from ._codes import UNSUPPORTED_NAMES, Category, classify
from ._errors import TypeDescError, type_name
from ._model import HAS_LABEL, MAX_DEPTH, Array, Boolean, Cluster, LVString, Scalar, TypeDesc
from ._nodes import FixedPoint, LVEnum, LVVariant, PhysicalQuantity, Refnum, Waveform
from ._readers import Fields, header, size_word

_OPAQUE = {Category.FXP: FixedPoint, Category.REFNUM: Refnum, Category.WAVEFORM: Waveform}


def parse_type_descriptor(data: bytes | bytearray | memoryview) -> TypeDesc:
    """Parse the leading type descriptor in ``data`` into a typed tree.

    Bytes after the descriptor (such as the flattened data that follows it) are
    ignored. Raises :class:`TypeDescError` on truncated, malformed or unsupported
    input and :class:`TypeError` when ``data`` is not bytes-like.

    >>> from lvtypedesc import parse_type_descriptor, describe
    >>> node = parse_type_descriptor(bytes.fromhex("000E 0040 0001 FFFFFFFF 0004 000A"))
    >>> describe(node), node.dimensions
    ('1D Array of DBL', (-1,))
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError(f"expected bytes, bytearray or memoryview, not {type_name(data)}")
    raw = bytes(data[:0xFFFF])  # no descriptor is longer, whatever follows it
    node, _ = _parse(raw, 0, len(raw), 1)
    return node


def _parse(data: bytes, offset: int, limit: int, depth: int) -> tuple[TypeDesc, int]:
    end, code, flags = header(data, offset, limit)
    kind = classify(code)
    if kind is None:
        name = UNSUPPORTED_NAMES.get(code)
        detail = f"unsupported type {name}" if name else "unknown type code"
        raise TypeDescError(f"{detail} 0x{code:02x} at offset {offset}")
    category, name = kind
    if category in _OPAQUE:
        payload = data[offset + 4 : end]
        return _OPAQUE[category](code, name, payload=payload, flags=flags), end
    fields = Fields(data, offset, end)
    node = _structured(fields, category, code, name, depth)
    label = fields.label() if flags & HAS_LABEL else None
    return _with(node, label, flags), end


def _with(node: TypeDesc, label: str | None, flags: int) -> TypeDesc:
    return replace(node, label=label, flags=flags)


def _structured(fields: Fields, category: Category, code: int, name: str, depth: int) -> TypeDesc:
    if category is Category.SCALAR:
        return Scalar(code, name)
    if category is Category.BOOLEAN:
        return Boolean(code, name)
    if category is Category.VARIANT:
        return LVVariant(code, name)
    if category is Category.STRING:
        return LVString(code, name, size=size_word(fields.u32()))
    if category is Category.ENUM:
        count = fields.u16()
        return LVEnum(code, name, items=tuple(fields.pstr() for _ in range(count)))
    if category is Category.QUANTITY:
        count = fields.u16()
        units = tuple((fields.u16(), fields.i16()) for _ in range(count))
        return PhysicalQuantity(code, name, units=units)
    if category is Category.ARRAY:
        rank = fields.u16()
        dims = tuple(size_word(fields.u32()) for _ in range(rank))
        element = _child(fields, depth)
        return Array(code, name, element=element, dimensions=dims)
    count = fields.u16()
    return Cluster(code, name, fields=tuple(_child(fields, depth) for _ in range(count)))


def _child(fields: Fields, depth: int) -> TypeDesc:
    if depth >= MAX_DEPTH:
        raise TypeDescError(f"descriptor nested deeper than {MAX_DEPTH} levels")
    node, fields.pos = _parse(fields.data, fields.pos, fields.end, depth + 1)
    return node
