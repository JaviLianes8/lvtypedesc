"""The complete promise of to_bytes: the inverse of parsing, and its refusals."""

from __future__ import annotations

import pytest

from lvtypedesc import (
    VARIABLE,
    Array,
    Boolean,
    Cluster,
    FixedPoint,
    LVEnum,
    LVString,
    LVVariant,
    PhysicalQuantity,
    Refnum,
    Scalar,
    TypeDesc,
    TypeDescError,
    Waveform,
    describe,
    parse_type_descriptor,
    pretty,
    to_bytes,
)

I32 = Scalar(0x03, "I32")
TREES: list[TypeDesc] = [
    I32,
    Scalar(0x0E, "CXT", label=""),
    Boolean(0x20, "Boolean16", label="b"),
    LVString(0x30, "String"),
    LVString(0x33, "Picture", size=0, label="pic"),
    LVString(0x32, "Path", size=0xFFFFFFFE),
    Array(0x40, "Array", element=I32, dimensions=()),
    Array(0x40, "Array", element=I32, dimensions=(VARIABLE, 3), label="xyz"),
    Cluster(0x50, "Cluster"),
    Cluster(0x50, "Cluster", fields=(I32, Cluster(0x50, "Cluster", fields=(I32,))), label="c"),
    LVEnum(0x15, "EnumU8"),
    LVEnum(0x16, "EnumU16", items=("a", "", "x" * 255), label="e"),
    PhysicalQuantity(0x19, "SGLUnit", units=((0, 1), (8, -1), (65535, 32767))),
    PhysicalQuantity(0x1C, "CSGUnit", label="u"),
    LVVariant(0x53, "Variant", label="v"),
    FixedPoint(0x5F, "FXP", payload=b"\x01"),
    Refnum(0x70, "Refnum", payload=b"\x00\x02xyz", flags=0x40),
    Waveform(0x54, "Waveform", payload=b"\x00\x06"),
]


@pytest.mark.parametrize("tree", TREES, ids=repr)
def test_parsing_the_written_bytes_gives_the_tree_back(tree: TypeDesc) -> None:
    data = to_bytes(tree)
    assert parse_type_descriptor(data) == tree
    assert to_bytes(parse_type_descriptor(data)) == data
    assert int.from_bytes(data[:2], "big") == len(data)


def test_names_set_bit_0x40_and_other_flags_are_kept() -> None:
    assert to_bytes(Scalar(0x03, "I32", label="n")) == bytes.fromhex("0006 4003 016E")
    assert to_bytes(Scalar(0x03, "I32", flags=0x81)) == bytes.fromhex("0004 8103")
    assert to_bytes(Scalar(0x03, "I32", flags=0x80, label="")) == bytes.fromhex("0006 C003 0000")


def test_structured_descriptors_are_padded_to_whole_words() -> None:
    assert to_bytes(LVEnum(0x15, "EnumU8", items=("A",))) == bytes.fromhex("0008 0015 0001 0141")
    assert to_bytes(LVEnum(0x15, "EnumU8", items=("AB",))) == bytes.fromhex(
        "000A 0015 0001 0241 4200"
    )
    assert to_bytes(LVEnum(0x15, "EnumU8", items=("AB",), label="x")) == bytes.fromhex(
        "000C 4015 0001 0241 4200 0178"
    )


def test_opaque_payloads_are_written_exactly() -> None:
    assert to_bytes(FixedPoint(0x5F, "FXP", payload=b"\x01")) == bytes.fromhex("0005 005F 01")


@pytest.mark.parametrize("function", [to_bytes, describe, pretty])
def test_a_name_that_does_not_match_the_code_is_refused(function: object) -> None:
    assert callable(function)
    with pytest.raises(TypeDescError, match=r"^name does not match code 0x03 \(expected I32\)$"):
        function(Scalar(0x03, "Bogus"))


@pytest.mark.parametrize(
    "tree",
    [
        Scalar(0x30, "String"),
        LVString(0x03, "I32"),
        Boolean(0x99, "Boolean"),
        Scalar(256, "I32"),
        Scalar(-1, "I32"),
        Refnum(0x5F, "FXP"),
        Waveform(0x70, "Refnum"),
        FixedPoint(0x54, "Waveform"),
        LVVariant(0x50, "Cluster"),
        Cluster(0x40, "Array"),
    ],
    ids=repr,
)
def test_a_code_must_fit_the_class(tree: TypeDesc) -> None:
    with pytest.raises(TypeDescError, match="does not fit a"):
        to_bytes(tree)


