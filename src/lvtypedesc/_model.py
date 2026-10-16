"""The typed tree a parsed type descriptor becomes: the base node and the containers."""

from __future__ import annotations

from dataclasses import dataclass, field

VARIABLE = -1
"""A dimension or string size that the descriptor does not fix.

LabVIEW writes it as ``0xFFFFFFFF``; the actual size travels with the flattened data.

>>> from lvtypedesc import VARIABLE, parse_type_descriptor
>>> parse_type_descriptor(bytes.fromhex("00080030FFFFFFFF")).size == VARIABLE
True
"""

MAX_DEPTH = 64
"""The deepest nesting of arrays and clusters any function accepts.

Real LabVIEW types stay far below it; deeper input raises :class:`TypeDescError`
instead of exhausting the interpreter's stack.

>>> from lvtypedesc import MAX_DEPTH
>>> MAX_DEPTH
64
"""

# The high byte of the code word that marks a descriptor followed by a name.
HAS_LABEL = 0x40


@dataclass(frozen=True)
class TypeDesc:
    """Base node: ``code`` is the type code, ``name`` its label in :func:`known_codes`.

    ``label`` is the name LabVIEW appends to a descriptor (a control or cluster element
    name), or None. ``flags`` is the high byte of the type-code word, which LabVIEW
    reserves; it is kept for exact re-emission and, as NI advises, ignored by equality.

    >>> from lvtypedesc import Scalar, TypeDesc
    >>> node = Scalar(0x03, "I32", label="count")
    >>> isinstance(node, TypeDesc), node == Scalar(0x03, "I32", label="count", flags=0x40)
    (True, True)
    """

    code: int
    name: str
    label: str | None = field(default=None, kw_only=True)
    flags: int = field(default=0, kw_only=True, compare=False)


@dataclass(frozen=True)
class Scalar(TypeDesc):
    """A fixed-width numeric type, for example I32 or DBL.

    >>> from lvtypedesc import Scalar, parse_type_descriptor
    >>> parse_type_descriptor(bytes.fromhex("0004000A")) == Scalar(0x0A, "DBL")
    True
    """


@dataclass(frozen=True)
class Boolean(TypeDesc):
    """A LabVIEW Boolean (``0x21``) or the old 16-bit Boolean (``0x20``).

    >>> from lvtypedesc import Boolean, parse_type_descriptor
    >>> parse_type_descriptor(bytes.fromhex("00040021"))
    Boolean(code=33, name='Boolean', label=None, flags=0)
    """


@dataclass(frozen=True)
class LVString(TypeDesc):
    """A string, path or picture.

    ``size`` is the descriptor's 32-bit size word: ``VARIABLE`` for ``0xFFFFFFFF``
    (what LabVIEW writes), otherwise a fixed byte count.

    >>> from lvtypedesc import LVString, parse_type_descriptor
    >>> parse_type_descriptor(bytes.fromhex("00080032FFFFFFFF")) == LVString(0x32, "Path")
    True
    """

    size: int = VARIABLE


@dataclass(frozen=True)
class Array(TypeDesc):
    """An n-dimensional array of one element type.

    ``dimensions`` holds one size per dimension, ``VARIABLE`` when not fixed.

    >>> from lvtypedesc import Array, parse_type_descriptor
    >>> node = parse_type_descriptor(bytes.fromhex("00120040 0002 FFFFFFFF FFFFFFFF 00040021"))
    >>> isinstance(node, Array), node.rank, node.element.name
    (True, 2, 'Boolean')
    """

    element: TypeDesc
    dimensions: tuple[int, ...] = ()

    @property
    def rank(self) -> int:
        """The number of dimensions.

        >>> from lvtypedesc import Array, Scalar
        >>> Array(0x40, "Array", element=Scalar(0x03, "I32"), dimensions=(-1,)).rank
        1
        """
        return len(self.dimensions)


@dataclass(frozen=True)
class Cluster(TypeDesc):
    """An ordered group of element types.

    >>> from lvtypedesc import Cluster, parse_type_descriptor
    >>> node = parse_type_descriptor(bytes.fromhex("000E 0050 0002 0004 0002 0004 0007"))
    >>> isinstance(node, Cluster), [f.name for f in node.fields]
    (True, ['I16', 'U32'])
    """

    fields: tuple[TypeDesc, ...] = ()
