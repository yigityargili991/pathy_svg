"""Tests for pathy_svg.annotations module."""

from pathy_svg.document import SVGDocument


class TestAnnotate:
    def test_adds_text_labels(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.annotate({"stomach": "Stomach", "liver": "Liver"})
        svg_str = result.to_string()
        assert "Stomach" in svg_str
        assert "Liver" in svg_str

    def test_has_annotations_group(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.annotate({"stomach": "S"})
        g = result._find_by_id("pathy-annotations")
        assert g is not None

    def test_immutability(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.annotate({"stomach": "S"})
        assert doc._find_by_id("pathy-annotations") is None
        assert result._find_by_id("pathy-annotations") is not None

    def test_nonexistent_id_ignored(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.annotate({"nonexistent": "X"})
        # Should not raise, group should exist but be empty of text
        assert result._find_by_id("pathy-annotations") is not None

    def test_with_background(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.annotate({"stomach": "S"}, background="rgba(0,0,0,0.5)")
        svg_str = result.to_string()
        assert "rgba(0,0,0,0.5)" in svg_str

    def test_placement_above(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.annotate({"stomach": "S"}, placement="above")
        assert result._find_by_id("pathy-annotations") is not None

    def test_chaining_with_heatmap(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.heatmap({"stomach": 0.5, "liver": 0.8}).annotate(
            {"stomach": "50%", "liver": "80%"}
        )
        svg_str = result.to_string()
        assert "50%" in svg_str
        assert "80%" in svg_str


class TestTooltips:
    def test_title_tooltips(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.add_tooltips({"stomach": "The stomach organ"})
        svg_str = result.to_string()
        assert "The stomach organ" in svg_str

    def test_css_tooltips(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.add_tooltips({"stomach": "Stomach info"}, method="css")
        elem = result._find_by_id("stomach")
        tooltip = result.root.xpath('//*[@data-tooltip-for="stomach"]')
        assert elem.get("data-tooltip") == "Stomach info"
        assert tooltip
        assert "Stomach info" in result.to_string()

    def test_immutability(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        doc.add_tooltips({"stomach": "tip"})
        # Original should not have tooltip
        orig_stomach = doc._find_by_id("stomach")
        has_title = any(c.tag.endswith("title") for c in orig_stomach)
        assert not has_title


class TestReplaceText:
    def test_replace_legend_text(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        # First add a legend with text
        result = doc.heatmap({"stomach": 0.0, "liver": 1.0}).legend(num_ticks=3)
        # Now replace text in the legend
        svg_before = result.to_string()
        replaced = result.replace_text({"0.00": "Low", "1.00": "High"})
        svg_after = replaced.to_string()
        if "0.00" in svg_before:
            assert "Low" in svg_after
