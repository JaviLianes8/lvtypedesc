"""Recursive descent over a LabVIEW type descriptor byte string.

Layout of the common types, all big-endian:

- header: a 16-bit length (bytes in this descriptor, including the length) and a
  16-bit type-code word whose low byte is the type code.
- scalar, boolean: header only.
- string, path, picture: header plus a 32-bit size word (0xFFFFFFFF = variable).
- array: header, a 16-bit dimension count, one 32-bit size per dimension, then
  the element descriptor.
- cluster: header, a 16-bit field count, then that many descriptors in order.
- fxp, refnum: header plus a type-specific payload kept as raw bytes, because its
  internal layout is version-specific and not fully documented.
"""

from __future__ import annotations

from ._codes import UNSUPPORTED_NAMES, Category, classify
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


def parse_type_descriptor(data: bytes) -> TypeDesc:
    """Parse the leading type descriptor in ``data`` into a typed tree.

    Trailing bytes (such as the flattened data that follows a descriptor) are
    ignored. Raises :class:`TypeDescError` on truncated or unsupported input.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise TypeDescError("expected bytes")
    node, _ = _parse(bytes(data), 0)
    return node


def _u16(data: bytes, offset: int) -> int:
    if offset + 2 > len(data):
        raise TypeDescError(f"truncated: need 2 bytes at offset {offset}")
    return int.from_bytes(data[offset : offset + 2], "big")


def _u32(data: bytes, offset: int) -> int:
    if offset + 4 > len(data):
        raise TypeDescError(f"truncated: need 4 bytes at offset {offset}")
    return int.from_bytes(data[offset : offset + 4], "big")


def _parse(data: bytes, offset: int) -> tuple[TypeDesc, int]:
    length = _u16(data, offset)
    code = _u16(data, offset + 2) & 0xFF
    end = offset + length
    if length < _HEADER:
        raise TypeDescError(f"length {length} too small at offset {offset}")
    if end > len(data):
        raise TypeDescError(f"descriptor at offset {offset} runs past the input")

    kind = classify(code)
    if kind is None:
        name = UNSUPPORTED_NAMES.get(code)
        detail = f"unsupported type {name}" if name else "unknown type code"
        raise TypeDescError(f"{detail} 0x{code:02x} at offset {offset}")

    category, name = kind
    if category is Category.SCALAR:
        return Scalar(code, name), end
    if category is Category.BOOLEAN:
        return Boolean(code, name), end
    if category is Category.STRING:
        return _parse_string(data, offset, end, code, name), end
    if category is Category.ARRAY:
        return _parse_array(data, offset, code, name), end
    if category is Category.CLUSTER:
        return _parse_cluster(data, offset, code, name), end
    if category is Category.FXP:
        return FixedPoint(code, name, payload=data[offset + _HEADER : end]), end
    return _parse_refnum(data, offset, end, code, name), end


def _parse_string(data: bytes, offset: int, end: int, code: int, name: str) -> LVString:
    if end - offset >= _HEADER + 4:
        raw = _u32(data, offset + _HEADER)
        size = VARIABLE if raw == _U32_VARIABLE else raw
    else:
        size = VARIABLE
    return LVString(code, name, size=size)


def _parse_array(data: bytes, offset: int, code: int, name: str) -> Array:
    rank = _u16(data, offset + _HEADER)
    pos = offset + _HEADER + 2
    dims: list[int] = []
    for _ in range(rank):
        size = _u32(data, pos)
        dims.append(VARIABLE if size == _U32_VARIABLE else size)
        pos += 4
    element, _ = _parse(data, pos)
    return Array(code, name, element=element, dimensions=tuple(dims))


def _parse_cluster(data: bytes, offset: int, code: int, name: str) -> Cluster:
    count = _u16(data, offset + _HEADER)
    pos = offset + _HEADER + 2
    fields: list[TypeDesc] = []
    for _ in range(count):
        child, pos = _parse(data, pos)
        fields.append(child)
    return Cluster(code, name, fields=tuple(fields))


def _parse_refnum(data: bytes, offset: int, end: int, code: int, name: str) -> Refnum:
    payload = data[offset + _HEADER : end]
    subtype = _u16(data, offset + _HEADER) if end - offset >= _HEADER + 2 else 0
    return Refnum(code, name, subtype=subtype, payload=payload)
