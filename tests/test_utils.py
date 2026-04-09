"""Comprehensive tests for pathy_svg.utils."""

from __future__ import annotations

import pytest

from pathy_svg.color import hex_to_rgb, interpolate_color, parse_svg_color, rgb_to_hex
from pathy_svg.data import bin_values, normalize_values
from pathy_svg.svg_tools import (
    extract_styles,
    merge_svgs,
    optimize_svg,
    strip_metadata,
    viewbox_to_pixel,
)


# ---------------------------------------------------------------------------
# hex_to_rgb
# ---------------------------------------------------------------------------


class TestHexToRgb:
    def test_six_digit_lowercase(self):
        assert hex_to_rgb("#ff0000") == (255, 0, 0)

    def test_six_digit_uppercase(self):
        assert hex_to_rgb("#FF0000") == (255, 0, 0)

    def test_six_digit_mixed(self):
        assert hex_to_rgb("#0080FF") == (0, 128, 255)

    def test_three_digit(self):
        assert hex_to_rgb("#f00") == (255, 0, 0)

    def test_three_digit_green(self):
        assert hex_to_rgb("#0f0") == (0, 255, 0)

    def test_three_digit_blue(self):
        assert hex_to_rgb("#00f") == (0, 0, 255)

    def test_no_hash(self):
        assert hex_to_rgb("00ff00") == (0, 255, 0)

    def test_black(self):
        assert hex_to_rgb("#000000") == (0, 0, 0)

    def test_white(self):
        assert hex_to_rgb("#ffffff") == (255, 255, 255)

    def test_grey(self):
        assert hex_to_rgb("#808080") == (128, 128, 128)

    def test_invalid_length(self):
        with pytest.raises(ValueError):
            hex_to_rgb("#12345")  # 5 hex digits

    def test_invalid_chars(self):
        with pytest.raises(ValueError):
            hex_to_rgb("#zzzzzz")


# ---------------------------------------------------------------------------
# rgb_to_hex
# ---------------------------------------------------------------------------


class TestRgbToHex:
    def test_red(self):
        assert rgb_to_hex(255, 0, 0) == "#ff0000"

    def test_green(self):
        assert rgb_to_hex(0, 255, 0) == "#00ff00"

    def test_blue(self):
        assert rgb_to_hex(0, 0, 255) == "#0000ff"

    def test_black(self):
        assert rgb_to_hex(0, 0, 0) == "#000000"

    def test_white(self):
        assert rgb_to_hex(255, 255, 255) == "#ffffff"

    def test_mixed(self):
        assert rgb_to_hex(0, 128, 255) == "#0080ff"

    def test_lowercase_output(self):
        result = rgb_to_hex(171, 205, 239)
        assert result == result.lower()

    def test_out_of_range_high(self):
        with pytest.raises(ValueError):
            rgb_to_hex(256, 0, 0)

    def test_out_of_range_low(self):
        with pytest.raises(ValueError):
            rgb_to_hex(-1, 0, 0)

    def test_roundtrip(self):
        for h in ("#ff0000", "#00ff00", "#0000ff", "#808080", "#123456"):
            assert rgb_to_hex(*hex_to_rgb(h)) == h


# ---------------------------------------------------------------------------
# interpolate_color
# ---------------------------------------------------------------------------


class TestInterpolateColor:
    def test_t0_returns_color1(self):
        assert interpolate_color("#000000", "#ffffff", 0.0) == "#000000"

    def test_t1_returns_color2(self):
        assert interpolate_color("#000000", "#ffffff", 1.0) == "#ffffff"

    def test_midpoint(self):
        result = interpolate_color("#000000", "#ffffff", 0.5)
        r, g, b = hex_to_rgb(result)
        assert r == g == b
        assert 127 <= r <= 128  # rounding either way is acceptable

    def test_red_to_blue(self):
        result = interpolate_color("#ff0000", "#0000ff", 0.5)
        r, g, b = hex_to_rgb(result)
        assert r == b
        assert g == 0

    def test_t_out_of_range(self):
        with pytest.raises(ValueError):
            interpolate_color("#000000", "#ffffff", -0.1)
        with pytest.raises(ValueError):
            interpolate_color("#000000", "#ffffff", 1.1)

    def test_returns_hex_string(self):
        result = interpolate_color("#aabbcc", "#112233", 0.3)
        assert result.startswith("#")
        assert len(result) == 7


# ---------------------------------------------------------------------------
# parse_svg_color
# ---------------------------------------------------------------------------


