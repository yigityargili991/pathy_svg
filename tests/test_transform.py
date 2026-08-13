"""Tests for pathy_svg.transform module."""

import math

import numpy as np
import pytest
from lxml import etree

from pathy_svg.transform import (
    BBox,
    ViewBox,
    _parse_transform,
    bbox_from_path_d,
    bbox_of_element,
    bbox_union,
    centroid_of_bbox,
    parse_viewbox,
)


class TestParseViewBox:
    def test_space_separated(self):
        assert parse_viewbox("0 0 500 400") == ViewBox(0, 0, 500, 400)

    def test_comma_separated(self):
        assert parse_viewbox("10,20,300,200") == ViewBox(10, 20, 300, 200)

    def test_mixed_separators(self):
        assert parse_viewbox("0, 0 100, 100") == ViewBox(0, 0, 100, 100)

    def test_floats(self):
        assert parse_viewbox("0.5 1.5 99.5 49.5") == ViewBox(0.5, 1.5, 99.5, 49.5)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_viewbox("0 0 100")


class TestCentroid:
    def test_simple(self):
        bbox = BBox(0, 0, 100, 50)
        assert centroid_of_bbox(bbox) == (50.0, 25.0)

    def test_offset(self):
        bbox = BBox(10, 20, 100, 50)
        cx, cy = centroid_of_bbox(bbox)
        assert cx == pytest.approx(60.0)
        assert cy == pytest.approx(45.0)


class TestBBoxUnion:
    def test_two_boxes(self):
        b1 = BBox(0, 0, 50, 50)
        b2 = BBox(30, 30, 50, 50)
        result = bbox_union([b1, b2])
        assert result == BBox(0, 0, 80, 80)

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            bbox_union([])


