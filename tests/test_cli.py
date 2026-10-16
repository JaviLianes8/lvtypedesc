"""The command line, in process: output, exit codes and bounded errors."""

from __future__ import annotations

import pytest

from lvtypedesc import __version__, known_codes, parse_type_descriptor, pretty
from lvtypedesc._cli import main


def _run(capsys: pytest.CaptureFixture[str], *args: str) -> tuple[int, str, str]:
    code = main(list(args))
    out, err = capsys.readouterr()
    return code, out, err


def test_decode_prints_the_readable_type(capsys: pytest.CaptureFixture[str]) -> None:
    assert _run(capsys, "decode", "00040003") == (0, "I32\n", "")


def test_decode_ignores_whitespace_in_hex(capsys: pytest.CaptureFixture[str]) -> None:
    assert _run(capsys, "decode", " 0004\t000A\n") == (0, "DBL\n", "")


def test_decode_tree_matches_pretty(capsys: pytest.CaptureFixture[str]) -> None:
    hex_text = "00140050000200064003016E00080030FFFFFFFF"
    expected = pretty(parse_type_descriptor(bytes.fromhex(hex_text))) + "\n"
    assert _run(capsys, "decode", "--tree", hex_text) == (0, expected, "")
    assert "'n'" in expected


def test_bad_hex_is_a_data_error_that_never_echoes_it(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = _run(capsys, "decode", "zz" * 5000)
    assert (code, out) == (1, "")
    assert err == (
        "lvtypedesc: error: not valid hex (digits 0-9 and A-F in pairs, spaces allowed)\n"
    )


def test_unreadable_descriptors_are_data_errors(capsys: pytest.CaptureFixture[str]) -> None:
    assert _run(capsys, "decode", "00040099") == (
        1,
        "",
        "lvtypedesc: error: unknown type code 0x99 at offset 0\n",
    )
    assert _run(capsys, "decode", "")[0] == 1


def test_codes_lists_every_known_code(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = _run(capsys, "codes")
    lines = out.splitlines()
    assert (code, err, len(lines)) == (0, "", len(known_codes()))
    assert lines[0] == "0x01  I8         scalar"
    assert "0x16  EnumU16    enum" in lines
    assert lines[-1] == "0x70  Refnum     refnum"


def test_version_and_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert _run(capsys, "--version") == (0, f"lvtypedesc {__version__}\n", "")
    code, out, _ = _run(capsys, "--help")
    assert code == 0
    assert "examples:" in out and "lvtypedesc decode --tree" in out


@pytest.mark.parametrize("args", [[], ["frob"], ["decode"], ["decode", "00", "--x"]])
def test_usage_errors_exit_two(capsys: pytest.CaptureFixture[str], args: list[str]) -> None:
    code, out, err = _run(capsys, *args)
    assert (code, out) == (2, "")
    assert err.startswith("usage: lvtypedesc")


def test_usage_errors_do_not_echo_huge_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = _run(capsys, "x" * 100_000)
    assert code == 2
    assert len(err) < 1000
