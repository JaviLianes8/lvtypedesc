import pytest

from lvtypedesc import parse_type_descriptor, pretty
from lvtypedesc._cli import main


def test_decode_prints_the_readable_type(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["decode", "00040003"]) == 0
    assert capsys.readouterr().out.strip() == "I32"


def test_decode_ignores_whitespace_in_hex(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["decode", "0004 000A"]) == 0
    assert capsys.readouterr().out.strip() == "DBL"


def test_decode_tree_matches_pretty(capsys: pytest.CaptureFixture[str]) -> None:
    hex_text = "000E00500002000400030004000A"
    assert main(["decode", "--tree", hex_text]) == 0
    expected = pretty(parse_type_descriptor(bytes.fromhex(hex_text)))
    assert capsys.readouterr().out.strip() == expected.strip()


def test_decode_bad_hex_errors_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["decode", "zzzz"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "not valid hex" in captured.err
    assert "zzzz" not in captured.err


def test_decode_unknown_code_errors_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["decode", "00040099"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unknown type code" in captured.err


def test_codes_lists_known_codes(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["codes"]) == 0
    out = capsys.readouterr().out
    assert "0x0A  DBL" in out
    assert "0x40  Array" in out
    assert "0x5F  FXP" in out


def test_no_command_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 2
    assert "usage: lvtypedesc" in capsys.readouterr().err
