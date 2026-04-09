"""Tests for pathy_svg.coloring module."""

import re

import numpy as np

from pathy_svg.document import SVGDocument
from pathy_svg.themes import ColorScale


def _extract_fill(result, eid):
    """Extract the fill hex color from an element's style."""
    style = result._find_by_id(eid).get("style", "")
    m = re.search(r"fill:(#[0-9a-fA-F]{6})", style)
    return m.group(1) if m else None


class TestHeatmap:
    def test_basic_heatmap(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        data = {"stomach": 0.0, "liver": 0.5, "heart": 1.0}
        result = doc.heatmap(data)

        orig_fill = doc._find_by_id("stomach").get("style", "")
        assert "fill:" not in orig_fill or "fill:#ffffff" in orig_fill

        for pid in data:
            elem = result._find_by_id(pid)
            style = elem.get("style", "")
            assert "fill:" in style

    def test_color_correctness_viridis(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        data = {"stomach": 0.0, "liver": 0.5, "heart": 1.0}
        result = doc.heatmap(data, palette="viridis")

        scale = ColorScale("viridis", vmin=0, vmax=1)
        for eid, val in data.items():
            expected = scale(val)
            actual = _extract_fill(result, eid)
            assert actual == expected, f"{eid}: expected {expected}, got {actual}"

    def test_color_correctness_diverging(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        data = {"stomach": -1.0, "liver": 0.0, "heart": 1.0}
        result = doc.heatmap(data, palette="coolwarm", vcenter=0, vmin=-1, vmax=1)

        scale = ColorScale("coolwarm", vmin=-1, vmax=1, vcenter=0)
        for eid, val in data.items():
            expected = scale(val)
            actual = _extract_fill(result, eid)
            assert actual == expected, f"{eid}: expected {expected}, got {actual}"

    def test_color_ordering(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        data = {"stomach": 0.0, "liver": 0.5, "heart": 1.0}
        result = doc.heatmap(data, palette="viridis")

        c0 = _extract_fill(result, "stomach")
        c5 = _extract_fill(result, "liver")
        c10 = _extract_fill(result, "heart")
        assert c0 != c5 != c10
        assert c0 != c10

    def test_different_values_get_different_colors(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        data = {"stomach": 0.0, "liver": 1.0}
        result = doc.heatmap(data)

        s_fill = _extract_fill(result, "stomach")
        l_fill = _extract_fill(result, "liver")
        assert s_fill and l_fill
        assert s_fill != l_fill

    def test_na_color_applied(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        data = {"stomach": 0.5}
        result = doc.heatmap(data, na_color="#aabbcc", color_missing=True)

        liver_style = result._find_by_id("liver").get("style", "")
        assert "#aabbcc" in liver_style

    def test_color_missing_false(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        data = {"stomach": 0.5}
        result = doc.heatmap(data, color_missing=False)

        # Liver should NOT be recolored
        liver_style = result._find_by_id("liver").get("style", "")
        assert "#cccccc" not in liver_style

    def test_color_missing_skips_explicitly_unfilled_elements(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.heatmap({"stomach": 0.5}, na_color="#aabbcc", color_missing=True)

        border = result._find_by_id("border")
        assert border.get("fill") == "none"
        assert "#aabbcc" not in (border.get("style", ""))

    def test_custom_vmin_vmax(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        data = {"stomach": 50, "liver": 100}
        result = doc.heatmap(data, vmin=0, vmax=200)
        scale = ColorScale("RdYlBu_r", vmin=0, vmax=200)
        for eid, val in data.items():
            expected = scale(val)
            actual = _extract_fill(result, eid)
            assert actual == expected

    def test_diverging_with_vcenter(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        data = {"stomach": -2, "liver": 0, "heart": 2}
        result = doc.heatmap(data, palette="coolwarm", vcenter=0, vmin=-4, vmax=4)
        for pid in data:
            style = result._find_by_id(pid).get("style", "")
            assert "fill:" in style

    def test_empty_data(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.heatmap({})
        assert isinstance(result, SVGDocument)
        assert result.path_ids == doc.path_ids
        assert result._find_by_id("stomach").get("fill") == "#ffffff"

    def test_nan_value_gets_na_color(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.heatmap(
            {"stomach": float("nan"), "liver": 0.5},
            na_color="#aabbcc",
        )
        stomach_style = result._find_by_id("stomach").get("style", "")
        assert "#aabbcc" in stomach_style
        liver_fill = _extract_fill(result, "liver")
        assert liver_fill != "#aabbcc"

    def test_inf_value_gets_na_color(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.heatmap(
            {"stomach": float("inf"), "liver": 0.5},
            na_color="#aabbcc",
        )
        stomach_style = result._find_by_id("stomach").get("style", "")
        assert "#aabbcc" in stomach_style

    def test_breaks_discrete_coloring(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        data = {"stomach": 10, "liver": 50, "heart": 90}
        result = doc.heatmap(data, breaks=[0, 33, 66, 100])
        c_low = _extract_fill(result, "stomach")
        c_mid = _extract_fill(result, "liver")
        c_high = _extract_fill(result, "heart")
        assert c_low != c_mid
        assert c_mid != c_high
        assert c_low != c_high

    def test_breaks_same_bin_same_color(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        data = {"stomach": 10, "liver": 20}
        result = doc.heatmap(data, breaks=[0, 50, 100])
        assert _extract_fill(result, "stomach") == _extract_fill(result, "liver")

    def test_method_chaining(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.heatmap({"stomach": 0.5, "liver": 0.8}).recolor(
            {"lung_l": "#ff0000"}
        )
        # heatmap colors should be present
        stomach_style = result._find_by_id("stomach").get("style", "")
        assert "fill:" in stomach_style
        # recolor should also have worked
        lung_style = result._find_by_id("lung_l").get("style", "")
        assert "#ff0000" in lung_style

    def test_opacity(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.heatmap({"stomach": 0.5}, opacity=0.7)
        style = result._find_by_id("stomach").get("style", "")
        assert "fill-opacity:0.7" in style

    def test_heatmap_syncs_fill_attribute_with_style(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.heatmap({"stomach": 0.5})

        elem = result._find_by_id("stomach")
        style = elem.get("style", "")
        fill_match = re.search(r"fill:(#[0-9a-fA-F]{6})", style)

        assert fill_match is not None
        assert elem.get("fill") == fill_match.group(1)


class TestRecolor:
    def test_basic_recolor(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.recolor({"stomach": "#ff0000", "liver": "blue"})

        stomach_style = result._find_by_id("stomach").get("style", "")
        assert "#ff0000" in stomach_style
        assert result._find_by_id("stomach").get("fill") == "#ff0000"
        liver_style = result._find_by_id("liver").get("style", "")
        assert "blue" in liver_style
        assert result._find_by_id("liver").get("fill") == "blue"

    def test_recolor_preserves_original(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        doc.recolor({"stomach": "#ff0000"})
        # Original should be unchanged
        orig_style = doc._find_by_id("stomach").get("style", "")
        assert "#ff0000" not in orig_style

    def test_nonexistent_id_ignored(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        # Should not raise
        result = doc.recolor({"nonexistent": "#ff0000"})
        assert result is not None


class TestRecolorByCategory:
    def test_basic_categorical(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.recolor_by_category(
            {"stomach": "digestive", "heart": "circulatory", "lung_l": "respiratory"},
            palette={
                "digestive": "#e6ab02",
                "circulatory": "#e7298a",
                "respiratory": "#66a61e",
            },
        )
        stomach_style = result._find_by_id("stomach").get("style", "")
        assert "#e6ab02" in stomach_style
        heart_style = result._find_by_id("heart").get("style", "")
        assert "#e7298a" in heart_style

    def test_auto_palette(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.recolor_by_category(
            {"stomach": "a", "liver": "b", "heart": "a"},
            palette="tab10",
        )
        # Same category should get same color
        stomach_style = result._find_by_id("stomach").get("style", "")
        heart_style = result._find_by_id("heart").get("style", "")
        s_fill = re.search(r"fill:(#[0-9a-fA-F]{6})", stomach_style)
        h_fill = re.search(r"fill:(#[0-9a-fA-F]{6})", heart_style)
        assert s_fill and h_fill
        assert s_fill.group(1) == h_fill.group(1)


class TestStyledSVG:
    def test_heatmap_on_styled_svg(self, styled_svg_path):
        """SVGs using style='fill:...' should have their fill replaced."""
        doc = SVGDocument.from_file(styled_svg_path)
        data = {"region_a": 0.0, "region_b": 1.0}
        result = doc.heatmap(data)

        a_style = result._find_by_id("region_a").get("style", "")
        b_style = result._find_by_id("region_b").get("style", "")
        # The original fill should be replaced, not duplicated
        fills_a = re.findall(r"fill:", a_style)
        assert len(fills_a) == 1  # Only one fill property
        fills_b = re.findall(r"fill:", b_style)
        assert len(fills_b) == 1


class TestGroupedSVG:
    def test_recolor_group(self, grouped_svg_path):
        """Recoloring a <g> should color all its children."""
        doc = SVGDocument.from_file(grouped_svg_path)
        result = doc.recolor({"north": "#ff0000"})

        # Children of the north group should be colored
        north_a_style = result._find_by_id("north_a").get("style", "")
        north_b_style = result._find_by_id("north_b").get("style", "")
        assert "#ff0000" in north_a_style
        assert "#ff0000" in north_b_style

    def test_heatmap_group_keeps_group_children_colored(self, grouped_svg_path):
        doc = SVGDocument.from_file(grouped_svg_path)
        result = doc.heatmap({"north": 1.0}, na_color="#cccccc")

        north_a_style = result._find_by_id("north_a").get("style", "")
        north_b_style = result._find_by_id("north_b").get("style", "")
        south_a_style = result._find_by_id("south_a").get("style", "")

        assert "#cccccc" not in north_a_style
        assert "#cccccc" not in north_b_style
        assert "#cccccc" in south_a_style


class TestPreserveStroke:
    def test_preserve_stroke_true_keeps_stroke(self, styled_svg_path):
        doc = SVGDocument.from_file(styled_svg_path)
        result = doc.heatmap({"region_a": 0.5}, preserve_stroke=True)
        elem = result._find_by_id("region_a")
        assert elem.get("stroke") != "none"

    def test_preserve_stroke_false_clears_stroke(self, styled_svg_path):
        doc = SVGDocument.from_file(styled_svg_path)
        result = doc.heatmap({"region_a": 0.5}, preserve_stroke=False)
        elem = result._find_by_id("region_a")
        assert elem.get("stroke") == "none"
        style = elem.get("style", "")
        assert "stroke:none" in style

    def test_recolor_preserve_stroke_false(self, styled_svg_path):
        doc = SVGDocument.from_file(styled_svg_path)
        result = doc.recolor({"region_a": "#ff0000"}, preserve_stroke=False)
        elem = result._find_by_id("region_a")
        assert elem.get("stroke") == "none"
