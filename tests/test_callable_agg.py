"""Tests for callable aggregation in aggregate_by_group."""

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
        "</g>"
        "</svg>"
    )
    return etree.ElementTree(etree.fromstring(svg.encode()))


class TestCallableAgg:
    def test_custom_callable(self):
        tree = _make_grouped_tree()
        data = {"north_a": 10.0, "north_b": 20.0}
        result = aggregate_by_group(tree, data, agg=lambda vals: max(vals) - min(vals))
        assert result["north"] == pytest.approx(10.0)

    def test_callable_single_value(self):
        tree = _make_grouped_tree()
        data = {"south_a": 42.0}
        result = aggregate_by_group(tree, data, agg=lambda vals: vals[0] * 2)
        assert result["south"] == pytest.approx(84.0)

    def test_string_agg_still_works(self):
        tree = _make_grouped_tree()
        data = {"north_a": 10.0, "north_b": 20.0}
        result = aggregate_by_group(tree, data, agg="sum")
        assert result["north"] == pytest.approx(30.0)

    def test_invalid_string_still_raises(self):
        tree = _make_grouped_tree()
        with pytest.raises(ValueError, match="Unknown aggregation"):
            aggregate_by_group(tree, {"north_a": 10.0}, agg="invalid")

    def test_callable_via_mixin(self, grouped_svg_path):
        doc = SVGDocument.from_file(grouped_svg_path)
        data = {"north_a": 10.0, "north_b": 30.0, "south_a": 5.0, "south_b": 15.0}
        result = doc.heatmap_groups(data, agg=lambda vals: sum(vals) / len(vals))
        assert result._last_scale is not None
