"""Seeded fuzzing: hostile input never crashes, hangs or grows quadratically."""

from __future__ import annotations

import contextlib
import random
import time

import pytest
from datalog import datalogs, leaves, nest, table, uses_typedef

from lvtypedesc import TypeDescError, describe, parse_type_descriptor, pretty, to_bytes


def _corpus() -> list[bytes]:
    out: list[bytes] = []
    for name in datalogs():
        out.extend(leaves(name))
        entries = table(name)
        out.extend(
            nest(entries, i)
            for i, td in enumerate(entries)
            if td[3] in (0x40, 0x50) and not uses_typedef(entries, i)
        )
    return out


CORPUS = _corpus()


def _check(data: bytes) -> None:
    try:
        node = parse_type_descriptor(data)
    except TypeDescError as exc:
        assert len(str(exc)) < 120
        return
    describe(node)
    pretty(node)
    written = to_bytes(node)
    assert parse_type_descriptor(written) == node
    assert to_bytes(parse_type_descriptor(written)) == written


@pytest.mark.parametrize("seed", range(8))
def test_mutated_real_descriptors_only_raise_type_desc_error(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(1500):
        data = bytearray(rng.choice(CORPUS))
        for _ in range(rng.randint(1, 4)):
            action = rng.random()
            position = rng.randrange(len(data) + 1)
            if action < 0.5 and data:
                data[min(position, len(data) - 1)] = rng.randrange(256)
            elif action < 0.75:
                data[position:position] = bytes([rng.randrange(256)])
            elif data:
                del data[min(position, len(data) - 1)]
        _check(bytes(data))


@pytest.mark.parametrize("seed", range(4))
def test_random_bytes_only_raise_type_desc_error(seed: int) -> None:
    rng = random.Random(1000 + seed)
    for _ in range(3000):
        size = rng.randrange(40)
        head = bytes((0, rng.randrange(4, 40), rng.choice((0, 0x40, 0x80)), rng.randrange(256)))
        _check(head + rng.randbytes(size))


def _time(data: bytes) -> float:
    start = time.perf_counter()
    for _ in range(3):
        with contextlib.suppress(TypeDescError):
            parse_type_descriptor(data)
    return time.perf_counter() - start


def test_the_largest_inputs_are_read_in_linear_time() -> None:
    small = (
        (0x0FFE).to_bytes(2, "big")
        + bytes.fromhex("0050 03FE")
        + bytes.fromhex("0004 0003") * 0x3FE
    )
    large = (
        (0xFFFE).to_bytes(2, "big")
        + bytes.fromhex("0050 3FFE")
        + bytes.fromhex("0004 0003") * 0x3FFE
    )
    assert len(parse_type_descriptor(large).fields) == 0x3FFE  # type: ignore[attr-defined]
    assert _time(large) < 40 * _time(small) + 0.5


def test_huge_counts_fail_fast() -> None:
    data = bytes.fromhex("FFFF 0050 FFFF") + bytes(0xFFF9)
    assert _time(data) < 1.0
    with pytest.raises(TypeDescError):
        parse_type_descriptor(data)


def test_trailing_megabytes_are_not_read() -> None:
    data = bytes.fromhex("0004 0003") + bytes(50_000_000)
    assert _time(data) < 2.0
