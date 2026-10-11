"""Parse LabVIEW type-descriptor byte strings into a readable, typed schema."""

from __future__ import annotations

from ._codes import Category, TypeCode, known_codes
from ._emit import to_bytes
from ._errors import TypeDescError
from ._model import (
    VARIABLE,
    Array,
    Boolean,
    Cluster,
    FixedPoint,
    LVString,
    Refnum,
    Scalar,
    TypeDesc,
    describe,
)
from ._parser import parse_type_descriptor
from ._pretty import pretty

__version__ = "0.2.0"

__all__ = [
    "VARIABLE",
    "Array",
    "Boolean",
    "Category",
    "Cluster",
    "FixedPoint",
    "LVString",
    "Refnum",
    "Scalar",
    "TypeCode",
    "TypeDesc",
    "TypeDescError",
    "describe",
    "known_codes",
    "parse_type_descriptor",
    "pretty",
    "to_bytes",
]
