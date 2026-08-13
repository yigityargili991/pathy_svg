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

    def test_empty_labels_render_bar_without_ticks(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.heatmap({"stomach": 0.2, "liver": 0.8}).legend(labels=[])
        g = result._find_by_id("pathy-legend")
        assert g.find(".//{http://www.w3.org/2000/svg}linearGradient") is not None
        assert g.findall(".//{http://www.w3.org/2000/svg}text") == []

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

    def test_horizontal_categorical_layout(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        palette = CategoricalPalette({"first": "#e6ab02", "second": "#e7298a"})
        result = doc.legend(
            palette=palette, direction="horizontal", expand_viewbox=False
        )
        g = result._find_by_id("pathy-legend")
        swatches = g.findall("./{http://www.w3.org/2000/svg}rect")
        assert len(swatches) == 2
        assert swatches[0].get("y") == swatches[1].get("y")
        assert float(swatches[0].get("x")) < float(swatches[1].get("x"))

    def test_categorical_background_honors_padding(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        palette = CategoricalPalette({"first": "#e6ab02", "second": "#e7298a"})
        result = doc.legend(
            palette=palette,
            background="white",
            padding=11,
            expand_viewbox=False,
        )
        g = result._find_by_id("pathy-legend")
        rects = g.findall("./{http://www.w3.org/2000/svg}rect")
        background, first_swatch = rects[0], rects[1]
        assert background.get("fill") == "white"
        assert float(first_swatch.get("x")) - float(background.get("x")) == 11

    def test_custom_label_count_must_match_categories(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        palette = CategoricalPalette({"first": "#e6ab02", "second": "#e7298a"})
        with pytest.raises(ValueError, match="exactly 2"):
            doc.legend(palette=palette, labels=["only one"])


class TestExplicitScaleAndPalette:
    def test_explicit_scale_on_fresh_document(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        assert doc._last_scale is None

        scale = ColorScale("viridis", vmin=0, vmax=100)
        scale.fit([0.0, 100.0])

        result = doc.legend(scale=scale, title="Score")
        g = result._find_by_id("pathy-legend")
        assert g is not None
        assert g.find(".//{http://www.w3.org/2000/svg}linearGradient") is not None

        svg_str = result.to_string()
        assert "Score" in svg_str
        assert "0.00" in svg_str
        assert "100.00" in svg_str

    def test_explicit_palette_on_fresh_document(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        assert doc._last_categorical_palette is None

        palette = CategoricalPalette({"digestive": "#e6ab02", "circulatory": "#e7298a"})

        result = doc.legend(palette=palette, title="System")
        g = result._find_by_id("pathy-legend")
        assert g is not None

        svg_str = result.to_string()
        assert "System" in svg_str
        assert "digestive" in svg_str
        assert "circulatory" in svg_str

    def test_explicit_scale_overrides_last_scale(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        heatmapped = doc.heatmap({"stomach": 0.0, "liver": 1.0})

        override = ColorScale("viridis", vmin=50, vmax=200)
        override.fit([50.0, 200.0])

        result = heatmapped.legend(scale=override)
        svg_str = result.to_string()
        assert "50.00" in svg_str
        assert "200.00" in svg_str


class TestLegendChaining:
    def test_full_chain(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.heatmap({"stomach": 0.3, "liver": 0.7, "heart": 0.9}).legend(
            title="Gene Expression", num_ticks=4
        )
        assert result._find_by_id("pathy-legend") is not None
        svg_str = result.to_string()
        assert "Gene Expression" in svg_str

    def test_repeated_calls_replace_the_canonical_legend(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        once = doc.heatmap({"stomach": 0.3, "liver": 0.7}).legend(title="Old")
        twice = once.legend(title="New")

        legends = twice.root.xpath(".//*[@id='pathy-legend']")
        assert len(legends) == 1
        text = "".join(legends[0].itertext())
        assert "New" in text
        assert "Old" not in text

    def test_user_viewbox_edit_between_legend_calls_survives(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        once = doc.heatmap({"stomach": 0.5}).legend()

        root = once.root_copy()
        root.set("viewBox", "0 0 300 300")
        edited = SVGDocument.from_tree(etree.ElementTree(root))
        twice = edited.heatmap({"stomach": 0.5}).legend()

        _, _, width, height = (
            float(value) for value in twice.root.get("viewBox").split()
        )
        # The user's 300x300 canvas must be the expansion base — a rollback
        # to the first call's stored canvas would yield a much smaller box.
        assert height == pytest.approx(300)
        assert width > 300

    def test_unchanged_canvas_is_still_restored_between_calls(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        once = doc.heatmap({"stomach": 0.5}).legend()
        twice = once.legend()
        assert twice.root.get("viewBox") == once.root.get("viewBox")
        assert twice.root.get("width") == once.root.get("width")
        assert twice.root.get("height") == once.root.get("height")

    def test_generated_legend_is_marked(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.heatmap({"stomach": 0.3}).legend()
        legend = result._find_by_id("pathy-legend")
        assert legend.get("data-pathy-legend") == "generated"
        private_attrs = {
            key: value
            for key, value in legend.attrib.items()
            if key.startswith("{urn:pathy-svg:private:legend:v1}")
        }
        assert private_attrs["{urn:pathy-svg:private:legend:v1}provenance"] == (
            "pathy-generated-legend-v1"
        )
        assert len(private_attrs) >= 7

    def test_user_owned_colliding_id_is_preserved(self):
        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            '<g id="pathy-legend"><text>User content</text></g>'
            '<path id="p" d="M0 0h100v100z"/></svg>'
        )
        scale = ColorScale("viridis", vmin=0, vmax=1)
        scale.fit([0, 1])

        once = doc.legend(scale=scale, title="Generated")
        twice = once.legend(scale=scale, title="Replacement")
        root = twice.root
        user = root.xpath("./*[@id='pathy-legend']")
        generated = root.xpath("./*[@data-pathy-legend='generated']")

        assert len(user) == 1
        assert "User content" in "".join(user[0].itertext())
        assert len(generated) == 1
        assert generated[0].get("id") == "pathy-legend-2"
        assert "Replacement" in "".join(generated[0].itertext())
        assert "Generated" not in "".join(generated[0].itertext())

    def test_only_direct_child_generated_legend_is_replaced(self):
        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            '<g id="user-wrapper"><g id="pathy-legend" '
            'data-pathy-legend="generated"><text>Nested user content</text></g></g>'
            "</svg>"
        )
        scale = ColorScale("viridis", vmin=0, vmax=1)
        scale.fit([0, 1])
        result = doc.legend(scale=scale)

        nested = result.root.xpath("./*[@id='user-wrapper']/*[@id='pathy-legend']")
        generated = result.root.xpath("./*[@data-pathy-legend='generated']")
        assert len(nested) == 1
        assert "Nested user content" in "".join(nested[0].itertext())
        assert len(generated) == 1
        assert generated[0].get("id") == "pathy-legend-2"

    def test_marker_and_partial_private_metadata_do_not_claim_user_groups(self):
        private_ns = "urn:pathy-svg:private:legend:v1"
        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:pathy-private="{private_ns}" viewBox="0 0 100 100">'
            '<g id="pathy-legend" data-pathy-legend="generated">'
            "<text>Marker only</text></g>"
            '<g id="pathy-legend-2" data-pathy-legend="generated" '
            'data-pathy-source-canvas="1"><text>Old partial schema</text></g>'
            '<g id="pathy-legend-3" data-pathy-legend="generated" '
            'pathy-private:provenance="pathy-generated-legend-v1">'
            "<text>Private marker without source schema</text></g>"
            '<g id="user-marker" data-pathy-legend="generated" '
            'pathy-private:provenance="pathy-generated-legend-v1">'
            "<text>Non-generated ID</text></g>"
            "</svg>"
        )
        scale = ColorScale("viridis", vmin=0, vmax=1)
        scale.fit([0, 1])

        once = doc.legend(scale=scale, title="First generated")
        twice = once.legend(scale=scale, title="Replacement generated")
        root = twice.root

        for element_id, text in (
            ("pathy-legend", "Marker only"),
            ("pathy-legend-2", "Old partial schema"),
            ("pathy-legend-3", "Private marker without source schema"),
            ("user-marker", "Non-generated ID"),
        ):
            matches = root.xpath(f"./*[@id='{element_id}']")
            assert len(matches) == 1
            assert text in "".join(matches[0].itertext())

        owned = [
            child
            for child in root
            if child.get("{urn:pathy-svg:private:legend:v1}provenance")
            == "pathy-generated-legend-v1"
            and child.get("id") == "pathy-legend-4"
        ]
        assert len(owned) == 1
        assert "Replacement generated" in "".join(owned[0].itertext())
        assert "First generated" not in "".join(owned[0].itertext())


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

    def test_empty_labels_render_bar_without_ticks(self):
        scale = self._make_scale()
        vb = ViewBox(0, 0, 500, 400)
        g = build_gradient_legend(scale, vb, labels=[])
        assert g.findall(".//{http://www.w3.org/2000/svg}text") == []
        bars = [
            r
            for r in g.findall(".//{http://www.w3.org/2000/svg}rect")
            if r.get("fill", "").startswith("url(#")
        ]
        assert len(bars) == 1

    def test_non_string_labels_raise(self):
        scale = self._make_scale()
        vb = ViewBox(0, 0, 500, 400)
        with pytest.raises(TypeError, match="only strings"):
            build_gradient_legend(scale, vb, labels=["ok", 1])

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

    def test_horizontal_places_swatches_side_by_side(self):
        vb = ViewBox(0, 0, 500, 400)
        g = build_discrete_legend(
            ["#ff0000", "#00ff00"], ["A", "B"], vb, direction="horizontal"
        )
        rects = g.findall("./{http://www.w3.org/2000/svg}rect")
        assert rects[0].get("y") == rects[1].get("y")
        assert float(rects[0].get("x")) < float(rects[1].get("x"))

    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            ({"direction": "diagonal"}, "direction"),
            ({"position": (float("nan"), 0.5)}, "position"),
            ({"size": (0, 0.4)}, "size"),
            ({"padding": -1}, "padding"),
            ({"font_size": 0}, "font_size"),
        ],
    )
    def test_invalid_layout_parameters_raise(self, kwargs, message):
        vb = ViewBox(0, 0, 500, 400)
        with pytest.raises(ValueError, match=message):
            build_discrete_legend(["#ff0000"], ["A"], vb, **kwargs)

    def test_color_and_label_counts_must_match(self):
        vb = ViewBox(0, 0, 500, 400)
        with pytest.raises(ValueError, match="exactly 2"):
            build_discrete_legend(["#ff0000", "#00ff00"], ["A"], vb)


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