class TestBBoxFromPathD:
    def test_simple_rect(self):
        d = "M 10 10 L 100 10 L 100 80 L 10 80 Z"
        bbox = bbox_from_path_d(d)
        assert bbox.x == pytest.approx(10)
        assert bbox.y == pytest.approx(10)
        assert bbox.width == pytest.approx(90)
        assert bbox.height == pytest.approx(70)

    def test_relative_commands(self):
        d = "M 10 10 l 90 0 l 0 70 l -90 0 z"
        bbox = bbox_from_path_d(d)
        assert bbox.x == pytest.approx(10)
        assert bbox.y == pytest.approx(10)
        assert bbox.width == pytest.approx(90)
        assert bbox.height == pytest.approx(70)

    def test_horizontal_vertical(self):
        d = "M 0 0 H 50 V 30 H 0 Z"
        bbox = bbox_from_path_d(d)
        assert bbox.x == pytest.approx(0)
        assert bbox.y == pytest.approx(0)
        assert bbox.width == pytest.approx(50)
        assert bbox.height == pytest.approx(30)

    def test_cubic_bezier(self):
        # Heart-like shape from our fixture
        d = "M 250 250 C 250 220 280 200 300 230 C 320 200 350 220 350 250 L 300 310 Z"
        bbox = bbox_from_path_d(d)
        # Control points included, so bbox should cover them
        assert bbox.x == pytest.approx(250)
        assert bbox.y == pytest.approx(200)
        assert bbox.width == pytest.approx(100)
        assert bbox.height == pytest.approx(110)

    def test_empty_path(self):
        bbox = bbox_from_path_d("")
        assert bbox == BBox(0, 0, 0, 0)

    @pytest.mark.parametrize("d", ["none", " NONE ", "\tnOnE\n"])
    def test_none_path_has_no_direct_geometry(self, d):
        assert bbox_from_path_d(d) == BBox(0, 0, 0, 0)

    def test_text_starting_like_none_yields_empty_bbox(self):
        assert bbox_from_path_d("none-ish") == BBox(0, 0, 0, 0)

    def test_truncated_trailing_parameters_parse_valid_prefix(self):
        assert bbox_from_path_d("M 10 20 L 30 40 L 50") == BBox(10, 20, 20, 20)

    def test_junk_suffix_parses_valid_prefix(self):
        assert bbox_from_path_d("M0 0 L10 10 garbage") == BBox(0, 0, 10, 10)

    def test_junk_before_any_command_yields_empty_bbox(self):
        assert bbox_from_path_d("garbage M 10 20") == BBox(0, 0, 0, 0)

    def test_truncated_moveto_yields_empty_bbox(self):
        assert bbox_from_path_d("M 10") == BBox(0, 0, 0, 0)

    def test_invalid_arc_flag_parses_valid_prefix(self):
        d = "M 0 0 L 10 10 A 5 5 0 X 1 20 20"
        assert bbox_from_path_d(d) == BBox(0, 0, 10, 10)

    def test_relative_h_v(self):
        d = "M 10 10 h 40 v 20 h -40 z"
        bbox = bbox_from_path_d(d)
        assert bbox.x == pytest.approx(10)
        assert bbox.y == pytest.approx(10)
        assert bbox.width == pytest.approx(40)
        assert bbox.height == pytest.approx(20)

    def test_relative_cubic(self):
        d = "M 10 10 c 10 -10 30 -10 40 0 c 10 10 30 10 40 0"
        bbox = bbox_from_path_d(d)
        assert bbox.x == pytest.approx(10)
        assert bbox.y == pytest.approx(0)
        assert bbox.width == pytest.approx(80)
        assert bbox.height == pytest.approx(20)

    def test_smooth_cubic_absolute(self):
        d = "M 0 0 S 50 50 100 0"
        bbox = bbox_from_path_d(d)
        assert bbox.x == pytest.approx(0)
        assert bbox.y == pytest.approx(0)
        assert bbox.width == pytest.approx(100)
        assert bbox.height == pytest.approx(50)

    def test_smooth_cubic_relative(self):
        d = "M 0 0 s 50 50 100 0"
        bbox = bbox_from_path_d(d)
        assert bbox.x == pytest.approx(0)
        assert bbox.y == pytest.approx(0)
        assert bbox.width == pytest.approx(100)
        assert bbox.height == pytest.approx(50)

    def test_smooth_cubic_includes_reflected_control(self):
        d = "M 0 0 C 10 100 20 100 30 0 S 50 0 60 0"
        assert bbox_from_path_d(d) == pytest.approx(BBox(0, -100, 60, 200))

    def test_smooth_cubic_resets_reflection_after_line(self):
        d = "M 0 0 C 10 -100 20 -100 30 0 L 40 0 S 50 0 60 0"
        assert bbox_from_path_d(d) == pytest.approx(BBox(0, -100, 60, 100))

    def test_repeated_relative_smooth_cubic_updates_reflected_control(self):
        d = "M 0 0 c 10 20 20 20 30 0 s 10 0 20 0 10 0 20 0"
        assert bbox_from_path_d(d) == pytest.approx(BBox(0, -20, 70, 40))

    def test_quadratic_absolute(self):
        d = "M 0 0 Q 50 100 100 0"
        bbox = bbox_from_path_d(d)
        assert bbox.x == pytest.approx(0)
        assert bbox.y == pytest.approx(0)
        assert bbox.width == pytest.approx(100)
        assert bbox.height == pytest.approx(100)

    def test_quadratic_relative(self):
        d = "M 0 0 q 50 100 100 0"
        bbox = bbox_from_path_d(d)
        assert bbox.x == pytest.approx(0)
        assert bbox.y == pytest.approx(0)
        assert bbox.width == pytest.approx(100)
        assert bbox.height == pytest.approx(100)

    def test_shorthand_quadratic_absolute(self):
        d = "M 0 0 T 100 50"
        bbox = bbox_from_path_d(d)
        assert bbox.x == pytest.approx(0)
        assert bbox.y == pytest.approx(0)
        assert bbox.width == pytest.approx(100)
        assert bbox.height == pytest.approx(50)

    def test_shorthand_quadratic_relative(self):
        d = "M 10 10 t 90 40"
        bbox = bbox_from_path_d(d)
        assert bbox.x == pytest.approx(10)
        assert bbox.y == pytest.approx(10)
        assert bbox.width == pytest.approx(90)
        assert bbox.height == pytest.approx(40)

    def test_smooth_quadratic_includes_reflected_control(self):
        d = "M 0 0 Q 10 100 20 0 T 40 0"
        assert bbox_from_path_d(d) == pytest.approx(BBox(0, -100, 40, 200))

    def test_smooth_quadratic_resets_reflection_after_close(self):
        d = "M 0 0 Q 10 -100 20 0 Z T 40 0"
        assert bbox_from_path_d(d) == pytest.approx(BBox(0, -100, 40, 100))

    def test_repeated_relative_smooth_quadratic_updates_reflected_control(self):
        d = "M 0 0 q 10 20 20 0 t 20 0 20 0"
        assert bbox_from_path_d(d) == pytest.approx(BBox(0, -20, 60, 40))

    def test_arc_absolute(self):
        d = "M 0 0 A 50 50 0 0 1 100 0"
        bbox = bbox_from_path_d(d)
        assert bbox.x == pytest.approx(0)
        assert bbox.y == pytest.approx(-50)
        assert bbox.width == pytest.approx(100)
        assert bbox.height == pytest.approx(50)

    def test_arc_sweep_direction_selects_other_semicircle(self):
        d = "M 0 0 A 50 50 0 0 0 100 0"
        bbox = bbox_from_path_d(d)
        assert bbox == pytest.approx(BBox(0, 0, 100, 50))

    def test_arc_relative(self):
        d = "M 10 20 a 50 50 0 0 1 100 0"
        bbox = bbox_from_path_d(d)
        assert bbox.x == pytest.approx(10)
        assert bbox.y == pytest.approx(-30)
        assert bbox.width == pytest.approx(100)
        assert bbox.height == pytest.approx(50)

    def test_rotated_elliptical_arc_extrema(self):
        diagonal = 30 * 2**0.5
        d = f"M {-diagonal} {-diagonal} A 60 20 45 0 1 {diagonal} {diagonal}"
        bbox = bbox_from_path_d(d)
        assert bbox.x == pytest.approx(-diagonal)
        assert bbox.y == pytest.approx(-20 * 5**0.5)
        assert bbox.width == pytest.approx(diagonal + 20 * 5**0.5)
        assert bbox.height == pytest.approx(diagonal + 20 * 5**0.5)

    def test_large_arc_includes_long_sweep_extrema(self):
        small = bbox_from_path_d("M 50 0 A 50 50 0 0 1 0 50")
        large = bbox_from_path_d("M 50 0 A 50 50 0 1 1 0 50")
        assert small == pytest.approx(BBox(0, 0, 50, 50))
        assert large == pytest.approx(BBox(0, 0, 100, 100))

    def test_repeated_arc_segments(self):
        d = "M 0 0 A 10 10 0 0 1 10 10 10 10 0 0 1 20 0"
        bbox = bbox_from_path_d(d)
        assert bbox == pytest.approx(BBox(0, 0, 20, 10))

    @pytest.mark.parametrize(
        "d, expected",
        [
            ("M 10 20 A 0 30 45 1 1 50 60", BBox(10, 20, 40, 40)),
            ("M 10 20 A 30 20 45 1 1 10 20", BBox(10, 20, 0, 0)),
        ],
    )
    def test_degenerate_arc(self, d, expected):
        assert bbox_from_path_d(d) == pytest.approx(expected)

    @pytest.mark.parametrize(
        ("large_arc", "sweep"),
        [(0, 0), (0, 1), (1, 0), (1, 1)],
    )
    def test_compact_arc_flags_match_separated_flags(self, large_arc, sweep):
        compact = f"M0 0A10 10 0 {large_arc}{sweep}10 10"
        separated = f"M0 0A10 10 0 {large_arc} {sweep} 10 10"
        assert bbox_from_path_d(compact) == pytest.approx(bbox_from_path_d(separated))

    def test_compact_flags_in_repeated_relative_arcs(self):
        compact = "M0 0a10 10 0 0110 10 10 10 0 10-10 10"
        separated = "M0 0a10 10 0 0 1 10 10 10 10 0 1 0 -10 10"
        assert bbox_from_path_d(compact) == pytest.approx(bbox_from_path_d(separated))

    @pytest.mark.parametrize(
        "arc",
        [
            "A10 10 0 2 1 10 10",
            "A10 10 0 01 10",
            "A10 10 0 01x 10",
        ],
    )
    def test_malformed_arc_data_uses_valid_prefix(self, arc):
        # Best-effort parsing keeps the valid prefix and drops the broken arc.
        assert bbox_from_path_d(f"M0 0 L5 5 {arc}") == BBox(0, 0, 5, 5)

    def test_relative_moveto(self):
        d = "M 10 10 m 20 20 L 50 50"
        bbox = bbox_from_path_d(d)
        assert bbox.x == pytest.approx(10)
        assert bbox.y == pytest.approx(10)
        assert bbox.width == pytest.approx(40)
        assert bbox.height == pytest.approx(40)


