"""Tests for expand_viewbox parameter on legend()."""

from pathy_svg.document import SVGDocument
from pathy_svg.themes import CategoricalPalette, ColorScale


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

    def test_repeated_identical_calls_do_not_compound_expansion(self, simple_svg_path):
        source = SVGDocument.from_file(simple_svg_path).heatmap({"stomach": 0.5})
        options = {
            "position": (0.95, 0.05),
            "labels": ["an intentionally wide label"],
            "font_size": 16,
            "background": "white",
            "padding": 8,
        }
        once = source.legend(**options)
        twice = once.legend(**options)

        assert twice.viewbox == once.viewbox
        assert twice.root.get("width") == once.root.get("width")
        assert twice.root.get("height") == once.root.get("height")
        first_bar = next(
            rect
            for rect in once.root.xpath("./*[@data-pathy-legend='generated']/*")
            if rect.get("fill", "").startswith("url(#")
        )
        second_bar = next(
            rect
            for rect in twice.root.xpath("./*[@data-pathy-legend='generated']/*")
            if rect.get("fill", "").startswith("url(#")
        )
        assert second_bar.get("x") == first_bar.get("x")
        assert second_bar.get("y") == first_bar.get("y")

    def test_expand_false_restores_prelegend_canvas(self, simple_svg_path):
        source = SVGDocument.from_file(simple_svg_path).heatmap({"stomach": 0.5})
        source_root = source.root
        expanded = source.legend(
            position=(1.5, 1.5), labels=["wide label"], font_size=18
        )
        restored = expanded.legend(
            position=(0.1, 0.1), expand_viewbox=False, labels=["short"]
        )

        assert restored.viewbox == source.viewbox
        assert restored.root.get("width") == source_root.get("width")
        assert restored.root.get("height") == source_root.get("height")

    def test_restore_preserves_absent_viewbox_and_dimension_units(self):
        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" width="120px" height="80px"/>'
        )
        scale = ColorScale("viridis", vmin=0, vmax=1)
        scale.fit([0, 1])
        expanded = doc.legend(scale=scale, position=(1.5, 1.5), labels=["outside"])
        restored = expanded.legend(
            scale=scale, position=(0.1, 0.1), expand_viewbox=False
        )

        assert restored.root.get("viewBox") is None
        assert restored.root.get("width") == "120px"
        assert restored.root.get("height") == "80px"

    def test_switching_expand_back_on_reuses_prelegend_canvas(self, simple_svg_path):
        source = SVGDocument.from_file(simple_svg_path).heatmap({"stomach": 0.5})
        options = {"position": (-0.75, 1.25), "labels": ["outside"], "font_size": 12}
        direct = source.legend(**options)
        unexpanded = source.legend(**options, expand_viewbox=False)
        reexpanded = unexpanded.legend(**options, expand_viewbox=True)

        assert reexpanded.viewbox == direct.viewbox
        assert reexpanded.root.get("width") == direct.root.get("width")
        assert reexpanded.root.get("height") == direct.root.get("height")

    def test_repositioning_replaces_expansion_instead_of_accumulating(self):
        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="10 20 100 50" '
            'width="100" height="50"/>'
        )
        scale = ColorScale("viridis", vmin=0, vmax=1)
        scale.fit([0, 1])
        right = doc.legend(scale=scale, position=(2, 0.5), labels=["right"])
        left = right.legend(scale=scale, position=(-1, 0.5), labels=["left"])
        direct_left = doc.legend(scale=scale, position=(-1, 0.5), labels=["left"])

        assert left.viewbox == direct_left.viewbox
        assert left.viewbox.x < 10
        assert left.viewbox.x + left.viewbox.width == 110

    def test_positions_outside_source_expand_on_all_edges(self):
        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="10 20 100 50"/>'
        )
        palette = CategoricalPalette({"category": "#ff0000"})
        top_left = doc.legend(
            palette=palette,
            position=(-0.5, -0.5),
            background="white",
            padding=4,
        )
        bottom_right = doc.legend(
            palette=palette,
            position=(1.5, 1.5),
            direction="horizontal",
            background="white",
            padding=4,
        )

        assert top_left.viewbox.x < 10
        assert top_left.viewbox.y < 20
        assert bottom_right.viewbox.x + bottom_right.viewbox.width > 110
        assert bottom_right.viewbox.y + bottom_right.viewbox.height > 70

    def test_layout_uses_original_nonzero_origin_viewbox(self):
        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="100 200 40 20" '
            'width="40" height="20"><path id="p" d="M100 200h40v20z"/></svg>'
        )
        scale = ColorScale("viridis", vmin=0, vmax=1)
        scale.fit([0, 1])
        result = doc.legend(
            scale=scale,
            position=(0.9, 0.1),
            labels=["a very long tick label"],
            font_size=10,
        )
        legend = result._find_by_id("pathy-legend")
        bar = next(
            rect
            for rect in legend.findall("./{http://www.w3.org/2000/svg}rect")
            if rect.get("fill", "").startswith("url(#")
        )

        # 100 + 90% of the original width. Expansion must not move the legend.
        assert float(bar.get("x")) == 136
        label = legend.find("./{http://www.w3.org/2000/svg}text")
        estimated_right = float(label.get("x")) + len(label.text) * 10 * 0.65
        assert result.viewbox.x + result.viewbox.width >= estimated_right

    def test_vertical_expansion_contains_title_background_and_padding(self):
        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="10 20 50 30"/>'
        )
        palette = CategoricalPalette({"long category": "#ff0000"})
        result = doc.legend(
            palette=palette,
            position=(0.95, 0.05),
            title="Legend title",
            title_size=12,
            font_size=10,
            background="white",
            padding=7,
        )
        background = result._find_by_id("pathy-legend").find(
            "./{http://www.w3.org/2000/svg}rect"
        )
        vb = result.viewbox
        assert float(background.get("x")) >= vb.x
        assert float(background.get("y")) >= vb.y
        assert float(background.get("x")) + float(background.get("width")) <= (
            vb.x + vb.width
        )
        assert float(background.get("y")) + float(background.get("height")) <= (
            vb.y + vb.height
        )
        assert vb.y < 20  # title and padded background extend above the source

    def test_horizontal_expansion_contains_category_labels_and_background(self):
        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-20 30 60 20"/>'
        )
        palette = CategoricalPalette(
            {"long left label": "#ff0000", "long right label": "#00ff00"}
        )
        result = doc.legend(
            palette=palette,
            direction="horizontal",
            position=(0.1, 0.95),
            font_size=9,
            background="#eee",
            padding=6,
        )
        legend = result._find_by_id("pathy-legend")
        background = legend.find("./{http://www.w3.org/2000/svg}rect")
        swatches = [
            rect
            for rect in legend.findall("./{http://www.w3.org/2000/svg}rect")
            if rect.get("fill") != "#eee"
        ]
        vb = result.viewbox
        assert swatches[0].get("y") == swatches[1].get("y")
        assert float(background.get("x")) >= vb.x
        assert float(background.get("y")) + float(background.get("height")) <= (
            vb.y + vb.height
        )
        assert vb.height > 20
