"""Validate a tree before rendering or emitting it, without recursion.

Fields must hold the exact built-in types (``int``, ``str``, ``bytes``, ``tuple``), so a
subclass that lies about its value, length or comparisons can never reach the writer.
"""

from __future__ import annotations

from ._codes import TypeCode
from ._errors import TypeDescError, type_name
from ._model import MAX_DEPTH, Array, Cluster, LVString, TypeDesc
from ._nodes import FixedPoint, LVEnum, PhysicalQuantity, Refnum, Waveform
from ._values import category, check_values

# Checked from lengths alone before any per-element work, so no tree costs more than one
# descriptor's worth of work. Every node takes at least 4 bytes, which also bounds the
# number of nodes (shared subtrees count once per place they appear).
MAX_BYTES = 0xFFFF


def is_int(value: object) -> bool:
    return type(value) is int


def _is_tuple_of(value: object, kind: type) -> bool:
    return type(value) is tuple and all(type(item) is kind for item in value)


def _expect(ok: bool, what: str, value: object) -> None:
    if not ok:
        raise TypeError(f"{what} must be {_WANTED[what]}, not {type_name(value)}")


_WANTED = {
    "code": "an int",
    "flags": "an int",
    "name": "a str",
    "label": "a str or None",
    "size": "an int",
    "dimensions": "a tuple of int",
    "items": "a tuple of str",
    "units": "a tuple of (int, int) pairs",
    "payload": "bytes",
    "fields": "a tuple of TypeDesc",
    "element": "a TypeDesc",
    "node": "a TypeDesc",
}


def _check_node(node: TypeDesc) -> None:
    wanted = category(node)
    if wanted is None:
        raise TypeError(
            f"node must be an instance of a node class such as Scalar or Cluster, "
            f"not {type_name(node)}"
        )
    _expect(is_int(node.code) or type(node.code) is TypeCode, "code", node.code)
    _expect(is_int(node.flags), "flags", node.flags)
    _expect(type(node.name) is str, "name", node.name)
    _expect(node.label is None or type(node.label) is str, "label", node.label)
    if isinstance(node, LVString):
        _expect(is_int(node.size), "size", node.size)
    elif isinstance(node, Array):
        dims = node.dimensions
        _expect(_is_tuple_of(dims, int), "dimensions", dims)
        _expect(isinstance(node.element, TypeDesc), "element", node.element)
    elif isinstance(node, Cluster):
        fields = node.fields
        ok = type(fields) is tuple and all(isinstance(f, TypeDesc) for f in fields)
        _expect(ok, "fields", fields)
    elif isinstance(node, LVEnum):
        items = node.items
        _expect(_is_tuple_of(items, str), "items", items)
    elif isinstance(node, PhysicalQuantity):
        units = node.units
        ok = type(units) is tuple and all(_is_tuple_of(u, int) and len(u) == 2 for u in units)
        _expect(ok, "units", units)
    elif isinstance(node, (FixedPoint, Refnum, Waveform)):
        _expect(type(node.payload) is bytes, "payload", node.payload)
    check_values(node, wanted)


def children(node: TypeDesc) -> tuple[TypeDesc, ...]:
    """The direct children of a node, in order."""
    if isinstance(node, Array):
        return (node.element,)
    if isinstance(node, Cluster):
        return node.fields
    return ()


def _length(value: object) -> int:
    """The length of an exact tuple, str or bytes, else 0 (the type check refuses it)."""
    return len(value) if type(value) in (tuple, str, bytes) else 0  # type: ignore[arg-type]


def least_bytes(node: TypeDesc) -> int:
    """A lower bound of the bytes ``node`` takes on its own, from lengths alone."""
    size = 4 + (1 + _length(node.label) if node.label is not None else 0)
    if isinstance(node, LVString):
        return size + 4
    if isinstance(node, Array):
        return size + 2 + 4 * _length(node.dimensions)
    if isinstance(node, Cluster):
        return size + 2
    if isinstance(node, LVEnum):
        items = node.items
        if type(items) is not tuple or len(items) > MAX_BYTES:  # refused before the sum
            return size + 2 + _length(items)
        return size + 2 + sum(1 + _length(item) for item in items)
    if isinstance(node, PhysicalQuantity):
        return size + 2 + 4 * _length(node.units)
    if isinstance(node, (FixedPoint, Refnum, Waveform)):
        return size + _length(node.payload)
    return size


def check_tree(node: object) -> None:
    """Raise TypeError for a malformed tree, TypeDescError for one nested too deep, that
    certainly needs more than 65535 bytes (shared subtrees count each time), or holding a
    value that does not fit its descriptor field."""
    _expect(isinstance(node, TypeDesc), "node", node)
    stack: list[tuple[TypeDesc, int]] = [(node, 1)]  # type: ignore[list-item]
    total = 0
    while stack:
        current, depth = stack.pop()
        total += least_bytes(current)
        if total > MAX_BYTES:
            raise TypeDescError(
                f"tree needs more than {MAX_BYTES} bytes, which does not fit the 16-bit length"
            )
        if depth > MAX_DEPTH:
            raise TypeDescError(f"tree nested deeper than {MAX_DEPTH} levels")
        _check_node(current)
        stack.extend((child, depth + 1) for child in children(current))