class TestBBoxOfElement:
    def test_rect_element(self):
        elem = etree.Element("rect", x="10", y="20", width="100", height="50")
        bbox = bbox_of_element(elem, {})
        assert bbox == BBox(10, 20, 100, 50)

    def test_circle_element(self):
        elem = etree.Element("circle", cx="50", cy="50", r="25")
        bbox = bbox_of_element(elem, {})
        assert bbox == BBox(25, 25, 50, 50)

    def test_path_element(self):
        elem = etree.Element("path", d="M 0 0 L 100 0 L 100 50 Z")
        bbox = bbox_of_element(elem, {})
        assert bbox is not None
        assert bbox.width == pytest.approx(100)
        assert bbox.height == pytest.approx(50)

    @pytest.mark.parametrize("d", ["none", " NONE ", "\tnOnE\n"])
    def test_none_path_element_has_no_bbox(self, d):
        elem = etree.Element("path", d=d)
        assert bbox_of_element(elem, {}) is None


class TestNestedSvgViewport:
    def test_nonzero_viewbox_maps_into_nested_viewport(self):
        outer = etree.Element("svg")
        nested = etree.SubElement(
            outer, "svg", width="20", height="30", viewBox="100 50 20 30"
        )
        rect = etree.SubElement(
            nested, "rect", x="100", y="50", width="20", height="30"
        )
        assert bbox_of_element(rect, {}) == pytest.approx(BBox(0, 0, 20, 30))
        assert bbox_of_element(nested, {}) == pytest.approx(BBox(0, 0, 20, 30))

    def test_preserve_aspect_ratio_none_uses_independent_scales(self):
        outer = etree.Element("svg")
        nested = etree.SubElement(
            outer,
            "svg",
            x="10",
            y="20",
            width="200",
            height="150",
            viewBox="100 50 20 30",
            preserveAspectRatio="none",
        )
        rect = etree.SubElement(nested, "rect", x="102", y="53", width="4", height="6")
        assert bbox_of_element(rect, {}) == pytest.approx(BBox(30, 35, 40, 30))

    @pytest.mark.parametrize(
        ("preserve", "expected"),
        [
            (None, BBox(60, 20, 100, 150)),
            ("xMaxYMin meet", BBox(110, 20, 100, 150)),
            ("xMinYMax slice", BBox(10, -130, 200, 300)),
        ],
    )
    def test_preserve_aspect_ratio_alignment(self, preserve, expected):
        outer = etree.Element("svg")
        attrs = {
            "x": "10",
            "y": "20",
            "width": "200",
            "height": "150",
            "viewBox": "100 50 20 30",
        }
        if preserve is not None:
            attrs["preserveAspectRatio"] = preserve
        nested = etree.SubElement(outer, "svg", **attrs)
        rect = etree.SubElement(
            nested, "rect", x="100", y="50", width="20", height="30"
        )
        assert bbox_of_element(rect, {}) == pytest.approx(expected)

    def test_viewport_composes_with_panel_and_root_transforms(self):
        outer = etree.Element("svg", transform="translate(5 7)")
        panel = etree.SubElement(outer, "g", transform="translate(200 300)")
        nested = etree.SubElement(
            panel,
            "svg",
            x="10",
            y="20",
            width="20",
            height="30",
            viewBox="100 50 20 30",
            transform="scale(2)",
        )
        rect = etree.SubElement(
            nested, "rect", x="100", y="50", width="20", height="30"
        )
        assert bbox_of_element(rect, {}) == pytest.approx(BBox(225, 347, 40, 60))

    def test_percentage_dimensions_ignore_viewport_scaling(self):
        # Percentages resolve against the parent viewport, which bbox
        # computation does not track; the viewport's scaling is ignored
        # instead of guessed at, so local coordinates pass through.
        outer = etree.Element("svg")
        nested = etree.SubElement(
            outer, "svg", width="100%", height="100%", viewBox="0 0 10 10"
        )
        rect = etree.SubElement(nested, "rect", x="0", y="0", width="10", height="10")
        assert bbox_of_element(rect, {}) == pytest.approx(BBox(0, 0, 10, 10))

    def test_percentage_dimensions_keep_nested_x_y(self):
        outer = etree.Element("svg")
        nested = etree.SubElement(
            outer, "svg", x="5", y="7", width="100%", viewBox="0 0 10 10"
        )
        rect = etree.SubElement(nested, "rect", x="0", y="0", width="10", height="10")
        assert bbox_of_element(rect, {}) == pytest.approx(BBox(5, 7, 10, 10))

    def test_unit_dimensions_parse_leniently(self):
        outer = etree.Element("svg")
        nested = etree.SubElement(
            outer,
            "svg",
            x="1cm",
            y="2cm",
            width="20px",
            height="30px",
            viewBox="100 50 20 30",
        )
        rect = etree.SubElement(
            nested, "rect", x="100", y="50", width="20", height="30"
        )
        assert bbox_of_element(rect, {}) == pytest.approx(BBox(1, 2, 20, 30))

    def test_unparsable_dimension_ignores_viewport_transform(self):
        outer = etree.Element("svg")
        nested = etree.SubElement(
            outer, "svg", x="5", y="7", width="auto", viewBox="100 50 20 30"
        )
        rect = etree.SubElement(
            nested, "rect", x="100", y="50", width="20", height="30"
        )
        # Scaling is dropped but the parsable x/y translation is kept.
        assert bbox_of_element(rect, {}) == pytest.approx(BBox(105, 57, 20, 30))

    def test_malformed_nested_viewbox_does_not_raise(self):
        outer = etree.Element("svg")
        nested = etree.SubElement(
            outer, "svg", x="5", y="7", width="100", height="100", viewBox="0 0 ten 10"
        )
        rect = etree.SubElement(nested, "rect", x="0", y="0", width="20", height="30")
        assert bbox_of_element(rect, {}) == pytest.approx(BBox(5, 7, 20, 30))

    def test_merged_nonzero_viewbox_uses_nested_viewport_coordinates(self):
        from pathy_svg.document import SVGDocument
        from pathy_svg.svg_tools import merge_svgs

        source = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="100 50 20 30">'
            '<rect x="100" y="50" width="20" height="30"/></svg>'
        )
        merged = merge_svgs([source, source], spacing=0)
        rects = merged.root.xpath('.//*[local-name()="rect"]')

        assert len(rects) == 2
        assert bbox_of_element(rects[0], {}) == pytest.approx(BBox(0, 0, 20, 30))
        assert bbox_of_element(rects[1], {}) == pytest.approx(BBox(20, 0, 20, 30))


