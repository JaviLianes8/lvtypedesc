import pytest

from lvtypedesc import (
    VARIABLE,
    Array,
    Boolean,
    Cluster,
    LVString,
    Scalar,
    TypeDescError,
    describe,
    parse_type_descriptor,
)


def td(hex_bytes: str) -> bytes:
    return bytes.fromhex(hex_bytes)


def test_scalar_i32() -> None:
    node = parse_type_descriptor(td("0004 0003"))
    assert isinstance(node, Scalar)
    assert node.code == 0x03
    assert node.name == "I32"


def test_scalar_dbl() -> None:
    node = parse_type_descriptor(td("0004 000A"))
    assert isinstance(node, Scalar)
    assert node.name == "DBL"


def test_boolean() -> None:
    node = parse_type_descriptor(td("0004 0021"))
    assert isinstance(node, Boolean)
    assert node.name == "Boolean"


def test_string_is_variable_sized() -> None:
    node = parse_type_descriptor(td("0008 0030 FFFFFFFF"))
    assert isinstance(node, LVString)
    assert node.name == "String"


def test_one_dimensional_array_of_numerics() -> None:
    node = parse_type_descriptor(td("000E 0040 0001 FFFFFFFF 0004 0003"))
    assert isinstance(node, Array)
    assert node.rank == 1
    assert node.dimensions == (VARIABLE,)
    assert isinstance(node.element, Scalar)
    assert node.element.name == "I32"


def test_two_dimensional_array_reports_rank() -> None:
    node = parse_type_descriptor(td("0012 0040 0002 FFFFFFFF FFFFFFFF 0004 000A"))
    assert isinstance(node, Array)
    assert node.rank == 2


def test_cluster_of_fields() -> None:
    node = parse_type_descriptor(td("000E 0050 0002 0004 0003 0004 000A"))
    assert isinstance(node, Cluster)
    assert [f.name for f in node.fields] == ["I32", "DBL"]


def test_nested_array_of_cluster_describes_readably() -> None:
    cluster = "0012 0050 0002 0004 0003 0008 0030 FFFFFFFF"
    node = parse_type_descriptor(td(f"001C 0040 0001 FFFFFFFF {cluster}"))
    assert describe(node) == "1D Array of Cluster { I32, String }"


def test_trailing_flattened_data_is_ignored() -> None:
    node = parse_type_descriptor(td("0004 0003") + b"\xde\xad\xbe\xef")
    assert isinstance(node, Scalar)


def test_empty_input_raises() -> None:
    with pytest.raises(TypeDescError):
        parse_type_descriptor(b"")


def test_truncated_array_raises() -> None:
    with pytest.raises(TypeDescError, match="past the input"):
        parse_type_descriptor(td("000E 0040 0001 FFFFFFFF 0004"))


def test_unknown_type_code_raises() -> None:
    with pytest.raises(TypeDescError, match="unknown type code"):
        parse_type_descriptor(td("0004 0099"))


def test_unsupported_type_code_names_the_type() -> None:
    with pytest.raises(TypeDescError, match="EnumU16"):
        parse_type_descriptor(td("0004 0016"))


def test_length_word_below_header_raises() -> None:
    with pytest.raises(TypeDescError, match="too small"):
        parse_type_descriptor(td("0002 0003"))


def test_non_bytes_input_raises() -> None:
    with pytest.raises(TypeDescError, match="expected bytes"):
        parse_type_descriptor("0004 0003")  # type: ignore[arg-type]
