"""Shared test fixtures for pathy_svg tests."""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def simple_svg_path():
    return FIXTURES_DIR / "simple.svg"


@pytest.fixture
def styled_svg_path():
    return FIXTURES_DIR / "styled.svg"


@pytest.fixture
def grouped_svg_path():
    return FIXTURES_DIR / "grouped.svg"


@pytest.fixture
def simple_svg_string():
    return (FIXTURES_DIR / "simple.svg").read_text()


@pytest.fixture
def minimal_svg_string():
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><path id="p1" d="M 0 0 L 100 0 L 100 100 Z" fill="#fff"/></svg>'
