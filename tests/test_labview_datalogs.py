"""Ground truth: type descriptors LabVIEW 2026 itself wrote (front-panel datalog files)."""

from __future__ import annotations

import hashlib

import pytest
from datalog import (
    FLAT_CONTAINERS,
    FOLDER,
    datalogs,
    leaves,
    manifest,
    nest,
    refs,
    table,
    uses_typedef,
)

from lvtypedesc import (
    VARIABLE,
    Array,
    Boolean,
    Cluster,
    FixedPoint,
    LVEnum,
    LVString,
    LVVariant,
    Refnum,
    Scalar,
    TypeDesc,
    TypeDescError,
    Waveform,
    describe,
    parse_type_descriptor,
    to_bytes,
)


@pytest.mark.parametrize("name", sorted(manifest()))
def test_every_capture_matches_its_manifest(name: str) -> None:
    data = (FOLDER / name).read_bytes()
    entry = manifest()[name]
    assert len(data) == entry["size"]
    assert hashlib.sha256(data).hexdigest() == entry["sha256"]


def _pstr_at_end(td: bytes) -> str:
    """The name LabVIEW appended, found by walking pstr candidates (test-side reading)."""
    for start in range(4, len(td)):
        if start % 2 == 0 and start + 1 + td[start] in (len(td), len(td) - 1):
            return td[start + 1 : start + 1 + td[start]].decode("latin-1")
    raise AssertionError("no name")


@pytest.mark.parametrize("name", datalogs())
def test_every_leaf_parses_and_is_written_back_byte_for_byte(name: str) -> None:
    for td in leaves(name):
        node = parse_type_descriptor(td)
        assert to_bytes(node) == td
        assert node.flags == td[2]
        if td[2] & 0x40 and not isinstance(node, (FixedPoint, Refnum, Waveform)):
            assert node.label == _pstr_at_end(td)


@pytest.mark.parametrize("name", datalogs())
def test_rebuilt_containers_parse_to_their_parsed_leaves(name: str) -> None:
    entries = table(name)
    checked = 0
    for index, td in enumerate(entries):
        if td[3] not in FLAT_CONTAINERS or uses_typedef(entries, index):
            continue
        nested = nest(entries, index)
        node = parse_type_descriptor(nested)
        assert to_bytes(node) == nested
        inner = tuple(parse_type_descriptor(nest(entries, ref)) for ref in refs(td)[1])
        if isinstance(node, Array):
            assert (node.element,) == inner
        else:
            assert isinstance(node, Cluster)
            assert node.fields == inner
        checked += 1
    assert checked >= 1


@pytest.mark.parametrize("name", datalogs())
def test_typedefs_are_refused_by_name(name: str) -> None:
    for td in table(name):
        if td[3] == 0xF1:
            with pytest.raises(TypeDescError, match="unsupported type Typedef 0xf1"):
                parse_type_descriptor(td)


def _node(name: str, index: int) -> TypeDesc:
    return parse_type_descriptor(nest(table(name), index))


def test_the_error_cluster_reads_as_labview_names_it() -> None:
    node = _node("Error_Cluster_From_Error_Code.dat", 6)
    assert node == Cluster(
        0x50,
        "Cluster",
        label="error out",
        fields=(
            Boolean(0x21, "Boolean", label="status"),
            Scalar(0x03, "I32", label="code"),
            LVString(0x30, "String", label="source", size=VARIABLE),
        ),
    )


def test_a_one_dimensional_array_of_i32_with_its_name() -> None:
    node = _node("Find_First_Error.dat", 6)
    assert node == Array(
        0x40,
        "Array",
        label="error codes",
        dimensions=(VARIABLE,),
        element=Scalar(0x03, "I32", label="  "),
    )


def test_a_two_dimensional_array_of_i16() -> None:
    node = _node("Read_File_I16.dat", 18)
    assert isinstance(node, Array)
    assert (node.label, node.dimensions, node.element) == (
        "2D data",
        (VARIABLE, VARIABLE),
        Scalar(0x02, "I16"),
    )


def test_a_standalone_enum_and_a_file_refnum() -> None:
    entries = table("Read_File_I16.dat")
    enum = parse_type_descriptor(entries[9])
    assert enum == LVEnum(
        0x16, "EnumU16", label="pos mode (rel. to current:2)", items=("start", "end", "current")
    )
    refnum = parse_type_descriptor(entries[8])
    assert isinstance(refnum, Refnum)
    assert (refnum.subtype, refnum.payload) == (2, b"\x00\x02\x06refnum\x00")


def test_paths_variants_and_time_stamps() -> None:
    path = parse_type_descriptor(table("Is_Path_and_Not_Empty.dat")[3])
    assert path == LVString(0x32, "Path", label="path", size=VARIABLE)
    variant = parse_type_descriptor(table("GetTypeInfo.dat")[3])
    assert variant == LVVariant(0x53, "Variant", label="Variant")
    stamp = parse_type_descriptor(table("Set_Refnum_Access_and_Modification_Time.dat")[3])
    assert isinstance(stamp, Waveform)
    assert (stamp.subtype, describe(stamp)) == (6, "Timestamp")


def test_fixed_point_payloads_are_kept_whole() -> None:
    entries = table("Fixed_Point_Cast.dat")
    fxps = [parse_type_descriptor(td) for td in entries if td[3] == 0x5F]
    assert len(fxps) == 5
    for node in fxps:
        assert isinstance(node, FixedPoint)
        assert node.label is None and node.flags == 0x40
        assert node.payload.endswith(b">") or node.payload.endswith(b">\x00")
    assert parse_type_descriptor(entries[4]) == Scalar(0x01, "I8", label="I8")
