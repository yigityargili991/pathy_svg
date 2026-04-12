"""Tests for pathy_svg.gradient module."""

import re

from lxml import etree

from pathy_svg.gradient import GradientSpec, apply_gradient_fill
from pathy_svg.document import SVGDocument


def _make_tree():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<path id="a" d="M 0 0 L 50 50 Z" fill="#fff"/>'
        '<path id="b" d="M 10 10 L 60 60 Z" fill="#fff"/>'
        "</svg>"
    )
    return etree.ElementTree(etree.fromstring(svg.encode()))


def _make_grouped_tree():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<g id="grp"><path id="c1" d="M 0 0 L 50 50 Z" fill="#fff"/>'
        '<path id="c2" d="M 10 10 L 60 60 Z" fill="#fff"/></g>'
        "</svg>"
    )
    return etree.ElementTree(etree.fromstring(svg.encode()))


class TestGradientSpec:
    def test_defaults(self):
        spec = GradientSpec(start="#ff0000", end="#0000ff")
        assert spec.direction == "horizontal"
        assert spec.mid is None

    def test_with_mid(self):
        spec = GradientSpec(start="#ff0000", end="#0000ff", mid="#00ff00")
        assert spec.mid == "#00ff00"


class TestApplyGradientFill:
    def test_creates_linear_gradient_in_defs(self):
        tree = _make_tree()
        spec = GradientSpec(start="#ff0000", end="#0000ff")
        apply_gradient_fill(tree, {"a": spec})

        svg_str = etree.tostring(tree, encoding="unicode")
        assert "<linearGradient" in svg_str or "linearGradient" in svg_str
        assert 'stop-color:#ff0000' in svg_str
        assert 'stop-color:#0000ff' in svg_str

    def test_element_fill_references_gradient(self):
        tree = _make_tree()
        spec = GradientSpec(start="#ff0000", end="#0000ff")
        apply_gradient_fill(tree, {"a": spec})

        ns = "{http://www.w3.org/2000/svg}"
        elem = tree.getroot().find(f".//{ns}path[@id='a']")
        fill = elem.get("fill", "")
        assert fill.startswith("url(#pathy-grad-")

    def test_horizontal_direction(self):
        tree = _make_tree()
        spec = GradientSpec(start="#ff0000", end="#0000ff", direction="horizontal")
        apply_gradient_fill(tree, {"a": spec})

        ns = "{http://www.w3.org/2000/svg}"
        grad = tree.getroot().find(f".//{ns}linearGradient")
        assert grad.get("x1") == "0"
        assert grad.get("y1") == "0"
        assert grad.get("x2") == "1"
        assert grad.get("y2") == "0"

    def test_vertical_direction(self):
        tree = _make_tree()
        spec = GradientSpec(start="#ff0000", end="#0000ff", direction="vertical")
        apply_gradient_fill(tree, {"a": spec})

        ns = "{http://www.w3.org/2000/svg}"
        grad = tree.getroot().find(f".//{ns}linearGradient")
        assert grad.get("x2") == "0"
        assert grad.get("y2") == "1"

    def test_diagonal_direction(self):
        tree = _make_tree()
        spec = GradientSpec(start="#ff0000", end="#0000ff", direction="diagonal")
        apply_gradient_fill(tree, {"a": spec})

        ns = "{http://www.w3.org/2000/svg}"
        grad = tree.getroot().find(f".//{ns}linearGradient")
        assert grad.get("x2") == "1"
        assert grad.get("y2") == "1"

    def test_mid_color_creates_three_stops(self):
        tree = _make_tree()
        spec = GradientSpec(start="#ff0000", end="#0000ff", mid="#00ff00")
        apply_gradient_fill(tree, {"a": spec})

        ns = "{http://www.w3.org/2000/svg}"
        grad = tree.getroot().find(f".//{ns}linearGradient")
        stops = grad.findall(f"{ns}stop")
        assert len(stops) == 3
        assert 'stop-color:#00ff00' in stops[1].get("style", "")

    def test_two_stops_without_mid(self):
        tree = _make_tree()
        spec = GradientSpec(start="#ff0000", end="#0000ff")
        apply_gradient_fill(tree, {"a": spec})

        ns = "{http://www.w3.org/2000/svg}"
        grad = tree.getroot().find(f".//{ns}linearGradient")
        stops = grad.findall(f"{ns}stop")
        assert len(stops) == 2

    def test_multiple_elements_get_separate_gradients(self):
        tree = _make_tree()
        apply_gradient_fill(tree, {
            "a": GradientSpec(start="#ff0000", end="#0000ff"),
            "b": GradientSpec(start="#00ff00", end="#ffff00"),
        })

        svg_str = etree.tostring(tree, encoding="unicode")
        # Count linearGradient occurrences
        count = svg_str.count("linearGradient")
        # Each gradient has opening tag, so at least 2 opening tags
        assert count >= 4  # 2 opening + 2 closing

        ns = "{http://www.w3.org/2000/svg}"
        a_fill = tree.getroot().find(f".//{ns}path[@id='a']").get("fill")
        b_fill = tree.getroot().find(f".//{ns}path[@id='b']").get("fill")
        assert a_fill != b_fill

    def test_nonexistent_id_skipped(self):
        tree = _make_tree()
        apply_gradient_fill(tree, {
            "nonexistent": GradientSpec(start="#ff0000", end="#0000ff"),
        })
        svg_str = etree.tostring(tree, encoding="unicode")
        assert "linearGradient" not in svg_str

    def test_group_gradient(self):
        tree = _make_grouped_tree()
        spec = GradientSpec(start="#ff0000", end="#0000ff")
        apply_gradient_fill(tree, {"grp": spec})

        ns = "{http://www.w3.org/2000/svg}"
        c1 = tree.getroot().find(f".//{ns}path[@id='c1']")
        c2 = tree.getroot().find(f".//{ns}path[@id='c2']")
        assert c1.get("fill", "").startswith("url(#pathy-grad-")
        assert c2.get("fill", "").startswith("url(#pathy-grad-")

    def test_opacity(self):
        tree = _make_tree()
        spec = GradientSpec(start="#ff0000", end="#0000ff")
        apply_gradient_fill(tree, {"a": spec}, opacity=0.5)

        ns = "{http://www.w3.org/2000/svg}"
        elem = tree.getroot().find(f".//{ns}path[@id='a']")
        assert elem.get("fill-opacity") == "0.5"
