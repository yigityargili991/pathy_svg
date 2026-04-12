"""Tests for pathy_svg.legend module."""

import pytest

from lxml import etree

from pathy_svg.document import SVGDocument
from pathy_svg.legend import (
    build_discrete_legend,
    build_gradient_legend,
    build_legend,
    resolve_legend_kind,
)
from pathy_svg.themes import CategoricalPalette, ColorScale
from pathy_svg.transform import ViewBox


class TestGradientLegend:
    def test_legend_after_heatmap(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.heatmap({"stomach": 0.2, "liver": 0.8}).legend(title="Score")
        g = result._find_by_id("pathy-legend")
        assert g is not None

    def test_legend_has_gradient(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.heatmap({"stomach": 0.2, "liver": 0.8}).legend()
        svg_str = result.to_string()
        assert "linearGradient" in svg_str

    def test_legend_has_ticks(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.heatmap({"stomach": 0.0, "liver": 1.0}).legend(num_ticks=3)
        g = result._find_by_id("pathy-legend")
        texts = g.findall(".//{http://www.w3.org/2000/svg}text")
        assert len(texts) >= 3

    def test_legend_title(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.heatmap({"stomach": 0.5}).legend(title="Expression")
        svg_str = result.to_string()
        assert "Expression" in svg_str

    def test_horizontal_legend(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.heatmap({"stomach": 0.5}).legend(direction="horizontal")
        g = result._find_by_id("pathy-legend")
        assert g is not None

    def test_single_tick_legend(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.heatmap({"stomach": 0.0, "liver": 1.0}).legend(num_ticks=1)
        g = result._find_by_id("pathy-legend")
        texts = g.findall(".//{http://www.w3.org/2000/svg}text")
        assert len(texts) >= 1

    def test_legend_immutability(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        heatmapped = doc.heatmap({"stomach": 0.5})
        with_legend = heatmapped.legend()
        assert heatmapped._find_by_id("pathy-legend") is None
        assert with_legend._find_by_id("pathy-legend") is not None


class TestCategoricalLegend:
    def test_categorical_legend(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.recolor_by_category(
            {"stomach": "digestive", "heart": "circulatory"},
            palette={"digestive": "#e6ab02", "circulatory": "#e7298a"},
        ).legend(title="System")
        g = result._find_by_id("pathy-legend")
        assert g is not None
        svg_str = result.to_string()
        assert "System" in svg_str


class TestLegendChaining:
    def test_full_chain(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.heatmap({"stomach": 0.3, "liver": 0.7, "heart": 0.9}).legend(
            title="Gene Expression", num_ticks=4
        )
        assert result._find_by_id("pathy-legend") is not None
        svg_str = result.to_string()
        assert "Gene Expression" in svg_str


class TestBuildGradientLegendDirect:
    def _make_scale(self):
        scale = ColorScale("viridis", vmin=0, vmax=1)
        scale.fit([0.0, 1.0])
        return scale

    def test_background_rect(self):
        scale = self._make_scale()
        vb = ViewBox(0, 0, 500, 400)
        g = build_gradient_legend(scale, vb, background="white")
        rects = g.findall(".//{http://www.w3.org/2000/svg}rect")
        assert any(r.get("fill") == "white" for r in rects)

    def test_background_rect_with_title(self):
        scale = self._make_scale()
        vb = ViewBox(0, 0, 500, 400)
        g = build_gradient_legend(scale, vb, background="white", title="Test")
        rects = g.findall(".//{http://www.w3.org/2000/svg}rect")
        assert any(r.get("fill") == "white" for r in rects)

    def test_border_on_color_bar(self):
        scale = self._make_scale()
        vb = ViewBox(0, 0, 500, 400)
        g = build_gradient_legend(scale, vb, border=True, border_color="red")
        bar_rects = [
            r
            for r in g.findall(".//{http://www.w3.org/2000/svg}rect")
            if r.get("fill", "").startswith("url(#")
        ]
        assert len(bar_rects) == 1
        assert bar_rects[0].get("stroke") == "red"

    def test_num_ticks_less_than_one_raises(self):
        scale = self._make_scale()
        vb = ViewBox(0, 0, 500, 400)
        with pytest.raises(ValueError, match="num_ticks must be at least 1"):
            build_gradient_legend(scale, vb, num_ticks=0)

    def test_custom_labels(self):
        scale = self._make_scale()
        vb = ViewBox(0, 0, 500, 400)
        g = build_gradient_legend(scale, vb, labels=["Low", "High"])
        texts = g.findall(".//{http://www.w3.org/2000/svg}text")
        text_values = [t.text for t in texts]
        assert "Low" in text_values
        assert "High" in text_values

    def test_horizontal_direction(self):
        scale = self._make_scale()
        vb = ViewBox(0, 0, 500, 400)
        g = build_gradient_legend(scale, vb, direction="horizontal")
        assert g is not None
        grad = g.find(".//{http://www.w3.org/2000/svg}linearGradient")
        assert grad is not None
        assert grad.get("x2") == "1"
        assert grad.get("y2") == "0"


class TestBuildDiscreteLegendDirect:
    def test_basic(self):
        vb = ViewBox(0, 0, 500, 400)
        g = build_discrete_legend(["#ff0000", "#00ff00"], ["A", "B"], vb)
        assert g is not None
        rects = g.findall(".//{http://www.w3.org/2000/svg}rect")
        assert len(rects) == 2

    def test_with_title(self):
        vb = ViewBox(0, 0, 500, 400)
        g = build_discrete_legend(["#ff0000"], ["A"], vb, title="Categories")
        texts = g.findall(".//{http://www.w3.org/2000/svg}text")
        text_values = [t.text for t in texts]
        assert "Categories" in text_values

    def test_with_border(self):
        vb = ViewBox(0, 0, 500, 400)
        g = build_discrete_legend(
            ["#ff0000", "#00ff00"], ["A", "B"], vb, border=True, border_color="blue"
        )
        rects = g.findall(".//{http://www.w3.org/2000/svg}rect")
        assert all(r.get("stroke") == "blue" for r in rects)


class TestResolveLegendKind:
    def test_explicit_gradient(self):
        assert resolve_legend_kind("gradient", None, None) == "gradient"

    def test_explicit_discrete(self):
        assert resolve_legend_kind("discrete", None, None) == "discrete"

    def test_explicit_categorical(self):
        assert resolve_legend_kind("categorical", None, None) == "categorical"

    def test_auto_with_categorical_palette(self):
        cat_pal = CategoricalPalette({"a": "#ff0000"})
        assert resolve_legend_kind("auto", None, cat_pal) == "categorical"

    def test_auto_with_breaks(self):
        scale = ColorScale("viridis", vmin=0, vmax=1, breaks=[0, 0.5, 1])
        assert resolve_legend_kind("auto", scale, None) == "discrete"

    def test_auto_with_continuous_scale(self):
        scale = ColorScale("viridis", vmin=0, vmax=1)
        assert resolve_legend_kind("auto", scale, None) == "gradient"

    def test_auto_without_scale_raises(self):
        with pytest.raises(ValueError, match="Cannot auto-detect"):
            resolve_legend_kind("auto", None, None)


class TestBuildLegendDispatch:
    def _make_scale(self):
        scale = ColorScale("viridis", vmin=0, vmax=1)
        scale.fit([0.0, 1.0])
        return scale

    def test_gradient_without_scale_raises(self):
        vb = ViewBox(0, 0, 500, 400)
        with pytest.raises(ValueError, match="Cannot build gradient legend"):
            build_legend("gradient", None, None, vb)

    def test_discrete_without_scale_raises(self):
        vb = ViewBox(0, 0, 500, 400)
        with pytest.raises(ValueError, match="Cannot build discrete legend"):
            build_legend("discrete", None, None, vb)

    def test_discrete_with_breaks(self):
        scale = ColorScale("viridis", vmin=0, vmax=10, breaks=[0, 5, 10])
        scale.fit([0.0, 5.0, 10.0])
        vb = ViewBox(0, 0, 500, 400)
        g = build_legend("discrete", scale, None, vb)
        assert g is not None
        rects = g.findall(".//{http://www.w3.org/2000/svg}rect")
        assert len(rects) >= 2

    def test_discrete_without_breaks_falls_back_to_gradient(self):
        scale = self._make_scale()
        vb = ViewBox(0, 0, 500, 400)
        g = build_legend("discrete", scale, None, vb)
        assert g is not None
        assert g.find(".//{http://www.w3.org/2000/svg}linearGradient") is not None

    def test_categorical_with_palette(self):
        cat_pal = CategoricalPalette({"a": "#ff0000", "b": "#00ff00"})
        vb = ViewBox(0, 0, 500, 400)
        g = build_legend("categorical", None, cat_pal, vb)
        assert g is not None
        rects = g.findall(".//{http://www.w3.org/2000/svg}rect")
        assert len(rects) == 2

    def test_categorical_without_palette_with_scale_falls_back(self):
        scale = self._make_scale()
        vb = ViewBox(0, 0, 500, 400)
        g = build_legend("categorical", scale, None, vb)
        assert g is not None
        assert g.find(".//{http://www.w3.org/2000/svg}linearGradient") is not None

    def test_categorical_without_palette_or_scale_raises(self):
        vb = ViewBox(0, 0, 500, 400)
        with pytest.raises(ValueError, match="Cannot build categorical legend"):
            build_legend("categorical", None, None, vb)

    def test_unknown_kind_raises(self):
        vb = ViewBox(0, 0, 500, 400)
        with pytest.raises(ValueError, match="Unknown legend kind"):
            build_legend("nonexistent", None, None, vb)
