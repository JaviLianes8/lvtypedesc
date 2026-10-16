"""Contracts added after the blind mutation round: exact limits, wording, closed output."""

from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path

import pytest

from lvtypedesc import (
    Array,
    Cluster,
    FixedPoint,
    LVString,
    PhysicalQuantity,
    Scalar,
    TypeDescError,
    describe,
    parse_type_descriptor,
    pretty,
    to_bytes,
)
from lvtypedesc._cli import main

I32 = Scalar(0x03, "I32")


def test_every_base_has_its_symbol_and_the_next_index_is_named_by_number() -> None:
    node = PhysicalQuantity(0x1A, "DBLUnit", units=((8, 1), (9, 2)))
    assert describe(node) == "DBLUnit [cd base9^2]"


def test_type_names_of_exactly_forty_characters_are_kept_whole() -> None:
    name = type("A" * 40, (), {})
    with pytest.raises(TypeError) as caught:
        parse_type_descriptor(name())
    assert str(caught.value).endswith("not " + "A" * 40)


class Broken(io.StringIO):
    def write(self, text: str) -> int:
        raise BrokenPipeError

    def flush(self) -> None:
        raise BrokenPipeError

    def fileno(self) -> int:
        raise OSError


@pytest.mark.parametrize("args", [["--version"], ["--help"], ["decode", "00040003"], ["codes"]])
def test_output_that_cannot_be_written_exits_one(
    monkeypatch: pytest.MonkeyPatch, args: list[str]
) -> None:
    monkeypatch.setattr(sys, "stdout", Broken())
    assert main(args) == 1


def test_a_closed_stdout_descriptor_exits_one_quietly() -> None:
    src = str(Path(__file__).resolve().parents[1] / "src")
    code = (
        "import os, sys; os.close(1); from lvtypedesc._cli import main;"
        " sys.exit(main(['decode', '00040003']))"
    )
    env = {**os.environ, "PYTHONPATH": src}
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=60, env=env
    )
    assert (result.returncode, result.stderr) == (1, "")


def test_codes_are_printed_in_upper_case_hex(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["codes"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert "0x0A  DBL        scalar" in lines
    assert "0x5F  FXP        fxp" in lines


def test_a_label_must_be_exactly_a_str() -> None:
    class S(str):
        pass

    for function in (to_bytes, describe, pretty):
        with pytest.raises(TypeError, match=r"^label must be a str or None, not S$"):
            function(Scalar(0x03, "I32", label=S("x")))


@pytest.mark.parametrize("function", [describe, pretty])
def test_the_size_bound_counts_string_words_and_name_length_bytes(function: object) -> None:
    assert callable(function)
    strings = Cluster(0x50, "Cluster", fields=(LVString(0x30, "String"),) * 8192)
    names = Cluster(0x50, "Cluster", fields=(Scalar(0x03, "I32", label=""),) * 13107)
    for tree in (strings, names):
        with pytest.raises(TypeDescError, match="needs more than 65535 bytes"):
            function(tree)


def test_a_rank_zero_array_has_rank_zero() -> None:
    assert Array(0x40, "Array", element=I32).rank == 0
    node = parse_type_descriptor(bytes.fromhex("000A 0040 0000 0004 0003"))
    assert isinstance(node, Array) and node.rank == 0


def test_fixed_point_payload_may_be_positional() -> None:
    assert FixedPoint(0x5F, "FXP", b"AB").payload == b"AB"


LARGEST = FixedPoint(0x5F, "FXP", payload=b"A" * 65531)


def test_a_65535_byte_descriptor_is_read_whole() -> None:
    data = to_bytes(LARGEST)
    assert len(data) == 0xFFFF
    assert parse_type_descriptor(data + b"xx") == LARGEST
    interleaved = bytes(b for byte in data + b"x" for b in (byte, 0))
    assert parse_type_descriptor(memoryview(interleaved)[::2]) == LARGEST


@pytest.mark.parametrize("data", ["000400", "0009 0050 0001 0004 00 0300"])
def test_a_header_cut_short_is_reported_as_truncated(data: str) -> None:
    with pytest.raises(TypeDescError, match=r"^truncated: need a 4-byte header at offset"):
        parse_type_descriptor(bytes.fromhex(data))


def test_the_lowest_exponent_round_trips() -> None:
    node = PhysicalQuantity(0x1A, "DBLUnit", units=((0, -32768),))
    assert parse_type_descriptor(to_bytes(node)) == node


@pytest.mark.parametrize("code", [0x10000, -1])
def test_codes_outside_sixteen_bits_are_reported_out_of_range(code: int) -> None:
    with pytest.raises(TypeDescError, match=r"^code out of range does not fit a Scalar node$"):
        to_bytes(Scalar(code, "I32"))


def test_padding_past_the_length_word_is_refused_by_writing() -> None:
    tree = Cluster(0x50, "Cluster", fields=(Scalar(0x03, "I32", label=""),) + (I32,) * 16381)
    with pytest.raises(TypeDescError, match=r"^descriptor of 65536 bytes does not fit"):
        to_bytes(tree)
