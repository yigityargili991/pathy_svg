"""Tests for pathy_svg.legend module."""

from pathy_svg.document import SVGDocument


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
        # Original heatmapped should NOT have legend
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
        # Can still save
        svg_str = result.to_string()
        assert "Gene Expression" in svg_str
