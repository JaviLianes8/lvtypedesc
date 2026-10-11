from lvtypedesc import parse_type_descriptor, pretty


def td(hex_bytes: str) -> bytes:
    return bytes.fromhex(hex_bytes)


def test_pretty_renders_a_scalar_on_one_line() -> None:
    assert pretty(parse_type_descriptor(td("0004 0003"))) == "I32"


def test_pretty_renders_a_nested_tree() -> None:
    node = parse_type_descriptor(
        td("001C 0040 0001 FFFFFFFF 0012 0050 0002 0004 0003 0008 0030 FFFFFFFF")
    )
    assert pretty(node) == (
        "Array (rank 1, dims [variable])\n"
        "  Cluster (2 fields)\n"
        "    [0] I32\n"
        "    [1] String (size variable)"
    )


def test_pretty_shows_fixed_string_size() -> None:
    assert pretty(parse_type_descriptor(td("0008 0030 00000010"))) == "String (size 16 bytes)"
