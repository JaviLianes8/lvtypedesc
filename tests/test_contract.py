import importlib.resources

import lvtypedesc
from lvtypedesc import (
    VARIABLE,
    Array,
    Cluster,
    LVString,
    Scalar,
    describe,
    parse_type_descriptor,
)

# The public API. Add every exported name here as the library grows; this list is the
# contract and the test below fails if the module and this list disagree.
PUBLIC_API: list[str] = [
    "MAX_DEPTH",
    "LVEnum",
    "LVVariant",
    "PhysicalQuantity",
    "Waveform",
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


def test_all_lists_exactly_the_public_api() -> None:
    assert sorted(lvtypedesc.__all__) == sorted(PUBLIC_API)


def test_every_exported_name_resolves() -> None:
    for name in lvtypedesc.__all__:
        assert hasattr(lvtypedesc, name)


def test_version_is_a_three_part_string() -> None:
    parts = lvtypedesc.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_the_package_ships_type_information() -> None:
    assert importlib.resources.files("lvtypedesc").joinpath("py.typed").is_file()


def test_contract_parses_every_structural_family_into_a_typed_tree() -> None:
    """The complete promise: parse one descriptor per structural family and
    assert the full typed tree, not just a label."""

    def td(hex_bytes: str) -> bytes:
        return bytes.fromhex(hex_bytes)

    # Scalar: a DBL.
    scalar = parse_type_descriptor(td("0004 000A"))
    assert scalar == Scalar(0x0A, "DBL")

    # String: variable sized.
    text = parse_type_descriptor(td("0008 0030 FFFFFFFF"))
    assert text == LVString(0x30, "String", size=VARIABLE)

    # Array of DBL: one variable dimension, DBL element.
    array = parse_type_descriptor(td("000E 0040 0001 FFFFFFFF 0004 000A"))
    assert array == Array(0x40, "Array", element=Scalar(0x0A, "DBL"), dimensions=(VARIABLE,))
    assert array.rank == 1

    # Cluster: an I32 then a DBL, in order.
    cluster = parse_type_descriptor(td("000E 0050 0002 0004 0003 0004 000A"))
    assert cluster == Cluster(0x50, "Cluster", fields=(Scalar(0x03, "I32"), Scalar(0x0A, "DBL")))

    # And the one-line rendering of a nested shape is stable.
    nested = parse_type_descriptor(
        td("001C 0040 0001 FFFFFFFF 0012 0050 0002 0004 0003 0008 0030 FFFFFFFF")
    )
    assert describe(nested) == "1D Array of Cluster { I32, String }"
