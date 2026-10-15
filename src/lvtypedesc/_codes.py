"""The type codes this library understands, and the family each one belongs to.

The values follow NI's published "Type Descriptors" page of the LabVIEW manual (see the
README for the link), checked against descriptors LabVIEW 2026 wrote on a real machine.
NI notes the codes may change between versions, so they live in this one table.
"""

from __future__ import annotations

from enum import Enum, IntEnum


class TypeCode(IntEnum):
    """Every raw type code this library recognises, by name.

    The label used in output comes from :func:`known_codes` (``BOOLEAN16`` is labelled
    ``Boolean16``, ``ENUM_U8`` is ``EnumU8``).

    >>> from lvtypedesc import TypeCode
    >>> TypeCode.DBL, int(TypeCode.CLUSTER)
    (<TypeCode.DBL: 10>, 80)
    """

    I8 = 0x01
    I16 = 0x02
    I32 = 0x03
    I64 = 0x04
    U8 = 0x05
    U16 = 0x06
    U32 = 0x07
    U64 = 0x08
    SGL = 0x09
    DBL = 0x0A
    EXT = 0x0B
    CSG = 0x0C
    CDB = 0x0D
    CXT = 0x0E
    ENUM_U8 = 0x15
    ENUM_U16 = 0x16
    ENUM_U32 = 0x17
    SGL_UNIT = 0x19
    DBL_UNIT = 0x1A
    EXT_UNIT = 0x1B
    CSG_UNIT = 0x1C
    CDB_UNIT = 0x1D
    CXT_UNIT = 0x1E
    BOOLEAN16 = 0x20
    BOOLEAN = 0x21
    STRING = 0x30
    PATH = 0x32
    PICTURE = 0x33
    ARRAY = 0x40
    CLUSTER = 0x50
    VARIANT = 0x53
    WAVEFORM = 0x54
    FXP = 0x5F
    REFNUM = 0x70


class Category(Enum):
    """The structural family a type code belongs to.

    >>> from lvtypedesc import Category
    >>> Category.ENUM.value
    'enum'
    """

    SCALAR = "scalar"
    ENUM = "enum"
    QUANTITY = "quantity"
    BOOLEAN = "boolean"
    STRING = "string"
    ARRAY = "array"
    CLUSTER = "cluster"
    VARIANT = "variant"
    WAVEFORM = "waveform"
    FXP = "fxp"
    REFNUM = "refnum"


_SCALARS = (
    *("I8", "I16", "I32", "I64", "U8", "U16", "U32", "U64"),
    *("SGL", "DBL", "EXT", "CSG", "CDB", "CXT"),
)

TABLE: dict[int, tuple[Category, str]] = {
    **{code: (Category.SCALAR, name) for code, name in enumerate(_SCALARS, start=0x01)},
    0x15: (Category.ENUM, "EnumU8"),
    0x16: (Category.ENUM, "EnumU16"),
    0x17: (Category.ENUM, "EnumU32"),
    0x19: (Category.QUANTITY, "SGLUnit"),
    0x1A: (Category.QUANTITY, "DBLUnit"),
    0x1B: (Category.QUANTITY, "EXTUnit"),
    0x1C: (Category.QUANTITY, "CSGUnit"),
    0x1D: (Category.QUANTITY, "CDBUnit"),
    0x1E: (Category.QUANTITY, "CXTUnit"),
    0x20: (Category.BOOLEAN, "Boolean16"),
    0x21: (Category.BOOLEAN, "Boolean"),
    0x30: (Category.STRING, "String"),
    0x32: (Category.STRING, "Path"),
    0x33: (Category.STRING, "Picture"),
    0x40: (Category.ARRAY, "Array"),
    0x50: (Category.CLUSTER, "Cluster"),
    0x53: (Category.VARIANT, "Variant"),
    0x54: (Category.WAVEFORM, "Waveform"),
    0x5F: (Category.FXP, "FXP"),
    0x70: (Category.REFNUM, "Refnum"),
}

# Codes LabVIEW uses whose layout is not documented or not consistent enough to parse
# honestly: the parser refuses them by name instead of with a bare "unknown code".
UNSUPPORTED_NAMES: dict[int, str] = {
    0x18: "EnumU64",
    0xF1: "Typedef",
}


def classify(code: int) -> tuple[Category, str] | None:
    """Map a type code to its category and name, or None if out of scope."""
    return TABLE.get(code)


def known_codes() -> list[tuple[int, str, Category]]:
    """Return every recognised ``(code, name, category)`` row, sorted by code.

    >>> from lvtypedesc import known_codes
    >>> known_codes()[0]
    (1, 'I8', <Category.SCALAR: 'scalar'>)
    >>> [row[1] for row in known_codes() if row[0] in (0x16, 0x21)]
    ['EnumU16', 'Boolean']
    """
    return [(code, name, category) for code, (category, name) in sorted(TABLE.items())]
