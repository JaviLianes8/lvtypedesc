"""Render a parsed type descriptor as an indented, multi-line tree.

This complements the one-line :func:`describe`. It is meant for reading a nested
descriptor at a glance, so it spells out ranks, dimensions and field positions.
"""

from __future__ import annotations

from ._model import (
    VARIABLE,
    Array,
    Cluster,
    FixedPoint,
    LVString,
    Refnum,
    TypeDesc,
)

_STEP = "  "


def pretty(node: TypeDesc) -> str:
    """Return a multi-line, indented rendering of ``node`` and its children."""
    return "\n".join(_lines(node, 0))


def _dim(value: int) -> str:
    return "variable" if value == VARIABLE else str(value)


def _lines(node: TypeDesc, depth: int) -> list[str]:
    pad = _STEP * depth
    if isinstance(node, Array):
        dims = ", ".join(_dim(d) for d in node.dimensions)
        head = f"{pad}Array (rank {node.rank}, dims [{dims}])"
        return [head, *_lines(node.element, depth + 1)]
    if isinstance(node, Cluster):
        head = f"{pad}Cluster ({len(node.fields)} fields)"
        out = [head]
        for index, child in enumerate(node.fields):
            label = f"{_STEP * (depth + 1)}[{index}]"
            child_lines = _lines(child, depth + 2)
            first = child_lines[0].lstrip()
            out.append(f"{label} {first}")
            out.extend(child_lines[1:])
        return out
    if isinstance(node, LVString):
        size = "variable" if node.size == VARIABLE else f"{node.size} bytes"
        return [f"{pad}{node.name} (size {size})"]
    if isinstance(node, Refnum):
        return [f"{pad}Refnum (subtype 0x{node.subtype:02x})"]
    if isinstance(node, FixedPoint):
        return [f"{pad}FXP ({len(node.payload)}-byte payload)"]
    return [f"{pad}{node.name}"]
