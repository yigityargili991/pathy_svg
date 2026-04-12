"""Tests for pathy_svg.animation module."""

import pytest

from lxml import etree

from pathy_svg.animation import inject_animation
from pathy_svg.document import SVGDocument


class TestAnimate:
    def test_pulse(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.heatmap({"stomach": 0.5}).animate(effect="pulse")
        svg_str = result.to_string()
        assert "@keyframes" in svg_str
        assert "pathy-pulse" in svg_str

    def test_fade_in(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.animate(effect="fade_in")
        svg_str = result.to_string()
        assert "pathy-fade" in svg_str

    def test_blink(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.animate(effect="blink", duration=1.0)
        svg_str = result.to_string()
        assert "pathy-blink" in svg_str

    def test_sequential(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.animate(effect="sequential")
        svg_str = result.to_string()
        assert "pathy-seq" in svg_str

    def test_immutability(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.animate(effect="pulse")
        assert "@keyframes" not in doc.to_string()
        assert "@keyframes" in result.to_string()

    def test_invalid_effect(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        with pytest.raises(ValueError):
            doc.animate(effect="nonexistent")


class TestInjectAnimationDirect:
    def _make_tree(self):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            '<path id="a" d="M 0 0 L 10 10"/>'
            '<path id="b" d="M 0 0 L 20 20"/>'
            '<path id="c" d="M 0 0 L 30 30"/>'
            "</svg>"
        )
        return etree.ElementTree(etree.fromstring(svg.encode()))

    def test_sequential_with_data_order(self):
        tree = self._make_tree()
        inject_animation(tree, effect="sequential", data_order=["a", "b", "c"])
        style = tree.getroot().find(".//{http://www.w3.org/2000/svg}style")
        assert style is not None
        css = style.text
        assert "pathy-seq" in css
        assert 'id="a"' in css
        assert 'id="b"' in css
        assert 'id="c"' in css
        assert "animation-delay:" in css

    def test_sequential_with_data_order_no_loop(self):
        tree = self._make_tree()
        inject_animation(tree, effect="sequential", data_order=["a", "b"], loop=False)
        style = tree.getroot().find(".//{http://www.w3.org/2000/svg}style")
        css = style.text
        assert "animation-delay:" in css
        assert "1" in css  # iteration count is 1 (not infinite)

    def test_sequential_without_data_order(self):
        tree = self._make_tree()
        inject_animation(tree, effect="sequential", data_order=None)
        style = tree.getroot().find(".//{http://www.w3.org/2000/svg}style")
        assert style is not None
        assert "pathy-seq" in style.text

    def test_pulse_no_loop(self):
        tree = self._make_tree()
        inject_animation(tree, effect="pulse", loop=False, duration=3.0)
        style = tree.getroot().find(".//{http://www.w3.org/2000/svg}style")
        css = style.text
        assert "3.0s" in css
        assert "1;" in css  # not infinite

    def test_creates_defs_if_missing(self):
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><path id="x" d="M 0 0"/></svg>'
        tree = etree.ElementTree(etree.fromstring(svg.encode()))
        defs_before = tree.getroot().find("{http://www.w3.org/2000/svg}defs")
        assert defs_before is None
        inject_animation(tree, effect="pulse")
        defs_after = tree.getroot().find("{http://www.w3.org/2000/svg}defs")
        assert defs_after is not None

    def test_invalid_effect_raises(self):
        tree = self._make_tree()
        with pytest.raises(ValueError, match="Unknown animation effect"):
            inject_animation(tree, effect="spin")
