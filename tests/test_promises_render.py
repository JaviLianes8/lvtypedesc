"""The promises of describe, pretty, the code table, the error type and the node classes."""

from __future__ import annotations

import dataclasses
import pickle

import pytest

from lvtypedesc import (
    MAX_DEPTH,
    VARIABLE,
    Array,
    Boolean,
    Category,
    Cluster,
    FixedPoint,
    LVEnum,
    LVString,
    LVVariant,
    PhysicalQuantity,
    Refnum,
    Scalar,
    TypeCode,
    TypeDesc,
    TypeDescError,
    Waveform,
    describe,
    known_codes,
    pretty,
    to_bytes,
)

I32 = Scalar(0x03, "I32", label="n")


@pytest.mark.parametrize(
    ("tree", "line", "tree_text"),
    [
        (I32, "I32", "I32 'n'"),
        (LVString(0x30, "String", size=4), "String", "String (size 4 bytes)"),
        (
            LVEnum(0x16, "EnumU16", items=("a", "b\n")),
            "EnumU16 (2 items)",
            "EnumU16 (2 items: 'a', 'b\\n')",
        ),
        (
            PhysicalQuantity(0x1A, "DBLUnit", units=((3, 1), (2, -2), (9, 3))),
            "DBLUnit [m s^-2 base9^3]",
            "DBLUnit [m s^-2 base9^3]",
        ),
        (LVVariant(0x53, "Variant", label="v\x00"), "Variant", "Variant 'v\\x00'"),
        (FixedPoint(0x5F, "FXP", payload=b"\x00" * 56), "FXP", "FXP (56-byte payload)"),
        (
            Refnum(0x70, "Refnum", payload=b"\x01\x2a"),
            "Refnum(subtype=0x12a)",
            "Refnum(subtype=0x12a)",
        ),
        (Waveform(0x54, "Waveform", payload=b"\x00\x06"), "Timestamp", "Timestamp"),
        (
            Waveform(0x54, "Waveform", payload=b"\x00\x03"),
            "Waveform(subtype=0x03)",
            "Waveform(subtype=0x03)",
        ),
        (Cluster(0x50, "Cluster"), "Cluster {  }", "Cluster (0 fields)"),
    ],
)
def test_each_node_has_a_line_and_a_tree(tree: TypeDesc, line: str, tree_text: str) -> None:
    assert describe(tree) == line
    assert pretty(tree) == tree_text


def test_pretty_spells_out_nesting_positions_and_names() -> None:
    inner = Array(0x40, "Array", element=I32, dimensions=(VARIABLE, 2), label="a")
    tree = Cluster(0x50, "Cluster", fields=(inner, Boolean(0x21, "Boolean")), label="c")
    assert describe(tree) == "Cluster { 2D Array of I32, Boolean }"
    assert pretty(tree) == (
        "Cluster (2 fields) 'c'\n"
        "  [0] Array (rank 2, dims [variable, 2]) 'a'\n"
        "      I32 'n'\n"
        "  [1] Boolean"
    )


def _deep(depth: int) -> TypeDesc:
    node: TypeDesc = I32
    for _ in range(depth - 1):
        node = Array(0x40, "Array", element=node, dimensions=(1,))
    return node


@pytest.mark.parametrize("function", [describe, pretty, to_bytes])
def test_every_function_takes_max_depth_and_refuses_more(function: object) -> None:
    assert callable(function)
    function(_deep(MAX_DEPTH))
    with pytest.raises(TypeDescError, match=f"tree nested deeper than {MAX_DEPTH} levels"):
        function(_deep(MAX_DEPTH + 1))


@pytest.mark.parametrize("function", [describe, pretty, to_bytes])
@pytest.mark.parametrize(
    ("tree", "message"),
    [
        ("I32", "node must be a TypeDesc, not str"),
        (Scalar("3", "I32"), "code must be an int, not str"),  # type: ignore[arg-type]
        (Scalar(True, "I32"), "code must be an int, not bool"),
        (Scalar(3, "I32", flags=None), "flags must be an int, not NoneType"),  # type: ignore[arg-type]
        (Scalar(3, b"I32"), "name must be a str, not bytes"),  # type: ignore[arg-type]
        (Scalar(3, "I32", label=b"x"), "label must be a str or None, not bytes"),  # type: ignore[arg-type]
        (LVString(0x30, "String", size=1.0), "size must be an int"),  # type: ignore[arg-type]
        (Array(0x40, "Array", element=I32, dimensions=[1]), "dimensions must be a tuple"),  # type: ignore[arg-type]
        (Array(0x40, "Array", element="I32"), "element must be a TypeDesc"),  # type: ignore[arg-type]
        (Cluster(0x50, "Cluster", fields=(I32, 3)), "fields must be a tuple of TypeDesc"),  # type: ignore[arg-type]
        (LVEnum(0x15, "EnumU8", items=["a"]), "items must be a tuple of str"),  # type: ignore[arg-type]
        (PhysicalQuantity(0x19, "SGLUnit", units=((1,),)), "units must be a tuple of"),  # type: ignore[arg-type]
        (FixedPoint(0x5F, "FXP", payload=bytearray()), "payload must be bytes"),  # type: ignore[arg-type]
    ],
)
def test_malformed_trees_raise_type_error(function: object, tree: object, message: str) -> None:
    assert callable(function)
    with pytest.raises(TypeError, match=message):
        function(tree)


def test_long_type_names_are_cut_in_messages() -> None:
    name = type("N" * 300, (), {})
    with pytest.raises(TypeError) as caught:
        describe(name())
    assert str(caught.value) == f"node must be a TypeDesc, not {'N' * 40}..."


def test_known_codes_is_the_whole_table_sorted() -> None:
    rows = known_codes()
    assert [code for code, _, _ in rows] == sorted(code for code, _, _ in rows)
    assert len(rows) == 34
    assert {code for code, _, _ in rows} == {int(member) for member in TypeCode}
    assert rows[-1] == (0x70, "Refnum", Category.REFNUM)
    assert known_codes() is not known_codes()


def test_category_values_are_stable() -> None:
    assert [c.value for c in Category] == [
        "scalar",
        "enum",
        "quantity",
        "boolean",
        "string",
        "array",
        "cluster",
        "variant",
        "waveform",
        "fxp",
        "refnum",
    ]


def test_type_desc_error_is_a_value_error_in_the_package() -> None:
    assert issubclass(TypeDescError, ValueError)
    assert TypeDescError.__module__ == "lvtypedesc"


def test_nodes_are_frozen_hashable_picklable_and_ignore_flags_in_equality() -> None:
    node = Cluster(0x50, "Cluster", fields=(I32,), label="c", flags=0x40)
    with pytest.raises(dataclasses.FrozenInstanceError):
        node.label = "x"  # type: ignore[misc]
    assert hash(node) == hash(dataclasses.replace(node, flags=0))
    assert node == dataclasses.replace(node, flags=0)
    assert node != dataclasses.replace(node, label=None)
    assert pickle.loads(pickle.dumps(node)) == node
    assert Refnum(0x70, "Refnum").subtype == 0 and Waveform(0x54, "Waveform").subtype == 0
