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

# No writable descriptor holds more: every node takes at least 4 of its 65535 bytes.
MAX_NODES = 16384


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


def check_tree(node: object) -> None:
    """Raise TypeError for a malformed tree, TypeDescError for one nested too deep, with
    more than MAX_NODES nodes (shared subtrees count each time), or holding a value that
    does not fit its descriptor field."""
    _expect(isinstance(node, TypeDesc), "node", node)
    stack: list[tuple[TypeDesc, int]] = [(node, 1)]  # type: ignore[list-item]
    visited = 0
    while stack:
        current, depth = stack.pop()
        visited += 1
        if visited > MAX_NODES:
            raise TypeDescError(f"tree has more than {MAX_NODES} nodes")
        if depth > MAX_DEPTH:
            raise TypeDescError(f"tree nested deeper than {MAX_DEPTH} levels")
        _check_node(current)
        stack.extend((child, depth + 1) for child in children(current))
