"""Tests for pathy_svg.animation module."""

import pytest

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
