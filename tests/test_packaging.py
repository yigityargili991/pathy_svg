"""Distribution artifact regression tests."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

from pathy_svg import __version__

ROOT = Path(__file__).resolve().parents[1]
SDIST_BASENAME = f"pathy_svg-{__version__}.tar.gz"
WHEEL_GLOB = f"pathy_svg-{__version__}-*.whl"


def _build_distributions(outdir: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--sdist",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(outdir),
        ],
        cwd=ROOT,
        check=True,
    )


@pytest.fixture(scope="session")
def built_distributions(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    sdist = ROOT / "dist" / SDIST_BASENAME
    wheels = sorted((ROOT / "dist").glob(WHEEL_GLOB))
    if sdist.exists() and wheels:
        return sdist, wheels[0]

    if importlib.util.find_spec("build") is None:
        pytest.skip("build is required to verify sdist and wheel contents")
    if importlib.util.find_spec("hatchling") is None:
        pytest.skip("hatchling is required to build distributions without isolation")

    outdir = tmp_path_factory.mktemp("dist")
    _build_distributions(outdir)

    built_sdist = outdir / SDIST_BASENAME
    built_wheels = sorted(outdir.glob(WHEEL_GLOB))
    assert built_sdist.exists()
    assert built_wheels
    return built_sdist, built_wheels[0]


def _sdist_members(path: Path) -> list[str]:
    with tarfile.open(path, "r:gz") as archive:
        return sorted(
            member.name for member in archive.getmembers() if member.isfile()
        )


def _wheel_members(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        return sorted(name for name in archive.namelist() if not name.endswith("/"))


def test_click_is_a_required_dependency():
    pyproject = ROOT / "pyproject.toml"
    text = pyproject.read_text()

    assert '"click>=8.0"' in text


def test_sdist_includes_source_examples_and_tests(built_distributions):
    sdist, _ = built_distributions
    members = set(_sdist_members(sdist))
    prefix = f"pathy_svg-{__version__}/"

    expected = {
        prefix + "pyproject.toml",
        prefix + "README.md",
        prefix + "LICENSE",
        prefix + "CHANGELOG.md",
        prefix + "src/pathy_svg/__init__.py",
        prefix + "src/pathy_svg/py.typed",
        prefix + "examples/map.svg",
        prefix + "examples/data.csv",
        prefix + "examples/baseline.csv",
        prefix + "examples/treatment.csv",
        prefix + "tests/conftest.py",
        prefix + "tests/test_packaging.py",
        prefix + "tests/fixtures/simple.svg",
    }

    assert expected <= members


def test_sdist_excludes_docs_and_ci_files(built_distributions):
    sdist, _ = built_distributions
    members = _sdist_members(sdist)
    prefix = f"pathy_svg-{__version__}/"

    assert not any(name.startswith(prefix + "docs/") for name in members)
    assert not any(name.startswith(prefix + "docs_templates/") for name in members)
    assert not any(name.startswith(prefix + ".github/") for name in members)


def test_wheel_contains_runtime_files_only(built_distributions):
    _, wheel = built_distributions
    members = set(_wheel_members(wheel))

    expected = {
        "pathy_svg/__init__.py",
        "pathy_svg/cli.py",
        "pathy_svg/py.typed",
        "pathy_svg/_mixins/serialization.py",
        f"pathy_svg-{__version__}.dist-info/METADATA",
        f"pathy_svg-{__version__}.dist-info/entry_points.txt",
        f"pathy_svg-{__version__}.dist-info/licenses/LICENSE",
    }

    assert expected <= members
    assert not any(name.startswith("tests/") for name in members)
    assert not any(name.startswith("examples/") for name in members)
    assert not any(name.startswith("docs/") for name in members)
    assert not any(name.startswith("docs_templates/") for name in members)


def test_artifacts_exclude_build_junk(built_distributions):
    sdist, wheel = built_distributions

    for members in (_sdist_members(sdist), _wheel_members(wheel)):
        assert not any("__pycache__/" in name for name in members)
        assert not any(name.endswith((".pyc", ".pyo")) for name in members)
        assert not any(name.endswith(".DS_Store") for name in members)