class TestTransformSupport:
    """Tests for SVG transform attribute handling in bbox computation."""

    def test_translate(self):
        elem = etree.Element("rect", x="10", y="20", width="50", height="30")
        elem.set("transform", "translate(100, 200)")
        bbox = bbox_of_element(elem, {})
        assert bbox is not None
        assert bbox.x == pytest.approx(110)
        assert bbox.y == pytest.approx(220)
        assert bbox.width == pytest.approx(50)
        assert bbox.height == pytest.approx(30)

    def test_scale(self):
        elem = etree.Element("rect", x="0", y="0", width="10", height="10")
        elem.set("transform", "scale(2)")
        bbox = bbox_of_element(elem, {})
        assert bbox is not None
        assert bbox.x == pytest.approx(0)
        assert bbox.y == pytest.approx(0)
        assert bbox.width == pytest.approx(20)
        assert bbox.height == pytest.approx(20)

    def test_rotate_90(self):
        # A rect at (0,0) with w=10, h=5 rotated 90 degrees about origin
        elem = etree.Element("rect", x="0", y="0", width="10", height="5")
        elem.set("transform", "rotate(90)")
        bbox = bbox_of_element(elem, {})
        assert bbox is not None
        # After 90° rotation: x goes from -5 to 0, y goes from 0 to 10
        assert bbox.x == pytest.approx(-5, abs=0.01)
        assert bbox.y == pytest.approx(0, abs=0.01)
        assert bbox.width == pytest.approx(5, abs=0.01)
        assert bbox.height == pytest.approx(10, abs=0.01)

    def test_combined_transforms(self):
        elem = etree.Element("rect", x="0", y="0", width="10", height="10")
        elem.set("transform", "translate(50, 50) scale(2)")
        bbox = bbox_of_element(elem, {})
        assert bbox is not None
        assert bbox.x == pytest.approx(50)
        assert bbox.y == pytest.approx(50)
        assert bbox.width == pytest.approx(20)
        assert bbox.height == pytest.approx(20)

    def test_parent_transform(self):
        group = etree.Element("g")
        group.set("transform", "translate(100, 100)")
        child = etree.SubElement(group, "rect", x="10", y="10", width="20", height="20")
        bbox = bbox_of_element(child, {})
        assert bbox is not None
        assert bbox.x == pytest.approx(110)
        assert bbox.y == pytest.approx(110)
        assert bbox.width == pytest.approx(20)
        assert bbox.height == pytest.approx(20)

    def test_nested_group_transforms(self):
        outer = etree.Element("g")
        outer.set("transform", "translate(50, 50)")
        inner = etree.SubElement(outer, "g")
        inner.set("transform", "translate(30, 30)")
        child = etree.SubElement(inner, "rect", x="0", y="0", width="10", height="10")
        bbox = bbox_of_element(child, {})
        assert bbox is not None
        assert bbox.x == pytest.approx(80)
        assert bbox.y == pytest.approx(80)
        assert bbox.width == pytest.approx(10)
        assert bbox.height == pytest.approx(10)

    def test_no_transform(self):
        elem = etree.Element("rect", x="5", y="10", width="100", height="50")
        bbox = bbox_of_element(elem, {})
        assert bbox == BBox(5, 10, 100, 50)

    def test_matrix_transform(self):
        # matrix(1,0,0,1,10,20) is equivalent to translate(10,20)
        elem = etree.Element("rect", x="0", y="0", width="10", height="10")
        elem.set("transform", "matrix(1,0,0,1,10,20)")
        bbox = bbox_of_element(elem, {})
        assert bbox is not None
        assert bbox.x == pytest.approx(10)
        assert bbox.y == pytest.approx(20)
        assert bbox.width == pytest.approx(10)
        assert bbox.height == pytest.approx(10)

    def test_skew_x(self):
        elem = etree.Element("rect", x="0", y="0", width="10", height="10")
        elem.set("transform", "skewX(45)")
        bbox = bbox_of_element(elem, {})
        assert bbox is not None
        # skewX(45) shifts x by y*tan(45) = y, so top-right corner (10,0) stays at 10,
        # bottom-right (10,10) shifts to x=20
        assert bbox.x == pytest.approx(0, abs=0.01)
        assert bbox.y == pytest.approx(0)
        assert bbox.width == pytest.approx(20, abs=0.01)
        assert bbox.height == pytest.approx(10)

    def test_rotate_about_point(self):
        # Rotate 180° about center (50, 50) of a 10x10 rect at (0,0)
        elem = etree.Element("rect", x="40", y="40", width="10", height="10")
        elem.set("transform", "rotate(180, 50, 50)")
        bbox = bbox_of_element(elem, {})
        assert bbox is not None
        # After 180° rotation about (50,50), rect at (40,40)-(50,50) becomes (50,50)-(60,60)
        assert bbox.x == pytest.approx(50, abs=0.01)
        assert bbox.y == pytest.approx(50, abs=0.01)
        assert bbox.width == pytest.approx(10)
        assert bbox.height == pytest.approx(10)

    def test_rotated_partial_arc_uses_transformed_extrema(self):
        elem = etree.Element(
            "path", d="M 50 0 A 50 50 0 0 1 0 50", transform="rotate(45)"
        )
        bbox = bbox_of_element(elem, {})
        assert bbox is not None
        diagonal = 50 / math.sqrt(2)
        assert bbox == pytest.approx(
            BBox(-diagonal, diagonal, 2 * diagonal, 50 - diagonal)
        )

    def test_partial_arc_combines_element_and_ancestor_transforms(self):
        group = etree.Element("g", transform="translate(100 200)")
        elem = etree.SubElement(
            group,
            "path",
            d="M 50 0 A 50 50 0 0 1 0 50",
            transform="rotate(45)",
        )
        bbox = bbox_of_element(elem, {})
        assert bbox is not None
        diagonal = 50 / math.sqrt(2)
        assert bbox == pytest.approx(
            BBox(100 - diagonal, 200 + diagonal, 2 * diagonal, 50 - diagonal)
        )

    def test_partial_arc_under_skew_and_nonuniform_scale(self):
        elem = etree.Element(
            "path",
            d="M 50 0 A 50 50 0 0 1 0 50",
            transform="skewX(30) scale(2 .5)",
        )
        bbox = bbox_of_element(elem, {})
        assert bbox is not None
        shear = math.tan(math.radians(30))
        x_min = 25 * shear
        x_max = 50 * math.hypot(2, 0.5 * shear)
        assert bbox == pytest.approx(BBox(x_min, 0, x_max - x_min, 25))

    def test_matrix_transformed_arc_matches_dense_sampling(self):
        matrix = (2, 0.5, 1.25, -1.5, 7, -11)
        elem = etree.Element(
            "path",
            d="M 50 0 A 50 50 0 0 1 0 50",
            transform="matrix(2 .5 1.25 -1.5 7 -11)",
        )
        bbox = bbox_of_element(elem, {})
        assert bbox is not None

        angles = np.linspace(0, math.pi / 2, 10_001)
        x = 50 * np.cos(angles)
        y = 50 * np.sin(angles)
        sampled_x = matrix[0] * x + matrix[2] * y + matrix[4]
        sampled_y = matrix[1] * x + matrix[3] * y + matrix[5]
        self._assert_tight_sample_containment(bbox, sampled_x, sampled_y)

    def test_matrix_transformed_relative_repeated_arcs_match_sampling(self):
        matrix = (1.25, -0.75, 0.4, 2, -13, 8)
        elem = etree.Element(
            "path",
            d="M 50 0 a 50 50 0 0 1 -50 50 50 50 0 0 1 -50 -50",
            transform="matrix(1.25 -.75 .4 2 -13 8)",
        )
        bbox = bbox_of_element(elem, {})
        assert bbox is not None

        angles = np.linspace(0, math.pi, 10_001)
        x = 50 * np.cos(angles)
        y = 50 * np.sin(angles)
        sampled_x = matrix[0] * x + matrix[2] * y + matrix[4]
        sampled_y = matrix[1] * x + matrix[3] * y + matrix[5]
        self._assert_tight_sample_containment(bbox, sampled_x, sampled_y)

    def test_degenerate_arc_endpoint_is_transformed(self):
        elem = etree.Element(
            "path", d="M 10 20 A 0 30 45 1 1 50 60", transform="rotate(90)"
        )
        assert bbox_of_element(elem, {}) == pytest.approx(BBox(-60, 10, 40, 40))

    def test_bezier_control_point_approximation_is_transformed_directly(self):
        elem = etree.Element("path", d="M 0 0 Q 50 100 100 0", transform="rotate(45)")
        bbox = bbox_of_element(elem, {})
        assert bbox is not None
        diagonal = 50 * math.sqrt(2)
        assert bbox == pytest.approx(
            BBox(-diagonal / 2, 0, 1.5 * diagonal, 1.5 * diagonal)
        )

    @pytest.mark.parametrize(
        ("path_d", "controls"),
        [
            (
                "M 0 0 C 10 100 20 100 30 0 S 50 0 60 0",
                [(0, 0), (10, 100), (20, 100), (30, 0), (40, -100), (50, 0), (60, 0)],
            ),
            (
                "M 0 0 Q 10 100 20 0 T 40 0",
                [(0, 0), (10, 100), (20, 0), (30, -100), (40, 0)],
            ),
        ],
    )
    def test_affine_smooth_curve_includes_reflected_control(self, path_d, controls):
        matrix = (1.2, -0.7, 0.4, 1.8, 5, -3)
        elem = etree.Element("path", d=path_d, transform="matrix(1.2 -.7 .4 1.8 5 -3)")
        bbox = bbox_of_element(elem, {})
        assert bbox is not None

        controls_array = np.array(controls, dtype=np.float64)
        transformed_x = (
            matrix[0] * controls_array[:, 0]
            + matrix[2] * controls_array[:, 1]
            + matrix[4]
        )
        transformed_y = (
            matrix[1] * controls_array[:, 0]
            + matrix[3] * controls_array[:, 1]
            + matrix[5]
        )
        assert bbox == pytest.approx(
            BBox(
                float(transformed_x.min()),
                float(transformed_y.min()),
                float(np.ptp(transformed_x)),
                float(np.ptp(transformed_y)),
            )
        )

    @pytest.mark.parametrize("degree", [2, 3])
    def test_affine_smooth_curve_bbox_contains_dense_geometry(self, degree):
        matrix = (1.2, -0.7, 0.4, 1.8, 5, -3)
        if degree == 3:
            elem = etree.Element(
                "path",
                d="M 0 0 C 10 100 20 100 30 0 S 50 0 60 0",
                transform="matrix(1.2 -.7 .4 1.8 5 -3)",
            )
            segments = [
                np.array([(0, 0), (10, 100), (20, 100), (30, 0)]),
                np.array([(30, 0), (40, -100), (50, 0), (60, 0)]),
            ]
        else:
            elem = etree.Element(
                "path",
                d="M 0 0 Q 10 100 20 0 T 40 0",
                transform="matrix(1.2 -.7 .4 1.8 5 -3)",
            )
            segments = [
                np.array([(0, 0), (10, 100), (20, 0)]),
                np.array([(20, 0), (30, -100), (40, 0)]),
            ]
        bbox = bbox_of_element(elem, {})
        assert bbox is not None

        t = np.linspace(0, 1, 10_001)[:, None]
        if degree == 3:
            samples = [
                (1 - t) ** 3 * p[0]
                + 3 * (1 - t) ** 2 * t * p[1]
                + 3 * (1 - t) * t**2 * p[2]
                + t**3 * p[3]
                for p in segments
            ]
        else:
            samples = [
                (1 - t) ** 2 * p[0] + 2 * (1 - t) * t * p[1] + t**2 * p[2]
                for p in segments
            ]
        samples_array = np.concatenate(samples)
        sampled_x = (
            matrix[0] * samples_array[:, 0]
            + matrix[2] * samples_array[:, 1]
            + matrix[4]
        )
        sampled_y = (
            matrix[1] * samples_array[:, 0]
            + matrix[3] * samples_array[:, 1]
            + matrix[5]
        )
        assert np.all(sampled_x >= bbox.x - 1e-10)
        assert np.all(sampled_x <= bbox.x + bbox.width + 1e-10)
        assert np.all(sampled_y >= bbox.y - 1e-10)
        assert np.all(sampled_y <= bbox.y + bbox.height + 1e-10)

    def test_skewed_circle_uses_ellipse_extrema(self):
        elem = etree.Element("circle", cx="0", cy="0", r="50", transform="skewX(45)")
        bbox = bbox_of_element(elem, {})
        assert bbox is not None
        radius_x = 50 * math.sqrt(2)
        assert bbox == pytest.approx(BBox(-radius_x, -50, 2 * radius_x, 100))

    @staticmethod
    def _assert_tight_sample_containment(
        bbox: BBox, sampled_x: np.ndarray, sampled_y: np.ndarray
    ) -> None:
        """Check that an analytic box tightly encloses an independent dense sample."""
        assert np.all(sampled_x >= bbox.x - 1e-10)
        assert np.all(sampled_x <= bbox.x + bbox.width + 1e-10)
        assert np.all(sampled_y >= bbox.y - 1e-10)
        assert np.all(sampled_y <= bbox.y + bbox.height + 1e-10)
        assert bbox.x == pytest.approx(float(sampled_x.min()), abs=1e-5)
        assert bbox.x + bbox.width == pytest.approx(float(sampled_x.max()), abs=1e-5)
        assert bbox.y == pytest.approx(float(sampled_y.min()), abs=1e-5)
        assert bbox.y + bbox.height == pytest.approx(float(sampled_y.max()), abs=1e-5)

    def test_parse_translate_single_arg(self):
        m = _parse_transform("translate(10)")
        expected = np.array([[1, 0, 10], [0, 1, 0], [0, 0, 1]], dtype=np.float64)
        assert np.allclose(m, expected)

    def test_parse_scale_single_arg(self):
        m = _parse_transform("scale(3)")
        expected = np.array([[3, 0, 0], [0, 3, 0], [0, 0, 1]], dtype=np.float64)
        assert np.allclose(m, expected)

    def test_multiple_transforms(self):
        elem = etree.Element("rect", x="0", y="0", width="5", height="5")
        elem.set("transform", "translate(10, 10) rotate(45) scale(2)")
        bbox = bbox_of_element(elem, {})
        assert bbox is not None
        assert bbox.width > 0
        assert bbox.height > 0

    def test_skew_y(self):
        elem = etree.Element("rect", x="0", y="0", width="10", height="10")
        elem.set("transform", "skewY(45)")
        bbox = bbox_of_element(elem, {})
        assert bbox is not None
        assert bbox.height == pytest.approx(20, abs=0.01)

    def test_scale_with_two_args(self):
        m = _parse_transform("scale(2, 3)")
        expected = np.array([[2, 0, 0], [0, 3, 0], [0, 0, 1]], dtype=np.float64)
        assert np.allclose(m, expected)


