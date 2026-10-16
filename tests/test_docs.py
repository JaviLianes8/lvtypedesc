"""The documentation is executable: doctests, README and GUIDE examples, CLI transcripts."""

from __future__ import annotations

import doctest
import importlib
import inspect
import pkgutil
import re
import shlex
import typing
from pathlib import Path

import pytest

import lvtypedesc
from lvtypedesc._cli import main

_ROOT = Path(__file__).resolve().parents[1]
_MODULES = ["lvtypedesc"] + [
    f"lvtypedesc.{m.name}"
    for m in pkgutil.iter_modules(lvtypedesc.__path__)
    if m.name != "__main__"
]


@pytest.mark.parametrize("name", _MODULES)
def test_module_doctests_pass(name: str) -> None:
    result = doctest.testmod(importlib.import_module(name))
    assert result.failed == 0


@pytest.mark.parametrize("name", lvtypedesc.__all__)
def test_every_public_name_documents_an_example(name: str) -> None:
    finder = doctest.DocTestFinder()
    examples = "".join(
        example.source
        for module in _MODULES
        for test in finder.find(importlib.import_module(module))
        for example in test.examples
    )
    assert re.search(rf"\b{name}\b", examples), name
    target = getattr(lvtypedesc, name)
    if inspect.isclass(target) or inspect.isfunction(target):
        assert ">>>" in (target.__doc__ or ""), name


@pytest.mark.parametrize("name", ["Array", "Refnum", "Waveform"])
def test_properties_document_an_example(name: str) -> None:
    for member in vars(getattr(lvtypedesc, name)).values():
        if isinstance(member, property):
            assert ">>>" in (member.__doc__ or "")


@pytest.mark.parametrize(
    "name", [n for n in lvtypedesc.__all__ if callable(getattr(lvtypedesc, n))]
)
def test_type_hints_resolve_at_run_time(name: str) -> None:
    target = getattr(lvtypedesc, name)
    typing.get_type_hints(target)


@pytest.mark.parametrize("doc", ["README.md", "GUIDE.md"])
def test_pycon_examples_run_and_print_what_they_show(doc: str) -> None:
    text = (_ROOT / doc).read_text(encoding="utf-8")
    blocks = re.findall(r"```pycon\n(.*?)```", text, re.S)
    assert blocks
    parser, runner = doctest.DocTestParser(), doctest.DocTestRunner()
    session: dict[str, object] = {}
    for number, block in enumerate(blocks):
        test = parser.get_doctest(block, session, f"{doc}[{number}]", doc, 0)
        runner.run(test, clear_globs=False)
        session.update(test.globs)
    assert runner.summarize(verbose=False).failed == 0


def _transcripts() -> list[tuple[list[str], list[str]]]:
    runs: list[tuple[list[str], list[str]]] = []
    for doc in ("README.md", "GUIDE.md"):
        text = (_ROOT / doc).read_text(encoding="utf-8")
        for block in re.findall(r"```\n(\$ lvtypedesc .*?)```", text, re.S):
            for line in block.splitlines():
                if line.startswith("$ lvtypedesc "):
                    runs.append((shlex.split(line)[2:], []))
                else:
                    runs[-1][1].append(line)
    return runs


@pytest.mark.parametrize(("args", "expected"), _transcripts())
def test_command_transcripts_match(
    capsys: pytest.CaptureFixture[str], args: list[str], expected: list[str]
) -> None:
    assert main(args) == 0
    assert capsys.readouterr().out.splitlines() == expected


def test_every_transcript_is_checked() -> None:
    assert len(_transcripts()) == 5
