"""The complete promise of parse_type_descriptor, edge by edge."""

from __future__ import annotations

import pytest

from lvtypedesc import (
    MAX_DEPTH,
    VARIABLE,
    Array,
    Cluster,
    FixedPoint,
    LVEnum,
    LVString,
    LVVariant,
    PhysicalQuantity,
    Refnum,
    Scalar,
    TypeDescError,
    Waveform,
    parse_type_descriptor,
)


def td(text: str) -> bytes:
    return bytes.fromhex(text)


@pytest.mark.parametrize("kind", [bytes, bytearray, memoryview])
def test_accepts_every_bytes_like_input(kind: type) -> None:
    assert parse_type_descriptor(kind(td("0004 0003"))) == Scalar(0x03, "I32")


@pytest.mark.parametrize("value", ["00040003", None, 3, [0, 4, 0, 3]])
def test_refuses_anything_else_with_type_error(value: object) -> None:
    with pytest.raises(TypeError, match=f"not {type(value).__name__}$"):
        parse_type_descriptor(value)  # type: ignore[arg-type]


def test_reads_every_scalar_code_with_its_name() -> None:
    names: tuple[str, ...] = ("I8", "I16", "I32", "I64", "U8", "U16", "U32", "U64")
    names += ("SGL", "DBL", "EXT", "CSG", "CDB", "CXT")
    for code, name in enumerate(names, start=1):
        assert parse_type_descriptor(bytes((0, 4, 0, code))) == Scalar(code, name)


def test_the_high_byte_is_kept_as_flags_and_the_low_byte_is_the_code() -> None:
    node = parse_type_descriptor(td("0004 8003"))
    assert (node.code, node.flags, node.label) == (3, 0x80, None)


def test_a_name_follows_when_bit_0x40_is_set() -> None:
    assert parse_type_descriptor(td("0008 4003 0261 6200")).label == "ab"
    assert parse_type_descriptor(td("0006 4003 0000")).label == ""


def test_a_name_starts_at_the_next_even_offset() -> None:
    node = parse_type_descriptor(td("000E 4016 0001 0241 4200 0278 7900"))
    assert isinstance(node, LVEnum)
    assert (node.items, node.label) == (("AB",), "xy")


def test_without_bit_0x40_trailing_bytes_are_not_a_name() -> None:
    assert parse_type_descriptor(td("0008 0003 0261 6200")).label is None


def test_bit_0x40_with_nothing_after_the_fields_means_no_name() -> None:
    node = parse_type_descriptor(td("0004 4003"))
    assert (node.label, node.flags) == (None, 0x40)


@pytest.mark.parametrize("data", ["0006 4003 0561", "0006 4003 0261", "0008 4003 0461 6263"])
def test_a_name_running_past_its_descriptor_raises(data: str) -> None:
    with pytest.raises(TypeDescError, match=r"^name of the descriptor at offset 0 runs past it$"):
        parse_type_descriptor(td(data))


def test_a_name_that_ends_exactly_at_the_end_is_read() -> None:
    assert parse_type_descriptor(td("0007 4003 0261 62")).label == "ab"


def test_names_are_latin_1() -> None:
    assert parse_type_descriptor(td("0006 4003 01E9")).label == "é"


def test_strings_keep_their_size_word() -> None:
    assert parse_type_descriptor(td("0008 0032 0000 0010")) == LVString(0x32, "Path", size=16)
    assert parse_type_descriptor(td("0008 0033 FFFF FFFF")).size == VARIABLE  # type: ignore[attr-defined]


def test_a_string_without_its_size_word_raises() -> None:
    with pytest.raises(TypeDescError, match="offset 0 is too short for its fields"):
        parse_type_descriptor(td("0006 0030 0000"))


def test_arrays_keep_dimensions_in_order() -> None:
    node = parse_type_descriptor(td("0016 0040 0003 0000 0002 FFFF FFFF 0000 0000 0004 0021"))
    assert node == Array(
        0x40, "Array", element=parse_type_descriptor(td("0004 0021")), dimensions=(2, VARIABLE, 0)
    )


