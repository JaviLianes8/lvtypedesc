"""The typed tree a parsed type descriptor becomes, and a readable rendering."""

from __future__ import annotations

from dataclasses import dataclass, field

# A dimension or string whose size is not fixed in the descriptor. LabVIEW
# stores this as 0xFFFFFFFF; the actual size lives in the flattened data.
VARIABLE = -1


@dataclass(frozen=True)
class TypeDesc:
    """Base node. ``code`` is the raw type code, ``name`` its documented label."""

    code: int
    name: str


@dataclass(frozen=True)
class Scalar(TypeDesc):
    """A fixed-width numeric type, for example I32 or DBL."""


@dataclass(frozen=True)
class Boolean(TypeDesc):
    """A LabVIEW boolean."""


@dataclass(frozen=True)
class LVString(TypeDesc):
    """A variable-length string, path or picture.

    ``size`` is the descriptor's 32-bit size word: ``VARIABLE`` when the size is
    not fixed (``0xFFFFFFFF``), otherwise the fixed byte count.
    """

    size: int = VARIABLE


@dataclass(frozen=True)
class Array(TypeDesc):
    """An n-dimensional array of one element type."""

    element: TypeDesc
    dimensions: tuple[int, ...] = field(default_factory=tuple)

    @property
    def rank(self) -> int:
        """The number of dimensions."""
        return len(self.dimensions)


@dataclass(frozen=True)
class Cluster(TypeDesc):
    """An ordered group of named-by-position field types."""

    fields: tuple[TypeDesc, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class FixedPoint(TypeDesc):
    """A LabVIEW fixed-point number (FXP).

    The word, delta and offset encoding inside an FXP descriptor is
    version-specific and not fully documented, so the type-specific bytes are
    preserved verbatim in ``payload`` rather than parsed into fields. This keeps
    round-trip exact without inventing an interpretation.
    """

    payload: bytes = b""


@dataclass(frozen=True)
class Refnum(TypeDesc):
    """A LabVIEW refnum (a handle to a queue, VISA resource, control, ...).

    ``subtype`` is the first payload word, which identifies the refnum kind. Its
    meaning is only partly documented, so it is surfaced best-effort and the full
    type-specific bytes are kept in ``payload`` for exact round-trip.
    """

    subtype: int = 0
    payload: bytes = b""


def describe(node: TypeDesc) -> str:
    """Render a parsed descriptor as a compact, readable one-line string."""
    if isinstance(node, Array):
        return f"{node.rank}D Array of {describe(node.element)}"
    if isinstance(node, Cluster):
        inner = ", ".join(describe(f) for f in node.fields)
        return f"Cluster {{ {inner} }}"
    if isinstance(node, Refnum):
        return f"Refnum(subtype=0x{node.subtype:02x})"
    return node.name