class TestBBoxOfElementExtended:
    def test_ellipse_element(self):
        elem = etree.Element("ellipse", cx="50", cy="60", rx="20", ry="10")
        bbox = bbox_of_element(elem, {})
        assert bbox == BBox(30, 50, 40, 20)

    def test_polygon_element(self):
        elem = etree.Element("polygon", points="0,0 100,0 50,50")
        bbox = bbox_of_element(elem, {})
        assert bbox is not None
        assert bbox.x == pytest.approx(0)
        assert bbox.y == pytest.approx(0)
        assert bbox.width == pytest.approx(100)
        assert bbox.height == pytest.approx(50)

    def test_polyline_element(self):
        elem = etree.Element("polyline", points="10,10 50,10 50,60")
        bbox = bbox_of_element(elem, {})
        assert bbox is not None
        assert bbox.x == pytest.approx(10)
        assert bbox.y == pytest.approx(10)
        assert bbox.width == pytest.approx(40)
        assert bbox.height == pytest.approx(50)

    def test_polygon_empty_points(self):
        elem = etree.Element("polygon", points="")
        bbox = bbox_of_element(elem, {})
        assert bbox is None

    def test_path_no_d_attr(self):
        elem = etree.Element("path")
        bbox = bbox_of_element(elem, {})
        assert bbox is None

    def test_group_with_children(self):
        g = etree.Element("g")
        etree.SubElement(g, "rect", x="10", y="10", width="20", height="20")
        etree.SubElement(g, "rect", x="50", y="50", width="10", height="10")
        bbox = bbox_of_element(g, {})
        assert bbox is not None
        assert bbox.x == pytest.approx(10)
        assert bbox.y == pytest.approx(10)
        assert bbox.width == pytest.approx(50)
        assert bbox.height == pytest.approx(50)

    def test_group_with_transform(self):
        g = etree.Element("g")
        g.set("transform", "translate(100, 100)")
        etree.SubElement(g, "rect", x="0", y="0", width="10", height="10")
        bbox = bbox_of_element(g, {})
        assert bbox is not None
        assert bbox.x == pytest.approx(100)
        assert bbox.y == pytest.approx(100)

    def test_empty_group(self):
        g = etree.Element("g")
        bbox = bbox_of_element(g, {})
        assert bbox is None

    def test_unknown_tag(self):
        elem = etree.Element("clipPath")
        bbox = bbox_of_element(elem, {})
        assert bbox is None

    def test_parent_transform_composed_with_own(self):
        outer = etree.Element("g")
        outer.set("transform", "translate(50, 50)")
        inner = etree.SubElement(outer, "g")
        inner.set("transform", "scale(2)")
        child = etree.SubElement(inner, "rect", x="0", y="0", width="10", height="10")
        bbox = bbox_of_element(child, {})
        assert bbox is not None
        assert bbox.x == pytest.approx(50)
        assert bbox.y == pytest.approx(50)
        assert bbox.width == pytest.approx(20)
        assert bbox.height == pytest.approx(20)


