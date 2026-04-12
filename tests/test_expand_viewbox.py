"""Tests for expand_viewbox parameter on legend()."""

from pathy_svg.document import SVGDocument


class TestExpandViewbox:
    def test_default_expands_viewbox(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        original_vb = doc.viewbox
        result = doc.heatmap({"stomach": 0.5}).legend()
        new_vb = result.viewbox
        assert new_vb.width >= original_vb.width

    def test_expand_false_preserves_viewbox(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        original_vb = doc.viewbox
        result = doc.heatmap({"stomach": 0.5}).legend(expand_viewbox=False)
        new_vb = result.viewbox
        assert new_vb.width == original_vb.width
        assert new_vb.height == original_vb.height

    def test_expand_false_still_adds_legend(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.heatmap({"stomach": 0.5}).legend(expand_viewbox=False)
        assert result._find_by_id("pathy-legend") is not None

    def test_horizontal_expand_false_preserves_height(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        original_vb = doc.viewbox
        result = doc.heatmap({"stomach": 0.5}).legend(
            direction="horizontal",
            position=(0.1, 0.85),
            expand_viewbox=False,
        )
        new_vb = result.viewbox
        assert new_vb.height == original_vb.height

    def test_expand_true_explicit(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.heatmap({"stomach": 0.5}).legend(expand_viewbox=True)
        assert result._find_by_id("pathy-legend") is not None
