"""Packaging metadata regression tests."""

from pathlib import Path
import re


def test_click_is_a_required_dependency():
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    text = pyproject.read_text()
    match = re.search(r"\[project\].*?dependencies = \[(.*?)\]", text, re.S)

    assert match is not None
    assert '"click>=8.0"' in match.group(1)