class TestDocumentBBoxLeniency:
    """Document-level APIs must be lenient about real-world SVG quirks."""

    PERCENT_SVG = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" '
        'viewBox="0 0 200 200">'
        '<svg width="100%" viewBox="0 0 10 10">'
        '<path id="a" d="M 1 1 L 5 5 L 1 5 Z"/></svg></svg>'
    )

    MALFORMED_D_SVG = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<path id="a" d="M 10 20 L 30 40 L 50"/>'
        '<g id="grp"><path id="b" d="M0 0 L10 10 garbage"/></g>'
        '<path id="c" d="M 0 0 L 5 5"/></svg>'
    )

    def _doc(self, svg):
        from pathy_svg.document import SVGDocument

        return SVGDocument.from_string(svg)

    def test_percentage_nested_svg_does_not_break_document_apis(self):
        doc = self._doc(self.PERCENT_SVG)
        assert isinstance(doc.bbox("a"), BBox)
        assert doc.centroid("a")
        assert doc.inspect_paths()
        assert doc.annotate({"a": "label"}, placement="centroid") is not None

    def test_truncated_path_bbox_uses_valid_prefix(self):
        doc = self._doc(self.MALFORMED_D_SVG)
        assert doc.bbox("a") == BBox(10, 20, 20, 20)

    def test_junk_suffix_path_bbox_uses_valid_prefix(self):
        doc = self._doc(self.MALFORMED_D_SVG)
        assert doc.bbox("b") == BBox(0, 0, 10, 10)

    def test_group_bbox_traversal_survives_malformed_path(self):
        doc = self._doc(self.MALFORMED_D_SVG)
        assert doc.bbox("grp") == BBox(0, 0, 10, 10)

    def test_document_apis_survive_malformed_paths(self):
        doc = self._doc(self.MALFORMED_D_SVG)
        assert len(doc.inspect_paths()) == 3
        assert doc.annotate({"c": "label"}, placement="centroid") is not None

    def test_bbox_never_leaks_validation_error(self):
        from pathy_svg.exceptions import PathNotFoundError

        doc = self._doc(self.MALFORMED_D_SVG)
        # Contract: bbox returns a BBox or raises PathNotFoundError.
        assert isinstance(doc.bbox("a"), BBox)
        with pytest.raises(PathNotFoundError):
            doc.bbox("missing")
