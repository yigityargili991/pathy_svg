"""Tests for group aggregation (heatmap_groups)."""

import re

import numpy as np
import pytest
from lxml import etree

from pathy_svg.coloring import aggregate_by_group
from pathy_svg.document import SVGDocument


def _make_grouped_tree():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">'
        '<g id="north">'
        '<path id="north_a" d="M 50 50 L 190 50 L 190 190 Z" fill="#fff"/>'
        '<path id="north_b" d="M 210 50 L 350 50 L 350 190 Z" fill="#fff"/>'
        "</g>"
        '<g id="south">'
        '<path id="south_a" d="M 50 210 L 190 210 L 190 350 Z" fill="#fff"/>'
        '<path id="south_b" d="M 210 210 L 350 210 L 350 350 Z" fill="#fff"/>'
        "</g>"
        "</svg>"
    )
    return etree.ElementTree(etree.fromstring(svg.encode()))


class TestAggregateByGroup:
    def test_mean(self):
        tree = _make_grouped_tree()
        data = {"north_a": 10.0, "north_b": 20.0, "south_a": 30.0, "south_b": 40.0}
        result = aggregate_by_group(tree, data, agg="mean")
        assert result["north"] == pytest.approx(15.0)
        assert result["south"] == pytest.approx(35.0)

    def test_sum(self):
        tree = _make_grouped_tree()
        data = {"north_a": 10.0, "north_b": 20.0}
        result = aggregate_by_group(tree, data, agg="sum")
        assert result["north"] == pytest.approx(30.0)

    def test_min(self):
        tree = _make_grouped_tree()
        data = {"north_a": 10.0, "north_b": 20.0}
        result = aggregate_by_group(tree, data, agg="min")
        assert result["north"] == pytest.approx(10.0)

    def test_max(self):
        tree = _make_grouped_tree()
        data = {"north_a": 10.0, "north_b": 20.0}
        result = aggregate_by_group(tree, data, agg="max")
        assert result["north"] == pytest.approx(20.0)

    def test_median(self):
        tree = _make_grouped_tree()
        data = {"north_a": 10.0, "north_b": 20.0}
        result = aggregate_by_group(tree, data, agg="median")
        assert result["north"] == pytest.approx(15.0)

    def test_group_with_no_data_excluded(self):
        tree = _make_grouped_tree()
        data = {"north_a": 10.0, "north_b": 20.0}
        result = aggregate_by_group(tree, data, agg="mean")
        assert "north" in result
        assert "south" not in result

    def test_partial_children_data(self):
        tree = _make_grouped_tree()
        data = {"north_a": 10.0}
        result = aggregate_by_group(tree, data, agg="mean")
        assert result["north"] == pytest.approx(10.0)

    def test_invalid_agg_raises(self):
        tree = _make_grouped_tree()
        with pytest.raises(ValueError, match="Unknown aggregation"):
            aggregate_by_group(tree, {"north_a": 10.0}, agg="invalid")


class TestHeatmapGroupsMixin:
    def test_colors_groups_by_aggregation(self, grouped_svg_path):
        doc = SVGDocument.from_file(grouped_svg_path)
        data = {"north_a": 0.0, "north_b": 1.0, "south_a": 0.5, "south_b": 0.5}
        result = doc.heatmap_groups(data, agg="mean")

        na_style = result._find_by_id("north_a").get("style", "")
        nb_style = result._find_by_id("north_b").get("style", "")
        na_fill = re.search(r"fill:(#[0-9a-fA-F]{6})", na_style)
        nb_fill = re.search(r"fill:(#[0-9a-fA-F]{6})", nb_style)
        assert na_fill and nb_fill
        assert na_fill.group(1) == nb_fill.group(1)

    def test_returns_new_document(self, grouped_svg_path):
        doc = SVGDocument.from_file(grouped_svg_path)
        result = doc.heatmap_groups({"north_a": 1.0}, agg="mean")
        assert result is not doc
        assert isinstance(result, SVGDocument)

    def test_stores_scale_for_legend(self, grouped_svg_path):
        doc = SVGDocument.from_file(grouped_svg_path)
        result = doc.heatmap_groups(
            {"north_a": 0.0, "north_b": 1.0}, agg="mean"
        )
        assert result._last_scale is not None
