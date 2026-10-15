"""Render a typed tree as one readable line."""

from __future__ import annotations

from ._check import check_tree
from ._model import Array, Cluster, TypeDesc
from ._nodes import LVEnum, PhysicalQuantity, Refnum, Waveform

_BASES = ("rad", "sr", "s", "m", "kg", "A", "K", "mol", "cd")
TIMESTAMP_SUBTYPE = 6


def unit_text(units: tuple[tuple[int, int], ...]) -> str:
    """Spell ``(base index, exponent)`` pairs as SI symbols, for example ``m s^-1``."""
    parts = []
    for base, exponent in units:
        symbol = _BASES[base] if 0 <= base < len(_BASES) else f"base{base}"
        parts.append(symbol if exponent == 1 else f"{symbol}^{exponent}")
    return " ".join(parts)


def leaf_text(node: TypeDesc) -> str | None:
    """The one-line text shared by :func:`describe` and ``pretty`` for special leaves."""
    if isinstance(node, LVEnum):
        return f"{node.name} ({len(node.items)} items)"
    if isinstance(node, PhysicalQuantity):
        return f"{node.name} [{unit_text(node.units)}]"
    if isinstance(node, Waveform):
        if node.subtype == TIMESTAMP_SUBTYPE:
            return "Timestamp"
        return f"Waveform(subtype=0x{node.subtype:02x})"
    if isinstance(node, Refnum):
        return f"Refnum(subtype=0x{node.subtype:02x})"
    return None


def describe(node: TypeDesc) -> str:
    """Render a parsed descriptor as a compact, readable one-line string.

    Element names (labels) are left out; :func:`pretty` shows them.

    >>> from lvtypedesc import describe, parse_type_descriptor
    >>> describe(parse_type_descriptor(bytes.fromhex("000E 0050 0002 0004 0003 0004 000A")))
    'Cluster { I32, DBL }'
    >>> describe(parse_type_descriptor(bytes.fromhex("000600540006")))
    'Timestamp'
    """
    check_tree(node)
    return _describe(node)


def _describe(node: TypeDesc) -> str:
    if isinstance(node, Array):
        return f"{node.rank}D Array of {_describe(node.element)}"
    if isinstance(node, Cluster):
        inner = ", ".join(_describe(f) for f in node.fields)
        return f"Cluster {{ {inner} }}"
    text = leaf_text(node)
    return node.name if text is None else text
