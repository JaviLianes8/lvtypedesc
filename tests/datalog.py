"""Test helper: read the type descriptor table at the start of a LabVIEW datalog file.

A datalog (and a flattened variant) stores its types as a flat list: every descriptor is
written once and an array or cluster names its elements by index into the list. This
library parses the nested form, where elements are written inline, so `nest` rebuilds the
nested form of a flat entry. The table layout (a 32-bit count at offset 16, then the
descriptors back to back) is read from the files LabVIEW wrote, not from a document.
"""

from __future__ import annotations

import json
from pathlib import Path

FOLDER = Path(__file__).resolve().parent / "fixtures" / "labview2026"
FLAT_CONTAINERS = (0x40, 0x50)


def manifest() -> dict[str, dict[str, object]]:
    files = json.loads((FOLDER / "manifest.json").read_text(encoding="utf-8"))["files"]
    assert isinstance(files, dict)
    return files


def datalogs() -> list[str]:
    return sorted(name for name in manifest() if name.endswith(".dat"))


def table(name: str) -> list[bytes]:
    """The descriptors of a datalog file, in table order."""
    data = (FOLDER / name).read_bytes()
    assert data[:4] == b"DTLG"
    count = int.from_bytes(data[16:20], "big")
    pos, out = 20, []
    for _ in range(count):
        length = int.from_bytes(data[pos : pos + 2], "big")
        out.append(data[pos : pos + length])
        pos += length
    return out


def leaves(name: str) -> list[bytes]:
    """Entries that hold no index references (everything but arrays and clusters)."""
    return [td for td in table(name) if td[3] not in FLAT_CONTAINERS and td[3] != 0xF1]


def _pad(chunk: bytes) -> bytes:
    return chunk + b"\x00" * (len(chunk) % 2)


def refs(td: bytes) -> tuple[int, list[int]]:
    """Where the index references of a flat array or cluster start, and the indexes."""
    if td[3] == 0x40:
        fixed = 6 + 4 * int.from_bytes(td[4:6], "big")
        return fixed, [int.from_bytes(td[fixed : fixed + 2], "big")]
    count = int.from_bytes(td[4:6], "big")
    return 6, [int.from_bytes(td[6 + 2 * i : 8 + 2 * i], "big") for i in range(count)]


def nest(entries: list[bytes], index: int) -> bytes:
    """Rebuild entry ``index`` in the nested form, its elements written inline."""
    td = entries[index]
    if td[3] not in FLAT_CONTAINERS:
        return td
    fixed, indexes = refs(td)
    inner = b"".join(nest(entries, ref) for ref in indexes)
    body = _pad(td[4:fixed] + inner)
    name = td[fixed + 2 * len(indexes) :]  # the appended name and its padding, unchanged
    total = 4 + len(body) + len(name)
    return total.to_bytes(2, "big") + td[2:4] + body + name


def uses_typedef(entries: list[bytes], index: int) -> bool:
    """Whether entry ``index`` is, or holds, a typedef (which this library refuses)."""
    td = entries[index]
    if td[3] == 0xF1:
        return True
    if td[3] not in FLAT_CONTAINERS:
        return False
    return any(uses_typedef(entries, ref) for ref in refs(td)[1])
