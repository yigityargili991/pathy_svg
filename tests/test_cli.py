"""Tests for pathy_svg.cli module."""

import csv

import pytest
from click.testing import CliRunner

from pathy_svg.cli import main, _read_data, _read_csv_data, _read_ids


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


class TestDiffCommand:
    def test_diff(self, runner, simple_svg_path, tmp_path):
        baseline = tmp_path / "baseline.csv"
        treatment = tmp_path / "treatment.csv"
        for p, vals in [(baseline, [0.5, 0.3, 0.2]), (treatment, [0.9, 0.1, 0.8])]:
            with open(p, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["organ", "expression"])
                for organ, val in zip(["stomach", "liver", "heart"], vals):
                    w.writerow([organ, str(val)])
        out = str(tmp_path / "diff.svg")
        result = runner.invoke(
            main,
            [
                "diff",
                str(simple_svg_path),
                str(baseline),
                str(treatment),
                "--id-col",
                "organ",
                "--value-col",
                "expression",
                "--mode",
                "delta",
                "-o",
                out,
            ],
        )
        assert result.exit_code == 0
        assert "Diff saved" in result.output


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


class TestExportCommand:
    def test_export_png(self, runner, simple_svg_path, tmp_path):
        out = str(tmp_path / "out.png")
        with pytest.MonkeyPatch.context() as m:
            from unittest.mock import MagicMock

            mock_cairo = MagicMock()
            mock_cairo.svg2png.return_value = b"\x89PNG fake"
            m.setattr("pathy_svg.export.require_cairosvg", lambda: mock_cairo)
            result = runner.invoke(
                main,
                ["export", str(simple_svg_path), "--format", "png", "-o", out],
            )
        assert result.exit_code == 0
        assert "Exported" in result.output

    def test_export_pdf(self, runner, simple_svg_path, tmp_path):
        out = str(tmp_path / "out.pdf")
        with pytest.MonkeyPatch.context() as m:
            from unittest.mock import MagicMock

            mock_cairo = MagicMock()
            mock_cairo.svg2pdf.return_value = b"%PDF fake"
            m.setattr("pathy_svg.export.require_cairosvg", lambda: mock_cairo)
            result = runner.invoke(
                main,
                ["export", str(simple_svg_path), "--format", "pdf", "-o", out],
            )
        assert result.exit_code == 0
        assert "Exported" in result.output

    def test_export_jpeg(self, runner, simple_svg_path, tmp_path):
        import io
        from unittest.mock import MagicMock

        from PIL import Image

        buf = io.BytesIO()
        img = Image.new("RGB", (10, 10), (255, 0, 0))
        img.save(buf, format="PNG")
        fake_png = buf.getvalue()

        out = str(tmp_path / "out.jpg")
        mock_cairo = MagicMock()
        mock_cairo.svg2png.return_value = fake_png
        with pytest.MonkeyPatch.context() as m:
            m.setattr("pathy_svg.export.require_cairosvg", lambda: mock_cairo)
            m.setattr("pathy_svg.export.require_pillow", lambda: __import__("PIL"))
            result = runner.invoke(
                main,
                ["export", str(simple_svg_path), "--format", "jpeg", "-o", out],
            )
        assert result.exit_code == 0
        assert "Exported" in result.output


class TestReadData:
    def test_read_csv(self, tmp_path):
        p = tmp_path / "data.csv"
        with open(p, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "val"])
            w.writerow(["a", "1.0"])
            w.writerow(["b", "2.0"])
        result = _read_data(str(p), "id", "val")
        assert result == {"a": 1.0, "b": 2.0}

    def test_read_tsv(self, tmp_path):
        p = tmp_path / "data.tsv"
        with open(p, "w", newline="") as f:
            w = csv.writer(f, delimiter="\t")
            w.writerow(["id", "val"])
            w.writerow(["x", "3.5"])
        result = _read_data(str(p), "id", "val")
        assert result == {"x": 3.5}

    def test_read_data_skips_non_numeric(self, tmp_path):
        p = tmp_path / "data.csv"
        with open(p, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "val"])
            w.writerow(["a", "1.0"])
            w.writerow(["b", "not_a_number"])
        result = _read_data(str(p), "id", "val")
        assert "a" in result
        assert "b" not in result

    def test_read_data_missing_id_col(self, tmp_path):
        p = tmp_path / "data.csv"
        with open(p, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["wrong_col", "val"])
            w.writerow(["a", "1.0"])
        with pytest.raises(Exception):
            _read_data(str(p), "id", "val")

    def test_read_data_missing_value_col(self, tmp_path):
        p = tmp_path / "data.csv"
        with open(p, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "wrong_col"])
            w.writerow(["a", "1.0"])
        with pytest.raises(Exception):
            _read_data(str(p), "id", "val")


class TestReadCsvData:
    def test_basic_csv(self, tmp_path):
        p = tmp_path / "data.csv"
        with open(p, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "val"])
            w.writerow(["a", "10"])
            w.writerow(["b", "20"])
        result = _read_csv_data(p, "id", "val")
        assert result == {"a": 10.0, "b": 20.0}

    def test_tsv_delimiter(self, tmp_path):
        p = tmp_path / "data.tsv"
        with open(p, "w", newline="") as f:
            w = csv.writer(f, delimiter="\t")
            w.writerow(["id", "val"])
            w.writerow(["x", "5"])
        result = _read_csv_data(p, "id", "val")
        assert result == {"x": 5.0}

    def test_tab_delimiter(self, tmp_path):
        p = tmp_path / "data.tab"
        with open(p, "w", newline="") as f:
            w = csv.writer(f, delimiter="\t")
            w.writerow(["id", "val"])
            w.writerow(["y", "7"])
        result = _read_csv_data(p, "id", "val")
        assert result == {"y": 7.0}


class TestReadIds:
    def test_read_ids(self, tmp_path):
        p = tmp_path / "ids.csv"
        with open(p, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["organ"])
            w.writerow(["stomach"])
            w.writerow(["liver"])
        result = _read_ids(str(p), "organ")
        assert result == ["stomach", "liver"]

    def test_read_ids_tsv(self, tmp_path):
        p = tmp_path / "ids.tsv"
        with open(p, "w", newline="") as f:
            w = csv.writer(f, delimiter="\t")
            w.writerow(["organ"])
            w.writerow(["heart"])
        result = _read_ids(str(p), "organ")
        assert result == ["heart"]

    def test_read_ids_skips_missing_col(self, tmp_path):
        p = tmp_path / "ids.csv"
        with open(p, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["organ", "extra"])
            w.writerow(["stomach", "x"])
            w.writerow(["liver", "y"])
        result = _read_ids(str(p), "organ")
        assert result == ["stomach", "liver"]
