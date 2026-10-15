"""Validate a tree before rendering or emitting it, without recursion."""

from __future__ import annotations

from ._errors import TypeDescError, type_name
from ._model import MAX_DEPTH, Array, Cluster, LVString, TypeDesc
from ._nodes import FixedPoint, LVEnum, PhysicalQuantity, Refnum, Waveform
from ._values import category, check_values


def is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


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
    _expect(is_int(node.code), "code", node.code)
    _expect(is_int(node.flags), "flags", node.flags)
    _expect(isinstance(node.name, str), "name", node.name)
    _expect(node.label is None or isinstance(node.label, str), "label", node.label)
    if isinstance(node, LVString):
        _expect(is_int(node.size), "size", node.size)
    elif isinstance(node, Array):
        dims = node.dimensions
        _expect(isinstance(dims, tuple) and all(map(is_int, dims)), "dimensions", dims)
        _expect(isinstance(node.element, TypeDesc), "element", node.element)
    elif isinstance(node, Cluster):
        fields = node.fields
        ok = isinstance(fields, tuple) and all(isinstance(f, TypeDesc) for f in fields)
        _expect(ok, "fields", fields)
    elif isinstance(node, LVEnum):
        items = node.items
        ok = isinstance(items, tuple) and all(isinstance(i, str) for i in items)
        _expect(ok, "items", items)
    elif isinstance(node, PhysicalQuantity):
        units = node.units
        ok = isinstance(units, tuple) and all(
            isinstance(u, tuple) and len(u) == 2 and is_int(u[0]) and is_int(u[1]) for u in units
        )
        _expect(ok, "units", units)
    elif isinstance(node, (FixedPoint, Refnum, Waveform)):
        _expect(isinstance(node.payload, bytes), "payload", node.payload)
    check_values(node, wanted)


def children(node: TypeDesc) -> tuple[TypeDesc, ...]:
    """The direct children of a node, in order."""
    if isinstance(node, Array):
        return (node.element,)
    if isinstance(node, Cluster):
        return node.fields
    return ()


def check_tree(node: object) -> None:
    """Raise TypeError for a malformed tree, TypeDescError for one nested too deep or
    holding a value that does not fit its descriptor field."""
    _expect(isinstance(node, TypeDesc), "node", node)
    stack: list[tuple[TypeDesc, int]] = [(node, 1)]  # type: ignore[list-item]
    while stack:
        current, depth = stack.pop()
        if depth > MAX_DEPTH:
            raise TypeDescError(f"tree nested deeper than {MAX_DEPTH} levels")
        _check_node(current)
        stack.extend((child, depth + 1) for child in children(current))
