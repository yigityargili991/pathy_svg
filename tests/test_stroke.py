"""Tests for pathy_svg.stroke module."""

import pytest
from lxml import etree

from pathy_svg.stroke import apply_stroke_map
from pathy_svg.document import SVGDocument


def _make_tree():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<path id="a" d="M 0 0 L 50 50 Z" fill="#fff" stroke="#000" stroke-width="1"/>'
        '<path id="b" d="M 10 10 L 60 60 Z" fill="#fff" stroke="#000" stroke-width="1"/>'
        "</svg>"
    )
    return etree.ElementTree(etree.fromstring(svg.encode()))


def _make_grouped_tree():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<g id="grp"><path id="c1" d="M 0 0 L 50 50 Z" fill="#fff" stroke="#000"/>'
        '<path id="c2" d="M 10 10 L 60 60 Z" fill="#fff" stroke="#000"/></g>'
        "</svg>"
    )
    return etree.ElementTree(etree.fromstring(svg.encode()))


class TestApplyStrokeMapWidth:
    def test_maps_data_to_stroke_width(self):
        tree = _make_tree()
        apply_stroke_map(tree, {"a": 0.0, "b": 1.0}, width_range=(1.0, 5.0))

        ns = "{http://www.w3.org/2000/svg}"
        a = tree.getroot().find(f".//{ns}path[@id='a']")
        b = tree.getroot().find(f".//{ns}path[@id='b']")
        a_width = float(a.get("stroke-width"))
        b_width = float(b.get("stroke-width"))
        assert a_width == pytest.approx(1.0)
        assert b_width == pytest.approx(5.0)

    def test_midpoint_value_gets_midpoint_width(self):
        tree = _make_tree()
        apply_stroke_map(tree, {"a": 0.5}, width_range=(1.0, 5.0), vmin=0.0, vmax=1.0)

        ns = "{http://www.w3.org/2000/svg}"
        a = tree.getroot().find(f".//{ns}path[@id='a']")
        assert float(a.get("stroke-width")) == pytest.approx(3.0)

    def test_does_not_touch_fill(self):
        tree = _make_tree()
        apply_stroke_map(tree, {"a": 0.5}, width_range=(1.0, 5.0))

        ns = "{http://www.w3.org/2000/svg}"
        a = tree.getroot().find(f".//{ns}path[@id='a']")
        assert a.get("fill") == "#fff"

    def test_na_width_for_nan(self):
        tree = _make_tree()
        apply_stroke_map(
            tree, {"a": float("nan")}, width_range=(1.0, 5.0), na_width=2.0
        )

        ns = "{http://www.w3.org/2000/svg}"
        a = tree.getroot().find(f".//{ns}path[@id='a']")
        assert float(a.get("stroke-width")) == pytest.approx(2.0)


class TestApplyStrokeMapColor:
    def test_maps_data_to_stroke_color(self):
        tree = _make_tree()
        scale = apply_stroke_map(
            tree, {"a": 0.0, "b": 1.0}, width_range=None, palette="viridis"
        )

        ns = "{http://www.w3.org/2000/svg}"
        a_stroke = tree.getroot().find(f".//{ns}path[@id='a']").get("stroke")
        b_stroke = tree.getroot().find(f".//{ns}path[@id='b']").get("stroke")
        assert a_stroke != b_stroke
        assert a_stroke.startswith("#")
        assert scale is not None

    def test_na_color_for_nan(self):
        tree = _make_tree()
        apply_stroke_map(
            tree,
            {"a": float("nan")},
            width_range=None,
            palette="viridis",
            na_color="#aabbcc",
        )

        ns = "{http://www.w3.org/2000/svg}"
        a_stroke = tree.getroot().find(f".//{ns}path[@id='a']").get("stroke")
        assert a_stroke == "#aabbcc"


class TestApplyStrokeMapBoth:
    def test_width_and_color_together(self):
        tree = _make_tree()
        apply_stroke_map(
            tree,
            {"a": 0.0, "b": 1.0},
            width_range=(1.0, 5.0),
            palette="viridis",
        )

        ns = "{http://www.w3.org/2000/svg}"
        a = tree.getroot().find(f".//{ns}path[@id='a']")
        b = tree.getroot().find(f".//{ns}path[@id='b']")
        assert float(a.get("stroke-width")) != float(b.get("stroke-width"))
        assert a.get("stroke") != b.get("stroke")


class TestApplyStrokeMapEdge:
    def test_nonexistent_id_skipped(self):
        tree = _make_tree()
        apply_stroke_map(tree, {"nonexistent": 0.5}, width_range=(1.0, 5.0))

    def test_empty_data(self):
        tree = _make_tree()
        scale = apply_stroke_map(tree, {}, width_range=(1.0, 5.0))
        assert scale is None

    def test_group_stroke(self):
        tree = _make_grouped_tree()
        apply_stroke_map(tree, {"grp": 1.0}, width_range=(1.0, 5.0), vmin=0.0, vmax=1.0)

        ns = "{http://www.w3.org/2000/svg}"
        c1 = tree.getroot().find(f".//{ns}path[@id='c1']")
        c2 = tree.getroot().find(f".//{ns}path[@id='c2']")
        assert float(c1.get("stroke-width")) == pytest.approx(5.0)
        assert float(c2.get("stroke-width")) == pytest.approx(5.0)

    def test_opacity(self):
        tree = _make_tree()
        apply_stroke_map(tree, {"a": 0.5}, width_range=(1.0, 5.0), opacity=0.5)

        ns = "{http://www.w3.org/2000/svg}"
        a = tree.getroot().find(f".//{ns}path[@id='a']")
        assert a.get("stroke-opacity") == "0.5"
