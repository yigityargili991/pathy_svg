"""Tests for pathy_svg.layers module."""

import pytest

from pathy_svg.document import SVGDocument
from pathy_svg.layers import LayerManager


class TestLayerManager:
    def test_init_from_document(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        lm = LayerManager(doc)
        assert lm.names == []
        assert lm.visible == {}

    def test_add_layer(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        lm = LayerManager(doc)
        lm2 = lm.add("heatmap", lambda d: d.heatmap({"stomach": 0.5}))

        assert lm.names == []
        assert lm2.names == ["heatmap"]
        assert lm2.visible == {"heatmap": True}

    def test_add_multiple_layers(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        lm = (
            LayerManager(doc)
            .add("layer1", lambda d: d.heatmap({"stomach": 0.5}))
            .add("layer2", lambda d: d.recolor({"liver": "#ff0000"}))
        )
        assert lm.names == ["layer1", "layer2"]

    def test_duplicate_name_raises(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        lm = LayerManager(doc).add("heatmap", lambda d: d)
        with pytest.raises(ValueError, match="already exists"):
            lm.add("heatmap", lambda d: d)

    def test_hide_layer(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        lm = (
            LayerManager(doc)
            .add("a", lambda d: d)
            .add("b", lambda d: d)
            .hide("a")
        )
        assert lm.visible == {"a": False, "b": True}

    def test_show_hidden_layer(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        lm = (
            LayerManager(doc)
            .add("a", lambda d: d)
            .hide("a")
            .show("a")
        )
        assert lm.visible == {"a": True}

    def test_hide_nonexistent_raises(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        lm = LayerManager(doc)
        with pytest.raises(KeyError, match="nonexistent"):
            lm.hide("nonexistent")

    def test_remove_layer(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        lm = (
            LayerManager(doc)
            .add("a", lambda d: d)
            .add("b", lambda d: d)
            .remove("a")
        )
        assert lm.names == ["b"]

    def test_remove_nonexistent_raises(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        lm = LayerManager(doc)
        with pytest.raises(KeyError, match="nonexistent"):
            lm.remove("nonexistent")

    def test_reorder(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        lm = (
            LayerManager(doc)
            .add("a", lambda d: d)
            .add("b", lambda d: d)
            .add("c", lambda d: d)
            .reorder(["c", "a", "b"])
        )
        assert lm.names == ["c", "a", "b"]

    def test_reorder_mismatched_names_raises(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        lm = LayerManager(doc).add("a", lambda d: d).add("b", lambda d: d)
        with pytest.raises(ValueError, match="must contain exactly"):
            lm.reorder(["a"])

    def test_immutability(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        lm1 = LayerManager(doc)
        lm2 = lm1.add("a", lambda d: d)
        assert lm1.names == []
        assert lm2.names == ["a"]


class TestLayerManagerFlatten:
    def test_flatten_empty_returns_base(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        lm = LayerManager(doc)
        result = lm.flatten()
        assert isinstance(result, SVGDocument)
        assert result._find_by_id("stomach").get("fill") == "#ffffff"

    def test_flatten_applies_visible_layers(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        lm = LayerManager(doc).add(
            "heatmap", lambda d: d.heatmap({"stomach": 0.5, "liver": 1.0})
        )
        result = lm.flatten()

        style = result._find_by_id("stomach").get("style", "")
        assert "fill:" in style

    def test_flatten_skips_hidden_layers(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        lm = (
            LayerManager(doc)
            .add("heatmap", lambda d: d.heatmap({"stomach": 0.5}))
            .hide("heatmap")
        )
        result = lm.flatten()

        assert result._find_by_id("stomach").get("fill") == "#ffffff"

    def test_flatten_layer_order_matters(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        lm = (
            LayerManager(doc)
            .add("red", lambda d: d.recolor({"stomach": "#ff0000"}))
            .add("blue", lambda d: d.recolor({"stomach": "#0000ff"}))
        )
        result = lm.flatten()
        style = result._find_by_id("stomach").get("style", "")
        assert "#0000ff" in style

    def test_flatten_does_not_mutate_base(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        lm = LayerManager(doc).add(
            "heatmap", lambda d: d.heatmap({"stomach": 0.5})
        )
        lm.flatten()

        assert doc._find_by_id("stomach").get("fill") == "#ffffff"
