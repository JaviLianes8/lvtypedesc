"""Check that the values in one node fit the descriptor fields that hold them.

Every function that takes a tree runs these checks, so ``to_bytes``, ``describe`` and
``pretty`` accept exactly the same trees.
"""

from __future__ import annotations

from ._codes import Category, classify
from ._errors import TypeDescError, type_name
from ._model import VARIABLE, Array, Boolean, Cluster, LVString, Scalar, TypeDesc
from ._nodes import FixedPoint, LVEnum, LVVariant, PhysicalQuantity, Refnum, Waveform
from ._readers import U32_VARIABLE

CATEGORY: tuple[tuple[type[TypeDesc], Category], ...] = (
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
OPAQUE = (FixedPoint, Refnum, Waveform)


def category(node: TypeDesc) -> Category | None:
    """The category of the node's class, or None for the bare base class."""
    for cls, found in CATEGORY:
        if isinstance(node, cls):
            return found
    return None


def pstr(text: str, what: str) -> bytes:
    """Encode ``text`` as a Pascal string, or raise if it cannot be one."""
    try:
        raw = text.encode("latin-1")
    except UnicodeEncodeError:
        raise TypeDescError(f"{what} holds a character outside Latin-1") from None
    if len(raw) > 0xFF:
        raise TypeDescError(f"{what} of {len(raw)} bytes is longer than 255")
    return bytes((len(raw),)) + raw


def _size(value: int, what: str) -> None:
    if value != VARIABLE and not 0 <= value < U32_VARIABLE:
        raise TypeDescError(f"{what} must be VARIABLE or 0 to {U32_VARIABLE - 1}")


def _code(node: TypeDesc, wanted: Category) -> None:
    kind = classify(node.code) if 0 <= node.code <= 0xFF else None
    shown = f"0x{node.code:02x}" if 0 <= node.code <= 0xFFFF else "out of range"
    if kind is None or kind[0] is not wanted:
        raise TypeDescError(f"code {shown} does not fit a {type_name(node)} node")
    if node.name != kind[1]:
        raise TypeDescError(f"name does not match code {shown} (expected {kind[1]})")


def check_values(node: TypeDesc, wanted: Category) -> None:
    """Raise TypeDescError when a value of ``node`` cannot be written as a descriptor."""
    _code(node, wanted)
    if not 0 <= node.flags <= 0xFF:
        raise TypeDescError("flags must be 0 to 255")
    if node.label is not None:
        if isinstance(node, OPAQUE):
            raise TypeDescError(f"a {type_name(node)} keeps its name inside payload")
        pstr(node.label, "label")
    if isinstance(node, LVString):
        _size(node.size, "size")
    elif isinstance(node, Array):
        for dimension in node.dimensions:
            _size(dimension, "dimension")
    elif isinstance(node, LVEnum):
        for item in node.items:
            pstr(item, "item")
    elif isinstance(node, PhysicalQuantity):
        for base, exponent in node.units:
            if not 0 <= base <= 0xFFFF or not -0x8000 <= exponent <= 0x7FFF:
                raise TypeDescError("unit base must be 0 to 65535 and exponent -32768 to 32767")
