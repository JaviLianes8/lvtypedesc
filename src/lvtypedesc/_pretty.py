"""Render a typed tree as an indented, multi-line tree.

This complements the one-line :func:`describe`: it spells out ranks, dimensions, field
positions, enum items and element names. Names and items are shown as Python string
literals, so a control character in them can never break the layout.
"""

from __future__ import annotations

from ._check import check_tree
from ._describe import leaf_text
from ._model import VARIABLE, Array, Cluster, LVString, TypeDesc
from ._nodes import FixedPoint, LVEnum

_STEP = "  "


def pretty(node: TypeDesc) -> str:
    """Return a multi-line, indented rendering of ``node`` and its children.

    >>> from lvtypedesc import parse_type_descriptor, pretty
    >>> data = bytes.fromhex("0014 0050 0002 0006 4003 016E 0008 4021 026F 6B00")
    >>> print(pretty(parse_type_descriptor(data)))
    Cluster (2 fields)
      [0] I32 'n'
      [1] Boolean 'ok'
    """
    check_tree(node)
    return "\n".join(_lines(node, 0))


def _dim(value: int) -> str:
    return "variable" if value == VARIABLE else str(value)


def _head(node: TypeDesc) -> str:
    if isinstance(node, Array):
        dims = ", ".join(_dim(d) for d in node.dimensions)
        text = f"Array (rank {node.rank}, dims [{dims}])"
    elif isinstance(node, Cluster):
        text = f"Cluster ({len(node.fields)} fields)"
    elif isinstance(node, LVString):
        size = "variable" if node.size == VARIABLE else f"{node.size} bytes"
        text = f"{node.name} (size {size})"
    elif isinstance(node, LVEnum):
        text = f"{node.name} ({len(node.items)} items: {', '.join(map(repr, node.items))})"
    elif isinstance(node, FixedPoint):
        text = f"FXP ({len(node.payload)}-byte payload)"
    else:
        text = leaf_text(node) or node.name
    return text if node.label is None else f"{text} {node.label!r}"


def _lines(node: TypeDesc, depth: int) -> list[str]:
    pad = _STEP * depth
    out = [pad + _head(node)]
    if isinstance(node, Array):
        out.extend(_lines(node.element, depth + 1))
    elif isinstance(node, Cluster):
        for index, child in enumerate(node.fields):
            child_lines = _lines(child, depth + 2)
            out.append(f"{_STEP * (depth + 1)}[{index}] {child_lines[0].lstrip()}")
            out.extend(child_lines[1:])
    return out
