"""Real end-to-end test.

Installs the package editable and drives the actual ``lvtypedesc`` console script
through a subprocess, asserting real stdout and exit codes. Unit coverage of
``main`` does not prove the installed entry point works, so this does.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def _console_script() -> str | None:
    found = shutil.which("lvtypedesc")
    if found:
        return found
    scripts = sysconfig.get_path("scripts")
    for name in ("lvtypedesc.exe", "lvtypedesc"):
        candidate = os.path.join(scripts, name)
        if os.path.exists(candidate):
            return candidate
    return None


@pytest.fixture(scope="module")
def script() -> str:
    install = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", str(_ROOT), "--quiet"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert install.returncode == 0, install.stderr
    path = _console_script()
    assert path is not None, "the lvtypedesc console script was not installed"
    return path


def _run(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([script, *args], capture_output=True, text=True, timeout=60)


def test_installed_script_decodes_a_scalar(script: str) -> None:
    result = _run(script, "decode", "00040003")
    assert result.returncode == 0
    assert result.stdout.strip() == "I32"


def test_installed_script_decodes_a_nested_tree(script: str) -> None:
    result = _run(script, "decode", "000E00400001FFFFFFFF0004000A")
    assert result.returncode == 0
    assert result.stdout.strip() == "1D Array of DBL"


def test_installed_script_lists_codes(script: str) -> None:
    result = _run(script, "codes")
    assert result.returncode == 0
    assert "0x0A  DBL" in result.stdout
    assert "0x5F  FXP" in result.stdout


def test_installed_script_reports_version(script: str) -> None:
    import lvtypedesc

    result = _run(script, "--version")
    assert result.returncode == 0
    assert result.stdout.strip() == f"lvtypedesc {lvtypedesc.__version__}"


def test_installed_script_errors_to_stderr(script: str) -> None:
    result = _run(script, "decode", "00040099")
    assert result.returncode == 1
    assert result.stdout == ""
    assert "unknown type code" in result.stderr