@pytest.mark.parametrize(
    ("tree", "message"),
    [
        (Scalar(0x03, "I32", flags=256), "flags must be 0 to 255"),
        (Scalar(0x03, "I32", flags=-1), "flags must be 0 to 255"),
        (LVString(0x30, "String", size=-2), "size must be VARIABLE or 0 to 4294967294"),
        (LVString(0x30, "String", size=0xFFFFFFFF), "size must be VARIABLE"),
        (Array(0x40, "Array", element=I32, dimensions=(2**32,)), "dimension must be"),
        (Array(0x40, "Array", element=I32, dimensions=(0,) * 65536), "65536 dimensions do not"),
        (Cluster(0x50, "Cluster", fields=(I32,) * 65536), "65536 fields do not fit"),
        (LVEnum(0x15, "EnumU8", items=("",) * 65536), "65536 items do not fit"),
        (LVEnum(0x15, "EnumU8", items=("x" * 256,)), "item of 256 bytes is longer than 255"),
        (LVEnum(0x15, "EnumU8", items=("€",)), "item holds a character outside Latin-1"),
        (Scalar(0x03, "I32", label="€"), "label holds a character outside Latin-1"),
        (Scalar(0x03, "I32", label="x" * 256), "label of 256 bytes is longer than 255"),
        (PhysicalQuantity(0x19, "SGLUnit", units=((65536, 0),)), "unit base must be"),
        (PhysicalQuantity(0x19, "SGLUnit", units=((0, 32768),)), "exponent -32768 to 32767"),
        (PhysicalQuantity(0x19, "SGLUnit", units=((0, -32769),)), "exponent -32768 to 32767"),
        (PhysicalQuantity(0x19, "SGLUnit", units=((0, 0),) * 65536), "65536 units do not"),
        (FixedPoint(0x5F, "FXP", label="x"), "a FixedPoint keeps its name inside payload"),
        (Refnum(0x70, "Refnum", label="x"), "a Refnum keeps its name inside payload"),
        (Waveform(0x54, "Waveform", label="x"), "a Waveform keeps its name inside payload"),
        (FixedPoint(0x5F, "FXP", payload=b"\x00" * 65532), "65536 bytes does not fit"),
    ],
)
@pytest.mark.parametrize("function", [to_bytes, describe, pretty])
def test_values_that_do_not_fit_raise(function: object, tree: TypeDesc, message: str) -> None:
    assert callable(function)
    big_only = "bytes does not fit" in message  # only writing knows the total length
    if big_only and function is not to_bytes:
        function(tree)
        return
    with pytest.raises(TypeDescError, match=message):
        function(tree)


@pytest.mark.parametrize("function", [to_bytes, describe, pretty])
def test_the_bare_base_class_is_not_a_node(function: object) -> None:
    assert callable(function)
    with pytest.raises(
        TypeError,
        match=r"^node must be an instance of a node class such as Scalar or Cluster, not TypeDesc$",
    ):
        function(TypeDesc(0x03, "I32"))


@pytest.mark.parametrize("function", [to_bytes, describe, pretty])
def test_huge_numbers_are_refused_before_rendering(function: object) -> None:
    assert callable(function)
    for tree in (
        LVString(0x30, "String", size=10**5000),
        Array(0x40, "Array", element=I32, dimensions=(-5,)),
        PhysicalQuantity(0x1A, "DBLUnit", units=((10**5000, 1),)),
    ):
        with pytest.raises(TypeDescError):
            function(tree)


def test_the_largest_descriptor_is_written() -> None:
    data = to_bytes(FixedPoint(0x5F, "FXP", payload=b"\x00" * 65531))
    assert len(data) == 0xFFFF


def test_a_tree_too_large_for_the_length_word_raises() -> None:
    with pytest.raises(TypeDescError, match="does not fit the 16-bit length"):
        to_bytes(Cluster(0x50, "Cluster", fields=(I32,) * 20000))