def test_a_child_may_not_run_past_its_parent() -> None:
    with pytest.raises(TypeDescError, match="offset 6 runs past its parent"):
        parse_type_descriptor(td("000A 0050 0001 0008 0003 0000 0000"))


def test_a_child_that_runs_past_the_input_raises() -> None:
    with pytest.raises(TypeDescError, match="runs past the input"):
        parse_type_descriptor(td("000E 0040 0001 FFFFFFFF 0004"))


def test_a_cluster_with_fewer_bytes_than_its_count_raises() -> None:
    with pytest.raises(TypeDescError, match="truncated: need a 4-byte header at offset 10"):
        parse_type_descriptor(td("000A 0050 0002 0004 0003"))


def test_clusters_may_be_empty() -> None:
    assert parse_type_descriptor(td("0006 0050 0000")) == Cluster(0x50, "Cluster")


def test_enums_units_variants_and_opaque_types() -> None:
    assert parse_type_descriptor(td("0008 0017 0001 0130")) == LVEnum(0x17, "EnumU32", items=("0",))
    assert parse_type_descriptor(td("000A 001E 0001 0008 8000")) == PhysicalQuantity(
        0x1E, "CXTUnit", units=((8, -32768),)
    )
    assert parse_type_descriptor(td("0004 0053")) == LVVariant(0x53, "Variant")
    assert parse_type_descriptor(td("0007 005F 0102 03")) == FixedPoint(
        0x5F, "FXP", payload=b"\x01\x02\x03"
    )
    assert parse_type_descriptor(td("0005 0070 01")).subtype == 0  # type: ignore[attr-defined]
    assert parse_type_descriptor(td("0004 0054")) == Waveform(0x54, "Waveform")


def test_opaque_types_keep_a_name_inside_their_payload() -> None:
    node = parse_type_descriptor(td("000A 4070 0002 0378 7978"))
    assert isinstance(node, Refnum)
    assert (node.label, node.payload, node.flags) == (None, td("0002 0378 7978"), 0x40)


def _nested(depth: int) -> bytes:
    data = td("0004 0003")
    for _ in range(depth - 1):
        data = (len(data) + 6).to_bytes(2, "big") + td("0050 0001") + data
    return data


def test_nesting_up_to_max_depth_is_read() -> None:
    node = parse_type_descriptor(_nested(MAX_DEPTH))
    for _ in range(MAX_DEPTH - 1):
        assert isinstance(node, Cluster)
        node = node.fields[0]
    assert node == Scalar(0x03, "I32")


def test_nesting_deeper_than_max_depth_raises() -> None:
    with pytest.raises(TypeDescError, match=f"nested deeper than {MAX_DEPTH} levels"):
        parse_type_descriptor(_nested(MAX_DEPTH + 1))


@pytest.mark.parametrize(
    ("code", "name"),
    [(0x00, "Void"), (0x5E, "ComplexFXP"), (0x73, "Set"), (0x74, "Map"), (0xF1, "Typedef")],
)
def test_known_but_unsupported_codes_are_refused_by_name(code: int, name: str) -> None:
    with pytest.raises(TypeDescError, match=rf"^unsupported type {name} 0x{code:02x} at offset 0$"):
        parse_type_descriptor(bytes((0, 4, 0, code)))


def test_unknown_codes_report_where_they_are() -> None:
    with pytest.raises(TypeDescError, match=r"^unknown type code 0x99 at offset 6$"):
        parse_type_descriptor(td("000A 0050 0001 0004 0099"))


@pytest.mark.parametrize("data", ["", "00", "0004 00", "0003 0003", "0000 0003"])
def test_short_or_impossible_headers_raise(data: str) -> None:
    with pytest.raises(TypeDescError):
        parse_type_descriptor(td(data))