class TestParseSvgColor:
    def test_hex_six(self):
        assert parse_svg_color("#ff0000") == (255, 0, 0)

    def test_hex_three(self):
        assert parse_svg_color("#f00") == (255, 0, 0)

    def test_rgb_function(self):
        assert parse_svg_color("rgb(0, 128, 255)") == (0, 128, 255)

    def test_rgb_no_spaces(self):
        assert parse_svg_color("rgb(255,0,0)") == (255, 0, 0)

    def test_named_red(self):
        assert parse_svg_color("red") == (255, 0, 0)

    def test_named_blue(self):
        assert parse_svg_color("blue") == (0, 0, 255)

    def test_named_green(self):
        # CSS "green" is #008000, not #00ff00
        r, g, b = parse_svg_color("green")
        assert r == 0 and b == 0 and g > 0

    def test_named_white(self):
        assert parse_svg_color("white") == (255, 255, 255)

    def test_named_black(self):
        assert parse_svg_color("black") == (0, 0, 0)

    def test_hsl_red(self):
        # hsl(0, 100%, 50%) == #ff0000
        r, g, b = parse_svg_color("hsl(0, 100%, 50%)")
        assert r == 255 and g == 0 and b == 0

    def test_hsl_green(self):
        # hsl(120, 100%, 50%) == #00ff00
        r, g, b = parse_svg_color("hsl(120, 100%, 50%)")
        assert g == 255 and r == 0 and b == 0

    def test_hsl_blue(self):
        # hsl(240, 100%, 50%) == #0000ff
        r, g, b = parse_svg_color("hsl(240, 100%, 50%)")
        assert b == 255 and r == 0 and g == 0

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            parse_svg_color("notacolor")

    def test_case_insensitive_named(self):
        assert parse_svg_color("Red") == parse_svg_color("red")


# ---------------------------------------------------------------------------
# normalize_values
# ---------------------------------------------------------------------------


class TestNormalizeValues:
    def test_basic(self):
        result = normalize_values({"a": 0, "b": 5, "c": 10})
        assert result == {"a": 0.0, "b": 0.5, "c": 1.0}

    def test_min_max(self):
        result = normalize_values({"x": 2, "y": 4, "z": 8})
        assert result["x"] == pytest.approx(0.0)
        assert result["z"] == pytest.approx(1.0)
        assert result["y"] == pytest.approx((4 - 2) / (8 - 2))

    def test_all_same(self):
        result = normalize_values({"a": 7, "b": 7, "c": 7})
        assert all(v == 0.0 for v in result.values())

    def test_empty(self):
        assert normalize_values({}) == {}

    def test_single_element(self):
        result = normalize_values({"only": 42})
        assert result == {"only": 0.0}

    def test_negative_values(self):
        result = normalize_values({"a": -10, "b": 0, "c": 10})
        assert result["a"] == pytest.approx(0.0)
        assert result["b"] == pytest.approx(0.5)
        assert result["c"] == pytest.approx(1.0)

    def test_keys_preserved(self):
        data = {"alpha": 1.0, "beta": 2.0, "gamma": 3.0}
        result = normalize_values(data)
        assert set(result.keys()) == {"alpha", "beta", "gamma"}


# ---------------------------------------------------------------------------
# bin_values
# ---------------------------------------------------------------------------


class TestBinValues:
    def test_basic(self):
        result = bin_values({"a": 1, "b": 5, "c": 9}, [0, 3, 6, 10])
        assert result == {"a": 0, "b": 1, "c": 2}

    def test_boundary_inclusive_lower(self):
        result = bin_values({"x": 3}, [0, 3, 6])
        # 3 >= 3 → bin 1
        assert result["x"] == 1

    def test_value_below_first_break(self):
        result = bin_values({"x": -5}, [0, 5, 10])
        assert result["x"] == 0

    def test_value_above_last_break(self):
        result = bin_values({"x": 100}, [0, 5, 10])
        assert result["x"] == 1  # last bin

    def test_two_breaks_one_bin(self):
        result = bin_values({"a": 0, "b": 50, "c": 99}, [0, 100])
        assert result == {"a": 0, "b": 0, "c": 0}

    def test_requires_at_least_two_breaks(self):
        with pytest.raises(ValueError):
            bin_values({"a": 1}, [5])

    def test_empty_data(self):
        assert bin_values({}, [0, 5, 10]) == {}

    def test_unsorted_breaks_are_sorted_internally(self):
        result = bin_values({"a": 1, "b": 7}, [10, 0, 5])
        # sorted breaks: [0, 5, 10] → a in bin 0, b in bin 1
        assert result["a"] == 0
        assert result["b"] == 1


# ---------------------------------------------------------------------------
# viewbox_to_pixel
# ---------------------------------------------------------------------------


