"""Parse LabVIEW type-descriptor byte strings into a readable, typed schema."""

from __future__ import annotations

from ._codes import Category
from ._errors import TypeDescError
from ._model import (
    VARIABLE,
    Array,
    Boolean,
    Cluster,
    LVString,
    Scalar,
    TypeDesc,
    describe,
)
from ._parser import parse_type_descriptor

__version__ = "0.1.0"

__all__ = [
    "VARIABLE",
    "Array",
    "Boolean",
    "Category",
    "Cluster",
    "LVString",
    "Scalar",
    "TypeDesc",
    "TypeDescError",
    "describe",
    "parse_type_descriptor",
]
