"""Packaging and house rules: metadata, links, version, line limits, no em-dash."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import pytest

import lvtypedesc

_ROOT = Path(__file__).resolve().parents[1]
needs_tomllib = pytest.mark.skipif(sys.version_info < (3, 11), reason="tomllib is 3.11+")


def _project() -> dict[str, Any]:
    if sys.version_info >= (3, 11):
        import tomllib

        data = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        project: dict[str, Any] = data["project"]
        return project
    raise AssertionError("tomllib is 3.11+")  # pragma: no cover


@needs_tomllib
def test_metadata_is_stable_and_dependency_free() -> None:
    project = _project()
    assert project["version"] == lvtypedesc.__version__ == "1.0.0"
    assert project["dependencies"] == []
    assert project["requires-python"] == ">=3.10"
    assert "Development Status :: 5 - Production/Stable" in project["classifiers"]
    minors = [
        c.rsplit(".", 1)[1]
        for c in project["classifiers"]
        if re.fullmatch(r"Programming Language :: Python :: 3\.\d+", c)
    ]
    assert minors == ["10", "11", "12", "13", "14"]
    assert {"Homepage", "Source", "Issues", "Changelog"} <= set(project["urls"])
    assert project["keywords"]
    assert project["scripts"] == {"lvtypedesc": "lvtypedesc._cli:main"}


def test_readme_links_are_absolute_and_reach_the_guide_and_changelog() -> None:
    readme = (_ROOT / "README.md").read_text(encoding="utf-8")
    links = re.findall(r"\]\(([^)]+)\)", readme)
    assert links and all(link.startswith("https://") for link in links)
    assert "https://github.com/JaviLianes8/lvtypedesc/blob/main/GUIDE.md" in links
    assert "https://github.com/JaviLianes8/lvtypedesc/blob/main/CHANGELOG.md" in links


def test_changelog_has_a_dated_section_for_this_version() -> None:
    changelog = (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    pattern = rf"^## \[{re.escape(lvtypedesc.__version__)}\] - \d{{4}}-\d{{2}}-\d{{2}}$"
    assert re.search(pattern, changelog, re.M)


def _sources() -> list[Path]:
    found = [*(_ROOT / "src").rglob("*.py"), *(_ROOT / "tests").glob("*.py")]
    return [p for p in found if "__pycache__" not in p.parts]


def test_source_and_test_files_stay_within_200_lines() -> None:
    long = [p.name for p in _sources() if len(p.read_text(encoding="utf-8").splitlines()) > 200]
    assert long == []


def test_no_em_dash_anywhere_in_the_package_or_docs() -> None:
    docs = [_ROOT / n for n in ("README.md", "GUIDE.md", "CHANGELOG.md", "CONTRIBUTING.md")]
    for path in [*_sources(), *docs, _ROOT / "pyproject.toml"]:
        if path.exists():
            assert chr(0x2014) not in path.read_text(encoding="utf-8"), path.name


def test_the_package_ships_type_information() -> None:
    assert (Path(lvtypedesc.__file__).parent / "py.typed").is_file()
