import pytest

from lvtypedesc import (
    Scalar,
    TypeDescError,
    parse_type_descriptor,
    to_bytes,
)


def td(hex_bytes: str) -> bytes:
    return bytes.fromhex(hex_bytes)


CANONICAL = [
    "0004 0003",  # I32
    "0004 000A",  # DBL
    "0004 0021",  # Boolean
    "0008 0030 FFFFFFFF",  # variable string
    "0008 0030 00000010",  # fixed 16-byte string
    "000E 0040 0001 FFFFFFFF 0004 000A",  # 1D array of DBL
    "0012 0040 0002 FFFFFFFF FFFFFFFF 0004 000A",  # 2D array of DBL
    "000E 0050 0002 0004 0003 0004 000A",  # cluster of I32, DBL
    "001C 0040 0001 FFFFFFFF 0012 0050 0002 0004 0003 0008 0030 FFFFFFFF",
    "0008 005F 12345678",  # FXP with payload
    "0006 0070 0001",  # refnum with subtype
]


@pytest.mark.parametrize("hex_bytes", CANONICAL)
def test_to_bytes_is_byte_exact_for_canonical_descriptors(hex_bytes: str) -> None:
    data = td(hex_bytes)
    assert to_bytes(parse_type_descriptor(data)) == data


@pytest.mark.parametrize("hex_bytes", CANONICAL)
def test_parse_and_emit_are_inverses(hex_bytes: str) -> None:
    node = parse_type_descriptor(td(hex_bytes))
    assert parse_type_descriptor(to_bytes(node)) == node


def test_to_bytes_ignores_trailing_flattened_data() -> None:
    data = td("0004 0003")
    node = parse_type_descriptor(data + b"\xde\xad")
    assert to_bytes(node) == data


def test_to_bytes_refuses_a_tree_too_large_for_the_short_form() -> None:
    # Build a cluster whose serialised body would exceed the 16-bit length word.
    from lvtypedesc import Cluster

    big = Cluster(0x50, "Cluster", fields=(Scalar(0x03, "I32", label="abcd"),) * 8000)
    with pytest.raises(TypeDescError, match="does not fit the 16-bit length"):
        to_bytes(big)
