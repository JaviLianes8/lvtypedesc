"""The type codes this library understands.

The names and values follow the community-documented LabVIEW type-descriptor
table (see the project README for provenance). These codes are not an official
NI byte specification and can change between LabVIEW versions, so they are kept
in one place rather than scattered through the parser.
"""

from __future__ import annotations

from enum import Enum, IntEnum


class TypeCode(IntEnum):
    """Every raw type code this library recognises, by name.

    Member names are Python identifiers. The human label used in output comes
    from the name tables below (for example ``BOOLEAN16`` is labelled
    ``Boolean16``).
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
    BOOLEAN16 = 0x20
    BOOLEAN = 0x21
    STRING = 0x30
    PATH = 0x32
    PICTURE = 0x33
    ARRAY = 0x40
    CLUSTER = 0x50
    FXP = 0x5F
    REFNUM = 0x70


SCALAR_NAMES: dict[int, str] = {
    0x01: "I8",
    0x02: "I16",
    0x03: "I32",
    0x04: "I64",
    0x05: "U8",
    0x06: "U16",
    0x07: "U32",
    0x08: "U64",
    0x09: "SGL",
    0x0A: "DBL",
    0x0B: "EXT",
    0x0C: "CSG",
    0x0D: "CDB",
    0x0E: "CXT",
}

BOOLEAN_NAMES: dict[int, str] = {
    0x20: "Boolean16",
    0x21: "Boolean",
}

STRING_NAMES: dict[int, str] = {
    0x30: "String",
    0x32: "Path",
    0x33: "Picture",
}

ARRAY_CODE = 0x40
CLUSTER_CODE = 0x50
FXP_CODE = 0x5F
REFNUM_CODE = 0x70

# Recognised by LabVIEW but outside this library's scope. Their payloads are not
# documented well enough to parse honestly, so the parser refuses them with a
# named message instead of a bare "unknown code".
UNSUPPORTED_NAMES: dict[int, str] = {
    0x15: "EnumU8",
    0x16: "EnumU16",
    0x17: "EnumU32",
    0x53: "Variant",
    0x54: "Waveform",
}


class Category(Enum):
    """The structural family a type code belongs to."""

    SCALAR = "scalar"
    BOOLEAN = "boolean"
    STRING = "string"
    ARRAY = "array"
    CLUSTER = "cluster"
    FXP = "fxp"
    REFNUM = "refnum"


def classify(code: int) -> tuple[Category, str] | None:
    """Map a type code to its category and name, or None if out of scope."""
    if code in SCALAR_NAMES:
        return Category.SCALAR, SCALAR_NAMES[code]
    if code in BOOLEAN_NAMES:
        return Category.BOOLEAN, BOOLEAN_NAMES[code]
    if code in STRING_NAMES:
        return Category.STRING, STRING_NAMES[code]
    if code == ARRAY_CODE:
        return Category.ARRAY, "Array"
    if code == CLUSTER_CODE:
        return Category.CLUSTER, "Cluster"
    if code == FXP_CODE:
        return Category.FXP, "FXP"
    if code == REFNUM_CODE:
        return Category.REFNUM, "Refnum"
    return None


def known_codes() -> list[tuple[int, str, Category]]:
    """Return every recognised ``(code, name, category)`` row, sorted by code."""
    rows: list[tuple[int, str, Category]] = []
    for code in range(0x100):
        kind = classify(code)
        if kind is not None:
            category, name = kind
            rows.append((code, name, category))
    return rows
