"""The code table and layouts against the public references, as fetched by
scripts/fetch_sources.py (copies stay local; tests skip without them)."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

import pytest

from lvtypedesc import describe, known_codes, parse_type_descriptor, pretty
from lvtypedesc._codes import UNSUPPORTED_NAMES

_FOLDER = Path(__file__).resolve().parent / "fixtures" / "sources"
_NI = _FOLDER / "ni-type-descriptors.json"
_WIKI = _FOLDER / "labviewwiki-type-descriptor.html"
needs_sources = pytest.mark.skipif(
    not (_NI.exists() and _WIKI.exists()), reason="run scripts/fetch_sources.py first"
)


def _text(markup: str) -> str:
    plain = html.unescape(re.sub(r"<[^>]+>", " ", markup))
    return re.sub(r"\s+", " ", plain)


def _ni() -> str:
    return _text(json.loads(_NI.read_text(encoding="utf-8"))["topic_html"])


def test_the_manifest_records_every_source() -> None:
    manifest = json.loads((_FOLDER / "MANIFEST.json").read_text(encoding="utf-8"))
    names = {entry["file"] for entry in manifest["files"]}
    assert names == {_NI.name, _WIKI.name}
    for entry in manifest["files"]:
        assert entry["url"].startswith("https://") and len(entry["sha256"]) == 64


@needs_sources
def test_every_code_in_nis_table_is_recognised() -> None:
    ni_codes = {int(code, 16) for code in re.findall(r"\bxx ([0-9A-F]{2})\b", _ni())}
    assert len(ni_codes) >= 30
    assert ni_codes <= {code for code, _, _ in known_codes()}


@needs_sources
def test_every_recognised_or_refused_code_is_in_the_wiki_list() -> None:
    wiki = {int(c, 16) for c in re.findall(r"\b0x([0-9A-F]{2})\b", _text(_WIKI.read_text("utf-8")))}
    assert {code for code, _, _ in known_codes()} <= wiki
    assert set(UNSUPPORTED_NAMES) <= wiki


_EXAMPLES = {
    "0016 0015 0003 0261 6D02 666D 0966 6D20 7374 6572 656F": "EnumU8 (3 items)",
    "001C 4015 0003 0261 6D02 666D 0966 6D20 7374 6572 656F 0572 6164 696F": "EnumU8 (3 items)",
    "000E 001A 0002 0002 FFFF 0003 0001": "DBLUnit [s^-1 m]",
    "000E 0040 0001 FFFF FFFF 0004 000A": "1D Array of DBL",
    "0012 0040 0002 FFFF FFFF FFFF FFFF 0004 0021": "2D Array of Boolean",
    "000E 0050 0002 0004 0002 0004 0007": "Cluster { I16, U32 }",
}


@needs_sources
@pytest.mark.parametrize("example", sorted(_EXAMPLES))
def test_nis_printed_examples_read_as_ni_explains_them(example: str) -> None:
    assert example in _ni()
    node = parse_type_descriptor(bytes.fromhex(example))
    assert describe(node) == _EXAMPLES[example]


@needs_sources
def test_nis_named_enum_example_carries_its_name() -> None:
    named = "001C 4015 0003 0261 6D02 666D 0966 6D20 7374 6572 656F 0572 6164 696F"
    node = parse_type_descriptor(bytes.fromhex(named))
    assert pretty(node) == "EnumU8 (3 items: 'am', 'fm', 'fm stereo') 'radio'"
