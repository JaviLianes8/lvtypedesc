"""Hostile trees and inputs: shared subtrees, lying subclasses, odd buffers, odd consoles."""

from __future__ import annotations

import array
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from lvtypedesc import (
    Array,
    Cluster,
    FixedPoint,
    LVEnum,
    LVString,
    PhysicalQuantity,
    Scalar,
    TypeCode,
    TypeDescError,
    describe,
    parse_type_descriptor,
    pretty,
    to_bytes,
)

I32 = Scalar(0x03, "I32")
FUNCTIONS = [to_bytes, describe, pretty]


def _shared(levels: int) -> Cluster:
    node: Any = I32
    for _ in range(levels):
        node = Cluster(0x50, "Cluster", fields=(node, node))
    return node  # type: ignore[no-any-return]


# Runs first: a cheap test that fails fast if the size bound is lost, before the shared
# tree below could take forever without it.
def test_the_largest_writable_tree_is_accepted_and_one_more_node_is_not() -> None:
    tree = Cluster(0x50, "Cluster", fields=(I32,) * 16382)
    assert len(to_bytes(tree)) == 0xFFFE
    assert describe(tree).startswith("Cluster { I32, ")
    with pytest.raises(TypeDescError, match="needs more than 65535 bytes"):
        describe(Cluster(0x50, "Cluster", fields=(I32,) * 16383))


@pytest.mark.parametrize("function", FUNCTIONS)
def test_shared_subtrees_are_counted_each_time_and_refused_fast(function: Any) -> None:
    start = time.perf_counter()
    for tree in (
        _shared(40),
        Cluster(0x50, "Cluster", fields=(Cluster(0x50, "Cluster", fields=(I32,) * 2000),) * 400),
    ):
        with pytest.raises(
            TypeDescError,
            match=r"^tree needs more than 65535 bytes, which does not fit the 16-bit length$",
        ):
            function(tree)
    assert time.perf_counter() - start < 2.0


@pytest.mark.parametrize("function", FUNCTIONS)
def test_wide_nodes_count_their_elements_before_any_work(function: Any) -> None:
    quantity = PhysicalQuantity(0x1A, "DBLUnit", units=((1, 1),) * 16000)
    enum = LVEnum(0x15, "EnumU8", items=("",) * 30000)
    dims = Array(0x40, "Array", element=I32, dimensions=(1,) * 16000)
    start = time.perf_counter()
    for wide in (quantity, enum, dims):
        with pytest.raises(TypeDescError, match="needs more than 65535 bytes"):
            function(Cluster(0x50, "Cluster", fields=(wide,) * 400))
    assert time.perf_counter() - start < 1.0


class LyingInt(int):
    def __ge__(self, other: object) -> bool:
        return True

    def __lt__(self, other: object) -> bool:
        return True


class LyingTuple(tuple):  # type: ignore[type-arg]
    def __len__(self) -> int:
        return 0


class LyingBytes(bytes):
    def __len__(self) -> int:
        return 2


class LyingStr(str):
    def __eq__(self, other: object) -> bool:
        return True

    __hash__ = str.__hash__


@pytest.mark.parametrize("function", FUNCTIONS)
@pytest.mark.parametrize(
    ("tree", "message"),
    [
        (LVString(0x30, "String", size=LyingInt(2**40)), "size must be an int, not LyingInt"),
        (Array(0x40, "Array", element=I32, dimensions=(LyingInt(1),)), "dimensions must be"),
        (Scalar(0x03, "I32", flags=LyingInt(1)), "flags must be an int, not LyingInt"),
        (Cluster(0x50, "Cluster", fields=LyingTuple((I32,))), "fields must be a tuple of"),
        (FixedPoint(0x5F, "FXP", payload=LyingBytes(b"x" * 9)), "payload must be bytes"),
        (Scalar(0x03, LyingStr("I32\nX")), "name must be a str, not LyingStr"),
        (LVEnum(0x15, "EnumU8", items=(LyingStr("a"),)), "items must be a tuple of str"),
        (PhysicalQuantity(0x19, "SGLUnit", units=((LyingInt(2), 1),)), "units must be a tuple"),
    ],
)
def test_lying_subclasses_are_refused_as_type_errors(
    function: Any, tree: object, message: str
) -> None:
    with pytest.raises(TypeError, match=message):
        function(tree)


def test_type_code_members_are_accepted_as_codes() -> None:
    assert to_bytes(Scalar(TypeCode.I32, "I32")) == bytes.fromhex("0004 0003")


def test_a_released_memoryview_is_a_type_error() -> None:
    view = memoryview(bytes.fromhex("0004 0003"))
    view.release()
    with pytest.raises(TypeError, match="released"):
        parse_type_descriptor(view)


class Raising(bytearray):
    def __getitem__(self, index: object) -> Any:
        raise RuntimeError("never called")


def test_buffers_are_read_through_the_buffer_protocol() -> None:
    assert parse_type_descriptor(Raising(bytes.fromhex("0004 0003"))) == I32
    wide = memoryview(
        array.array("Q", [int.from_bytes(bytes.fromhex("0004 0003 0000 0000"), "little")])
    )
    assert parse_type_descriptor(wide) == I32
    strided = memoryview(bytes.fromhex("00 FF 04 FF 00 FF 03 FF"))[::2]
    assert parse_type_descriptor(strided) == I32


def _cli(*args: str, **env: str) -> subprocess.CompletedProcess[str]:
    src = str(Path(__file__).resolve().parents[1] / "src")
    full = {**os.environ, "PYTHONPATH": src, **env}
    command = [sys.executable, "-m", "lvtypedesc", *args]
    return subprocess.run(command, capture_output=True, text=True, timeout=60, env=full)


def test_names_the_console_cannot_show_are_escaped() -> None:
    result = _cli(
        "decode", "--tree", "000A 4003 0563 6166 E90A".replace(" ", ""), PYTHONIOENCODING="ascii"
    )
    assert (result.returncode, result.stdout) == (0, "I32 'caf\\xe9\\n'\n")


def test_usage_errors_stay_on_one_line() -> None:
    result = _cli("decode", "00040003", "x\n\x1b[31mINJECT")
    assert result.returncode == 2
    last = result.stderr.splitlines()[-1]
    assert "\x1b" not in result.stderr and "\\x1b" in last and "\\n" in last


@pytest.mark.parametrize("function", FUNCTIONS)
def test_enum_items_count_their_full_length(function: Any) -> None:
    big = LVEnum(0x16, "EnumU16", items=("" * 255,) * 65000)
    with pytest.raises(TypeDescError, match="needs more than 65535 bytes"):
        function(big)
    largest = LVEnum(0x16, "EnumU16", items=("x" * 254,) * 256 + ("x" * 247,))
    assert function(largest)
