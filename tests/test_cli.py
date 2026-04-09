"""Tests for pathy_svg.cli module."""

import csv

import pytest
from click.testing import CliRunner

from pathy_svg.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def data_csv(tmp_path):
    p = tmp_path / "data.csv"
    with open(p, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["organ", "expression"])
        writer.writerow(["stomach", "0.5"])
        writer.writerow(["liver", "0.8"])
        writer.writerow(["heart", "0.3"])
    return str(p)


class TestInspectCommand:
    def test_inspect(self, runner, simple_svg_path):
        result = runner.invoke(main, ["inspect", str(simple_svg_path)])
        assert result.exit_code == 0
        assert "stomach" in result.output
        assert "liver" in result.output
        assert "Paths" in result.output


class TestHeatmapCommand:
    def test_heatmap(self, runner, simple_svg_path, data_csv, tmp_path):
        out = str(tmp_path / "result.svg")
        result = runner.invoke(
            main,
            [
                "heatmap",
                str(simple_svg_path),
                data_csv,
                "--id-col",
                "organ",
                "--value-col",
                "expression",
                "--palette",
                "viridis",
                "-o",
                out,
            ],
        )
        assert result.exit_code == 0
        assert "Saved to" in result.output

    def test_heatmap_with_legend(self, runner, simple_svg_path, data_csv, tmp_path):
        out = str(tmp_path / "result.svg")
        result = runner.invoke(
            main,
            [
                "heatmap",
                str(simple_svg_path),
                data_csv,
                "--id-col",
                "organ",
                "--value-col",
                "expression",
                "--legend",
                "--legend-title",
                "Score",
                "-o",
                out,
            ],
        )
        assert result.exit_code == 0


class TestValidateCommand:
    def test_validate_success(self, runner, simple_svg_path, data_csv):
        result = runner.invoke(
            main,
            [
                "validate",
                str(simple_svg_path),
                data_csv,
                "--id-col",
                "organ",
            ],
        )
        assert result.exit_code == 0
        assert "All data IDs found" in result.output

    def test_validate_failure(self, runner, simple_svg_path, tmp_path):
        p = tmp_path / "bad.csv"
        with open(p, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["organ"])
            writer.writerow(["typo_organ"])
        result = runner.invoke(
            main,
            [
                "validate",
                str(simple_svg_path),
                str(p),
                "--id-col",
                "organ",
            ],
        )
        assert result.exit_code == 1
        assert "not found" in result.output


class TestGuideCommand:
    def test_guide(self, runner, simple_svg_path, tmp_path):
        out = str(tmp_path / "guide.svg")
        result = runner.invoke(
            main,
            [
                "guide",
                str(simple_svg_path),
                "-o",
                out,
            ],
        )
        assert result.exit_code == 0
        assert "Guide saved" in result.output
