"""Parse LabVIEW type descriptors into a typed tree, render them, and write them back.

>>> import lvtypedesc
>>> node = lvtypedesc.parse_type_descriptor(bytes.fromhex("0004 0003"))
>>> lvtypedesc.describe(node), lvtypedesc.to_bytes(node).hex()
('I32', '00040003')

``VARIABLE`` (-1) stands for a size the descriptor leaves open, and ``MAX_DEPTH`` (64) is
the deepest nesting of arrays and clusters every function accepts:

>>> from lvtypedesc import MAX_DEPTH, VARIABLE
>>> lvtypedesc.parse_type_descriptor(bytes.fromhex("00080030FFFFFFFF")).size == VARIABLE
True
>>> MAX_DEPTH
64
"""

from __future__ import annotations

from ._codes import Category, TypeCode, known_codes
from ._describe import describe
from ._emit import to_bytes
from ._errors import TypeDescError
from ._model import (
    MAX_DEPTH,
    VARIABLE,
    Array,
    Boolean,
    Cluster,
    LVString,
    Scalar,
    TypeDesc,
)
from ._nodes import FixedPoint, LVEnum, LVVariant, PhysicalQuantity, Refnum, Waveform
from ._parser import parse_type_descriptor
from ._pretty import pretty

__version__ = "1.0.0"

__all__ = [
    "MAX_DEPTH",
    "VARIABLE",
    "Array",
    "Boolean",
    "Category",
    "Cluster",
    "FixedPoint",
    "LVEnum",
    "LVString",
    "LVVariant",
    "PhysicalQuantity",
    "Refnum",
    "Scalar",
    "TypeCode",
    "TypeDesc",
    "TypeDescError",
    "Waveform",
    "describe",
    "known_codes",
    "parse_type_descriptor",
    "pretty",
    "to_bytes",
]
