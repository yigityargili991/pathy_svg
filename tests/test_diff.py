"""Tests for pathy_svg.diff module."""

import pytest

from pathy_svg.diff import compose_side_by_side, compute_diff
from pathy_svg.document import SVGDocument


class TestComputeDiff:
    def test_delta(self):
        b = {"a": 10, "b": 20}
        t = {"a": 15, "b": 10}
        result = compute_diff(b, t, mode="delta")
        assert result["a"] == 5
        assert result["b"] == -10

    def test_ratio(self):
        b = {"a": 10, "b": 20}
        t = {"a": 30, "b": 10}
        result = compute_diff(b, t, mode="ratio")
        assert result["a"] == pytest.approx(3.0)
        assert result["b"] == pytest.approx(0.5)

    def test_log2ratio(self):
        b = {"a": 1, "b": 4}
        t = {"a": 4, "b": 1}
        result = compute_diff(b, t, mode="log2ratio")
        assert result["a"] == pytest.approx(2.0)
        assert result["b"] == pytest.approx(-2.0)

    def test_percent_change(self):
        b = {"a": 100}
        t = {"a": 150}
        result = compute_diff(b, t, mode="percent_change")
        assert result["a"] == pytest.approx(50.0)

    def test_only_common_keys(self):
        b = {"a": 10, "c": 30}
        t = {"a": 20, "b": 40}
        result = compute_diff(b, t, mode="delta")
        assert "a" in result
        assert "b" not in result
        assert "c" not in result

    def test_invalid_mode(self):
        with pytest.raises(ValueError):
            compute_diff({"a": 1}, {"a": 2}, mode="invalid")


class TestDocDiff:
    def test_diff_returns_doc(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        b = {"stomach": 0.5, "liver": 0.3}
        t = {"stomach": 0.9, "liver": 0.1}
        result = doc.diff(b, t)
        assert result is not doc
        style = result._find_by_id("stomach").get("style", "")
        assert "fill:" in style


class TestComputeDiffEdgeCases:
    def test_ratio_division_by_zero(self):
        result = compute_diff({"a": 0}, {"a": 10}, mode="ratio")
        assert result["a"] == float("inf")

    def test_log2ratio_zero_baseline(self):
        import math

        result = compute_diff({"a": 0}, {"a": 10}, mode="log2ratio")
        assert math.isnan(result["a"])

    def test_percent_change_zero_baseline(self):
        result = compute_diff({"a": 0}, {"a": 10}, mode="percent_change")
        assert result["a"] == float("inf")

    def test_empty_dicts(self):
        result = compute_diff({}, {}, mode="delta")
        assert result == {}


class TestDocCompare:
    def test_compare_returns_doc(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.compare(
            {
                "Baseline": {"stomach": 0.3, "liver": 0.5},
                "Treatment": {"stomach": 0.9, "liver": 0.1},
            }
        )
        svg_str = result.to_string()
        assert "Baseline" in svg_str
        assert "Treatment" in svg_str

    def test_compare_vertical_layout(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.compare(
            {
                "A": {"stomach": 0.3},
                "B": {"stomach": 0.9},
            },
            layout="vertical",
        )
        vb = result.viewbox
        assert vb is not None
        assert vb.height > doc.viewbox.height

    def test_compose_rebases_non_zero_viewbox(self):
        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="100 100 50 50">'
            '<rect id="r" x="100" y="100" width="50" height="50"/>'
            "</svg>"
        )

        tree = compose_side_by_side([doc], titles=None)
        group = tree.getroot().find("{http://www.w3.org/2000/svg}g")

        assert group is not None
        assert group.get("transform") == "translate(-100.0,-100.0)"