class TestViewboxToPixel:
    def test_origin(self):
        from pathy_svg.transform import ViewBox

        px, py = viewbox_to_pixel(0, 0, ViewBox(0, 0, 500, 400), 1000, 800)
        assert px == pytest.approx(0.0)
        assert py == pytest.approx(0.0)

    def test_midpoint(self):
        from pathy_svg.transform import ViewBox

        px, py = viewbox_to_pixel(250, 200, ViewBox(0, 0, 500, 400), 1000, 800)
        assert px == pytest.approx(500.0)
        assert py == pytest.approx(400.0)

    def test_full_extent(self):
        from pathy_svg.transform import ViewBox

        px, py = viewbox_to_pixel(500, 400, ViewBox(0, 0, 500, 400), 1000, 800)
        assert px == pytest.approx(1000.0)
        assert py == pytest.approx(800.0)

    def test_nonzero_viewbox_origin(self):
        from pathy_svg.transform import ViewBox

        # viewBox starts at (100, 100)
        px, py = viewbox_to_pixel(100, 100, ViewBox(100, 100, 400, 300), 400, 300)
        assert px == pytest.approx(0.0)
        assert py == pytest.approx(0.0)

    def test_accepts_plain_tuple(self):
        px, py = viewbox_to_pixel(50, 50, (0, 0, 100, 100), 200, 200)
        assert px == pytest.approx(100.0)
        assert py == pytest.approx(100.0)

    def test_zero_viewbox_raises(self):
        with pytest.raises(ValueError):
            viewbox_to_pixel(0, 0, (0, 0, 0, 100), 100, 100)


# ---------------------------------------------------------------------------
# merge_svgs
# ---------------------------------------------------------------------------


class TestMergeSvgs:
    SVG_A = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100"><rect id="a" width="100" height="100" fill="red"/></svg>'
    SVG_B = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100" width="200" height="100"><rect id="b" width="200" height="100" fill="blue"/></svg>'

    def _docs(self):
        from pathy_svg.document import SVGDocument

        return SVGDocument.from_string(self.SVG_A), SVGDocument.from_string(self.SVG_B)

    def test_returns_svgdocument(self):
        from pathy_svg.document import SVGDocument

        a, b = self._docs()
        result = merge_svgs([a, b])
        assert isinstance(result, SVGDocument)

    def test_horizontal_viewbox_width(self):
        a, b = self._docs()
        result = merge_svgs([a, b], layout="horizontal", spacing=10)
        vb = result.viewbox
        assert vb is not None
        # 100 + 10 + 200 = 310
        assert vb.width == pytest.approx(310.0)
        assert vb.height == pytest.approx(100.0)

    def test_vertical_viewbox_height(self):
        a, b = self._docs()
        result = merge_svgs([a, b], layout="vertical", spacing=5)
        vb = result.viewbox
        assert vb is not None
        # 100 + 5 + 100 = 205
        assert vb.height == pytest.approx(205.0)
        assert vb.width == pytest.approx(200.0)

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            merge_svgs([])

    def test_single_svg(self):
        from pathy_svg.document import SVGDocument

        a, _ = self._docs()
        result = merge_svgs([a])
        assert isinstance(result, SVGDocument)
        vb = result.viewbox
        assert vb.width == pytest.approx(100.0)

    def test_children_preserved(self):
        a, b = self._docs()
        result = merge_svgs([a, b])
        svg_str = result.to_string()
        assert 'id="a"' in svg_str
        assert 'id="b"' in svg_str


# ---------------------------------------------------------------------------
# strip_metadata
# ---------------------------------------------------------------------------


class TestStripMetadata:
    INKSCAPE_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.0.dtd"
     xmlns:dc="http://purl.org/dc/elements/1.1/"
     xmlns:cc="http://creativecommons.org/ns#"
     xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
     viewBox="0 0 100 100">
  <metadata>
    <rdf:RDF>
      <cc:Work>
        <dc:title>Test</dc:title>
      </cc:Work>
    </rdf:RDF>
  </metadata>
  <inkscape:label>Test label</inkscape:label>
  <sodipodi:namedview/>
  <rect id="r1" width="100" height="100" fill="green"/>
