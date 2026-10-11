"""The documented type codes this library understands.

The names and values follow the common LabVIEW type descriptor table. NI warns
that these codes may change between LabVIEW versions, so they are kept in one
place rather than scattered through the parser.
"""

from __future__ import annotations

from enum import Enum

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

# Recognised by LabVIEW but outside this library's scope. Listed so the parser
# can refuse them with an honest message instead of a bare "unknown code".
UNSUPPORTED_NAMES: dict[int, str] = {
    0x15: "EnumU8",
    0x16: "EnumU16",
    0x17: "EnumU32",
    0x53: "Variant",
    0x54: "Waveform",
    0x70: "Refnum",
}


class Category(Enum):
    """The structural family a type code belongs to."""

    SCALAR = "scalar"
    BOOLEAN = "boolean"
    STRING = "string"
    ARRAY = "array"
    CLUSTER = "cluster"


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
    return None
