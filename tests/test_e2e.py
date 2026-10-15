"""Real end-to-end: build a wheel, install it into a throwaway venv, run its console script.

Nothing is imported from the source tree here: every check shells out to the script pip
generated in a fresh virtual environment. Set LVTYPEDESC_WHEEL to test a built wheel.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import venv
import zipfile
from pathlib import Path

import pytest
from datalog import table

_ROOT = Path(__file__).resolve().parents[1]
_LEAKY = ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "PYTHONSTARTUP")
_ENV = {key: value for key, value in os.environ.items() if key.upper() not in _LEAKY}


def _wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    given = os.environ.get("LVTYPEDESC_WHEEL")
    if given:
        return Path(given)
    if not (_ROOT / "src" / "lvtypedesc" / "__init__.py").is_file():
        pytest.skip("no source tree to build from; set LVTYPEDESC_WHEEL to a built wheel")
    wheels = tmp_path_factory.mktemp("wheels")
    build = [sys.executable, "-m", "pip", "wheel", "--quiet", "--no-deps"]
    if importlib.util.find_spec("hatchling") is not None:
        build.append("--no-build-isolation")
    subprocess.run([*build, "-w", str(wheels), str(_ROOT)], check=True, timeout=600, env=_ENV)
    (wheel,) = wheels.glob("lvtypedesc-*.whl")
    return wheel


@pytest.fixture(scope="module")
def env(tmp_path_factory: pytest.TempPathFactory) -> Path:
    wheel = _wheel(tmp_path_factory)
    with zipfile.ZipFile(wheel) as archive:
        assert "lvtypedesc/py.typed" in archive.namelist()
    env_dir = tmp_path_factory.mktemp("venv")
    venv.EnvBuilder(with_pip=True).create(env_dir)
    scripts = env_dir / ("Scripts" if os.name == "nt" else "bin")
    install = [str(scripts / "python"), "-m", "pip", "install", "--quiet", "--no-index"]
    subprocess.run([*install, "--no-deps", str(wheel)], check=True, timeout=600, env=_ENV)
    return scripts


def _run(
    command: list[str], cwd: Path | None = None, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command, capture_output=True, text=True, timeout=120, env=env or _ENV, cwd=cwd
    )


def _script(env: Path) -> str:
    found = shutil.which("lvtypedesc", path=str(env))
    assert found is not None, "pip did not install the lvtypedesc console script"
    return found


def test_the_package_comes_from_the_venv(env: Path) -> None:
    result = _run([str(env / "python"), "-c", "import lvtypedesc; print(lvtypedesc.__file__)"])
    assert Path(result.stdout.strip()).resolve().is_relative_to(env.parent.resolve())


def test_the_script_decodes_what_labview_wrote(env: Path) -> None:
    error_cluster = table("Error_Cluster_From_Error_Code.dat")[3]  # Boolean "status"
    result = _run([_script(env), "decode", "--tree", error_cluster.hex()])
    assert (result.returncode, result.stdout, result.stderr) == (0, "Boolean 'status'\n", "")


def test_python_dash_m_and_version(env: Path) -> None:
    result = _run(
        [str(env / "python"), "-m", "lvtypedesc", "decode", "000E00400001FFFFFFFF0004000A"]
    )
    assert (result.returncode, result.stdout) == (0, "1D Array of DBL\n")
    version = _run([_script(env), "--version"])
    assert version.stdout == "lvtypedesc 1.0.0\n"


def test_exit_codes_and_messages(env: Path) -> None:
    bad = _run([_script(env), "decode", "00040099"])
    assert (bad.returncode, bad.stdout, bad.stderr) == (
        1,
        "",
        "lvtypedesc: error: unknown type code 0x99 at offset 0\n",
    )
    usage = _run([_script(env), "frobnicate"])
    assert usage.returncode == 2 and usage.stderr.startswith("usage: lvtypedesc")


def test_a_reader_that_goes_away_gives_exit_one_without_a_traceback(env: Path) -> None:
    code = (
        "import subprocess, sys\n"
        "p = subprocess.Popen([sys.argv[1], 'codes'], stdout=subprocess.PIPE,"
        " stderr=subprocess.PIPE)\n"
        "p.stdout.close()\n"
        "err = p.stderr.read()\n"
        "print(p.wait(), len(err))\n"
    )
    result = _run([sys.executable, "-c", code, _script(env)])
    assert result.stdout.split() in (["1", "0"], ["0", "0"])


def test_a_strict_consumer_type_checks(env: Path, tmp_path: Path) -> None:
    if importlib.util.find_spec("mypy") is None:
        pytest.skip("mypy is not installed")
    consumer = tmp_path / "consumer.py"
    consumer.write_text(
        "from lvtypedesc import Cluster, TypeDesc, parse_type_descriptor, to_bytes\n"
        "node: TypeDesc = parse_type_descriptor(b'\\x00\\x04\\x00\\x03')\n"
        "data: bytes = to_bytes(Cluster(0x50, 'Cluster', fields=(node,)))\n",
        encoding="utf-8",
    )
    site = _run(
        [str(env / "python"), "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"]
    )
    command = [sys.executable, "-m", "mypy", "--strict", "--no-incremental", str(consumer)]
    result = _run(command, cwd=tmp_path, env={**_ENV, "MYPYPATH": site.stdout.strip()})
    assert result.returncode == 0, result.stdout