</svg>"""

    def test_removes_metadata_element(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(self.INKSCAPE_SVG)
        result = strip_metadata(doc)
        svg_str = result.to_string()
        assert "<metadata" not in svg_str

    def test_removes_sodipodi_elements(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(self.INKSCAPE_SVG)
        result = strip_metadata(doc)
        svg_str = result.to_string()
        assert "sodipodi" not in svg_str

    def test_removes_inkscape_elements(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(self.INKSCAPE_SVG)
        result = strip_metadata(doc)
        svg_str = result.to_string()
        assert "inkscape:label" not in svg_str

    def test_keeps_regular_elements(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(self.INKSCAPE_SVG)
        result = strip_metadata(doc)
        svg_str = result.to_string()
        assert 'id="r1"' in svg_str

    def test_returns_svgdocument(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(self.INKSCAPE_SVG)
        result = strip_metadata(doc)
        assert isinstance(result, SVGDocument)

    def test_clean_svg_unchanged(self, simple_svg_path):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_file(simple_svg_path)
        result = strip_metadata(doc)
        # The rect and paths should still be there
        assert "stomach" in result.to_string()


# ---------------------------------------------------------------------------
# optimize_svg
# ---------------------------------------------------------------------------


class TestOptimizeSvg:
    COMMENTED_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <!-- This is a comment -->
  <!-- Another comment -->
  <rect id="r" width="100" height="100" fill="red"/>
  <g>
    <!-- nested comment -->
    <path id="p" d="M 0 0 L 10 10"/>
  </g>
</svg>"""

    def test_removes_comments(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(self.COMMENTED_SVG)
        result = optimize_svg(doc)
        svg_str = result.to_string()
        assert "<!--" not in svg_str
        assert "-->" not in svg_str

    def test_preserves_elements(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(self.COMMENTED_SVG)
        result = optimize_svg(doc)
        svg_str = result.to_string()
        assert 'id="r"' in svg_str
        assert 'id="p"' in svg_str

    def test_returns_svgdocument(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(self.COMMENTED_SVG)
        result = optimize_svg(doc)
        assert isinstance(result, SVGDocument)

    def test_no_comments_svg_unchanged_structurally(self, simple_svg_path):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_file(simple_svg_path)
        result = optimize_svg(doc)
        # All path IDs should still be present
        for pid in ["stomach", "liver", "heart", "lung_l", "lung_r"]:
            assert pid in result.to_string()

    def test_does_not_modify_original(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(self.COMMENTED_SVG)
        _ = optimize_svg(doc)
        # Original should still have comments
        original_str = doc.to_string()
        assert "<!--" in original_str


# ---------------------------------------------------------------------------
# extract_styles
# ---------------------------------------------------------------------------


class TestExtractStyles:
    INLINE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
  <rect id="r1" style="fill:red;stroke:black" width="100" height="100"/>
  <rect id="r2" style="fill:blue" width="50" height="50"/>
  <rect id="r3" style="fill:red;stroke:black" width="30" height="30"/>
</svg>"""

    def test_creates_style_element(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(self.INLINE_SVG)
        result = extract_styles(doc)
        svg_str = result.to_string()
        assert "<style" in svg_str

    def test_removes_inline_style_attrs(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(self.INLINE_SVG)
        result = extract_styles(doc)

        for elem in result.root.iter():
            assert elem.get("style") is None, f"Found inline style on {elem.tag}"

    def test_adds_class_attrs(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(self.INLINE_SVG)
        result = extract_styles(doc)
        svg_str = result.to_string()
        assert 'class="pathy-s' in svg_str

    def test_deduplicates_identical_styles(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(self.INLINE_SVG)
        result = extract_styles(doc)
        svg_str = result.to_string()
        # r1 and r3 share the same style, so only one class definition
        # Count occurrences of "fill:red;stroke:black" (should be 1 in <style>)
        import re

        style_block_match = re.search(r"<style[^>]*>(.*?)</style>", svg_str, re.DOTALL)
        assert style_block_match is not None
        style_content = style_block_match.group(1)
        assert style_content.count("fill:red") == 1

    def test_places_style_in_defs(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(self.INLINE_SVG)
        result = extract_styles(doc)
        svg_str = result.to_string()
        # <defs> should appear before <style>
        defs_pos = svg_str.find("<defs")
        style_pos = svg_str.find("<style")
        assert defs_pos != -1 and style_pos != -1
        assert defs_pos < style_pos

    def test_returns_svgdocument(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(self.INLINE_SVG)
        result = extract_styles(doc)
        assert isinstance(result, SVGDocument)

    def test_no_styles_returns_unchanged(self):
        from pathy_svg.document import SVGDocument

        svg = '<svg xmlns="http://www.w3.org/2000/svg"><rect id="r" fill="red"/></svg>'
        doc = SVGDocument.from_string(svg)
        result = extract_styles(doc)
        svg_str = result.to_string()
        assert "<style" not in svg_str

    def test_does_not_modify_original(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(self.INLINE_SVG)
        _ = extract_styles(doc)
        original_str = doc.to_string()
        assert 'style="fill:red' in original_str


# ---------------------------------------------------------------------------
# Top-level import check
# ---------------------------------------------------------------------------


class TestTopLevelImports:
    def test_all_utils_importable_from_package(self):
        import pathy_svg

        for name in [
            "hex_to_rgb",
            "rgb_to_hex",
            "interpolate_color",
            "parse_svg_color",
            "normalize_values",
            "bin_values",
            "viewbox_to_pixel",
            "merge_svgs",
            "strip_metadata",
            "optimize_svg",
            "extract_styles",
        ]:
            assert hasattr(pathy_svg, name), f"Missing from pathy_svg: {name}"
