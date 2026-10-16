"""Ground truth: LabVIEW's own type-descriptor VIs (vi.lib GetType.llb) read and build
the same nested descriptors, and agree with this library on every one."""

from __future__ import annotations

import json
from typing import Any

import pytest
from datalog import FOLDER

from lvtypedesc import (
    VARIABLE,
    Array,
    Cluster,
    LVEnum,
    LVString,
    PhysicalQuantity,
    Refnum,
    TypeDesc,
    parse_type_descriptor,
    to_bytes,
)

_DOC = json.loads((FOLDER / "gettype.json").read_text(encoding="utf-8"))
_RESULTS: dict[str, dict[str, Any]] = {r["id"]: r for r in _DOC["results"]}


def _by_vi(vi: str) -> list[str]:
    return [key for key, r in _RESULTS.items() if r["vi"] == vi]


def _parse(ident: str) -> TypeDesc:
    return parse_type_descriptor(bytes.fromhex(_RESULTS[ident]["hex"]))


def _words(values: list[int]) -> bytes:
    return b"".join((v & 0xFFFF).to_bytes(2, "big") for v in values)


def _offsets(data: bytes, start: int, count: int) -> list[int]:
    """Word offsets of ``count`` consecutive descriptors starting at byte ``start``."""
    out = []
    for _ in range(count):
        out.append(start // 2)
        start += int.from_bytes(data[start : start + 2], "big")
    return out


def test_the_capture_is_from_labview_2026() -> None:
    assert _DOC["labview"] == "26.3.1f1"
    assert len(_RESULTS) == 25


@pytest.mark.parametrize("ident", _by_vi("TD_Get Array Information.vi"))
def test_arrays_agree_with_labview(ident: str) -> None:
    node, result = _parse(ident), _RESULTS[ident]
    assert isinstance(node, Array)
    assert result["Number of Dimensions"] == [node.rank]
    assert result["Dim Sizes"] == [list(node.dimensions)]
    data = bytes.fromhex(result["hex"])
    offset = result["Contained TD Offset"][0] * 2
    assert parse_type_descriptor(data[offset:]) == node.element


@pytest.mark.parametrize("ident", _by_vi("TD_Get Cluster Information.vi"))
def test_clusters_agree_with_labview(ident: str) -> None:
    node, result = _parse(ident), _RESULTS[ident]
    assert isinstance(node, Cluster)
    assert result["Number of Elements"] == [len(node.fields)]
    data = bytes.fromhex(result["hex"])
    assert result["Contained TD Offsets"] == [_offsets(data, 6, len(node.fields))]


@pytest.mark.parametrize("ident", _by_vi("TD_Get Enum Information.vi"))
def test_enums_agree_with_labview(ident: str) -> None:
    node, result = _parse(ident), _RESULTS[ident]
    assert isinstance(node, LVEnum)
    assert result["Number of Values"] == [len(node.items)]
    assert result["Value Names"] == [list(node.items)]


@pytest.mark.parametrize("ident", _by_vi("TD_Get Unit Information.vi"))
def test_units_agree_with_labview(ident: str) -> None:
    node, result = _parse(ident), _RESULTS[ident]
    assert isinstance(node, PhysicalQuantity)
    assert result["N Units"] == [len(node.units)]
    assert result["Base Units"] == [[base for base, _ in node.units]]
    assert result["Base Exponents"] == [[exponent for _, exponent in node.units]]


@pytest.mark.parametrize("ident", _by_vi("TD_Get StringLike Information.vi"))
def test_string_sizes_agree_with_labview(ident: str) -> None:
    node, result = _parse(ident), _RESULTS[ident]
    assert isinstance(node, LVString)
    assert result["Max Length (-1 for Unbounded)"] == [node.size]


def test_refnum_kind_agrees_with_labview() -> None:
    node = _parse("refnum_file")
    assert isinstance(node, Refnum)
    assert _RESULTS["refnum_file"]["Refnum Type"] == [node.subtype]


def test_named_examples_carry_their_names() -> None:
    assert _parse("enum_radio_named").label == "radio"
    assert _parse("array_fixed_3d").label == "gid"
    assert _parse("path_named").label == "path"
    cluster = _parse("cluster_named")
    assert isinstance(cluster, Cluster)
    assert [f.label for f in cluster.fields] == ["n", "ok", None]


@pytest.mark.parametrize("ident", _by_vi("TD_Create Cluster.vi"))
def test_clusters_labview_builds_are_what_to_bytes_writes(ident: str) -> None:
    result = _RESULTS[ident]
    built = _words(result["ClusterTD"][0])
    elements = bytes.fromhex(result["hex"])
    fields, pos = [], 0
    while pos < len(elements):
        fields.append(parse_type_descriptor(elements[pos:]))
        pos += int.from_bytes(elements[pos : pos + 2], "big")
    node = parse_type_descriptor(built)
    assert isinstance(node, Cluster)
    assert node.fields == tuple(fields)
    assert to_bytes(Cluster(0x50, "Cluster", fields=tuple(fields), label=node.label)) == built


@pytest.mark.parametrize("ident", _by_vi("TD_Create Array.vi"))
def test_arrays_labview_builds_are_what_to_bytes_writes(ident: str) -> None:
    result = _RESULTS[ident]
    built = _words(result["NewArray"][0])
    element = parse_type_descriptor(bytes.fromhex(result["hex"]))
    node = parse_type_descriptor(built)
    assert isinstance(node, Array)
    assert node.element == element
    assert set(node.dimensions) == {VARIABLE}
    expected = Array(0x40, "Array", element=element, dimensions=node.dimensions, label=node.label)
    assert to_bytes(expected) == built


def test_labview_names_built_descriptors_as_asked() -> None:
    names = {
        key: parse_type_descriptor(_words((r.get("ClusterTD") or r["NewArray"])[0])).label
        for key, r in _RESULTS.items()
        if key.startswith("make_")
    }
    assert names == {
        "make_cluster": None,
        "make_cluster_named": "abc",
        "make_cluster_even_name": "ab",
        "make_cluster_one": "status",
        "make_array": None,
        "make_array_2d_named": "ab",
        "make_array_of_cluster": "rows",
    }
