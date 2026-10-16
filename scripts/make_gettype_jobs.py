"""Write the job list for scripts/capture-labview-gettype.ps1.

Every descriptor below is hand-written hex (labelled so in the captured file). Those marked
"NI example" are the sample descriptors printed on NI's Type Descriptors page:
https://www.ni.com/docs/en-US/bundle/labview/page/type-descriptors.html

    python scripts/make_gettype_jobs.py jobs.json
"""

from __future__ import annotations

import json
import sys

READ_ARRAY = ["Number of Dimensions", "Dim Sizes", "Contained TD Offset"]
READ_CLUSTER = ["Number of Elements", "Contained TD Offsets"]
READ_ENUM = ["Number of Values", "Value Names"]
READ_UNIT = ["N Units", "Base Units", "Base Exponents"]
READ_STRING = ["Max Length (-1 for Unbounded)"]
READ_REFNUM = ["Refnum Type"]

# (id, VI, descriptor hex, outputs, extra inputs)
READERS: list[tuple[str, str, str, list[str], dict[str, object]]] = [
    (
        "array_dbl",
        "TD_Get Array Information.vi",
        "000E 0040 0001 FFFFFFFF 0004 000A",
        READ_ARRAY,
        {},
    ),
    (
        "array_bool_2d",
        "TD_Get Array Information.vi",
        "0012 0040 0002 FFFFFFFF FFFFFFFF 0004 0021",
        READ_ARRAY,
        {},
    ),
    (
        "array_fixed_3d",
        "TD_Get Array Information.vi",
        "001A 4040 0003 00000002 00000003 00000004 0004 0002 0367 6964",
        READ_ARRAY,
        {},
    ),
    (
        "array_of_cluster",
        "TD_Get Array Information.vi",
        "001C 0040 0001 FFFFFFFF 0012 0050 0002 0004 0003 0008 0030 FFFFFFFF",
        READ_ARRAY,
        {},
    ),
    (
        "cluster_i16_u32",
        "TD_Get Cluster Information.vi",
        "000E 0050 0002 0004 0002 0004 0007",
        READ_CLUSTER,
        {},
    ),
    (
        "cluster_named",
        "TD_Get Cluster Information.vi",
        "0020 4050 0003 0006 4003 016E 0008 4021 026F 6B00 0008 0030 FFFFFFFF 0361 6263",
        READ_CLUSTER,
        {},
    ),
    (
        "cluster_nested",
        "TD_Get Cluster Information.vi",
        "0018 0050 0002 000E 0050 0002 0004 0001 0004 0005 0004 000A",
        READ_CLUSTER,
        {},
    ),
    ("cluster_empty", "TD_Get Cluster Information.vi", "0006 0050 0000", READ_CLUSTER, {}),
    (
        "enum_radio",
        "TD_Get Enum Information.vi",
        "0016 0015 0003 0261 6D02 666D 0966 6D20 7374 6572 656F",
        READ_ENUM,
        {},
    ),
    (
        "enum_radio_named",
        "TD_Get Enum Information.vi",
        "001C 4015 0003 0261 6D02 666D 0966 6D20 7374 6572 656F 0572 6164 696F",
        READ_ENUM,
        {},
    ),
    (
        "enum_odd_named",
        "TD_Get Enum Information.vi",
        "0012 4016 0002 0141 0242 4300 0478 7979 7A00",
        READ_ENUM,
        {},
    ),
    ("enum_u32_one", "TD_Get Enum Information.vi", "000A 0017 0001 0130 0000", READ_ENUM, {}),
    (
        "unit_m_per_s",
        "TD_Get Unit Information.vi",
        "000E 001A 0002 0002 FFFF 0003 0001",
        READ_UNIT,
        {},
    ),
    (
        "unit_three",
        "TD_Get Unit Information.vi",
        "0012 0019 0003 0004 0001 0003 0002 0002 FFFE",
        READ_UNIT,
        {},
    ),
    ("string_var", "TD_Get StringLike Information.vi", "0008 0030 FFFFFFFF", READ_STRING, {}),
    (
        "path_named",
        "TD_Get StringLike Information.vi",
        "000E 4032 FFFFFFFF 0470 6174 6800",
        READ_STRING,
        {},
    ),
    ("picture_fixed", "TD_Get StringLike Information.vi", "0008 0033 00000010", READ_STRING, {}),
    ("refnum_file", "TD_Get Ref Info.vi", "000E 4070 0002 0672 6566 6E75 6D00", READ_REFNUM, {}),
]

# (id, VI, element descriptors hex, count or rank, name, extra)
CREATORS: list[tuple[str, str, str, int, str]] = [
    ("make_cluster", "TD_Create Cluster.vi", "0004 0003 0004 000A", 2, ""),
    ("make_cluster_named", "TD_Create Cluster.vi", "0004 0003 0004 000A", 2, "abc"),
    (
        "make_cluster_even_name",
        "TD_Create Cluster.vi",
        "0006 4003 016E 0008 0030 FFFFFFFF",
        2,
        "ab",
    ),
    ("make_cluster_one", "TD_Create Cluster.vi", "0004 0021", 1, "status"),
    ("make_array", "TD_Create Array.vi", "0004 000A", 1, ""),
    ("make_array_2d_named", "TD_Create Array.vi", "0004 0021", 2, "ab"),
    (
        "make_array_of_cluster",
        "TD_Create Array.vi",
        "000E 0050 0002 0004 0003 0004 000A",
        1,
        "rows",
    ),
]


def words(hex_text: str) -> list[int]:
    raw = bytes.fromhex(hex_text)
    return [int.from_bytes(raw[i : i + 2], "big", signed=True) for i in range(0, len(raw), 2)]


def jobs() -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for ident, vi, hex_text, outputs, extra in READERS:
        inputs: dict[str, object] = {"Type descriptor": {"t": "i16a", "v": words(hex_text)}}
        inputs.update({name: {"t": "i32", "v": value} for name, value in extra.items()})
        out.append({"id": ident, "vi": vi, "hex": hex_text, "inputs": inputs, "outputs": outputs})
    for ident, vi, hex_text, count, name in CREATORS:
        cluster = vi == "TD_Create Cluster.vi"
        inputs = {
            ("Concatenated Elts" if cluster else "Array Elt"): {"t": "i16a", "v": words(hex_text)},
            ("N Elts" if cluster else "N Dims"): {"t": "i32", "v": count},
            "Name": {"t": "str", "v": name},
        }
        output = ["ClusterTD" if cluster else "NewArray"]
        out.append({"id": ident, "vi": vi, "hex": hex_text, "inputs": inputs, "outputs": output})
    return out


if __name__ == "__main__":
    with open(sys.argv[1], "w", encoding="utf-8") as handle:
        json.dump(jobs(), handle, indent=1)
