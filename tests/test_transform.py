"""Tests for pathy_svg.transform module."""

import pytest

from pathy_svg.transform import (
    BBox,
    ViewBox,
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

    def test_arc_absolute(self):
        d = "M 0 0 A 50 50 0 0 1 100 0"
        bbox = bbox_from_path_d(d)
        assert bbox.x == pytest.approx(0)
        assert bbox.y == pytest.approx(0)
        assert bbox.width == pytest.approx(100)

    def test_arc_relative(self):
        d = "M 0 0 a 50 50 0 0 1 100 0"
        bbox = bbox_from_path_d(d)
        assert bbox.x == pytest.approx(0)
        assert bbox.y == pytest.approx(0)
        assert bbox.width == pytest.approx(100)

    def test_relative_moveto(self):
        d = "M 10 10 m 20 20 L 50 50"
        bbox = bbox_from_path_d(d)
        assert bbox.x == pytest.approx(10)
        assert bbox.y == pytest.approx(10)
        assert bbox.width == pytest.approx(40)
        assert bbox.height == pytest.approx(40)


class TestBBoxOfElement:
    def test_rect_element(self):
        from lxml import etree

        elem = etree.Element("rect", x="10", y="20", width="100", height="50")
        bbox = bbox_of_element(elem, {})
        assert bbox == BBox(10, 20, 100, 50)

    def test_circle_element(self):
        from lxml import etree

        elem = etree.Element("circle", cx="50", cy="50", r="25")
        bbox = bbox_of_element(elem, {})
        assert bbox == BBox(25, 25, 50, 50)

    def test_path_element(self):
        from lxml import etree

        elem = etree.Element("path", d="M 0 0 L 100 0 L 100 50 Z")
        bbox = bbox_of_element(elem, {})
        assert bbox is not None
        assert bbox.width == pytest.approx(100)
        assert bbox.height == pytest.approx(50)


class TestTransformSupport:
    """Tests for SVG transform attribute handling in bbox computation."""

    def test_translate(self):
        from lxml import etree

        elem = etree.Element("rect", x="10", y="20", width="50", height="30")
        elem.set("transform", "translate(100, 200)")
        bbox = bbox_of_element(elem, {})
        assert bbox is not None
        assert bbox.x == pytest.approx(110)
        assert bbox.y == pytest.approx(220)
        assert bbox.width == pytest.approx(50)
        assert bbox.height == pytest.approx(30)

    def test_scale(self):
        from lxml import etree

        elem = etree.Element("rect", x="0", y="0", width="10", height="10")
        elem.set("transform", "scale(2)")
        bbox = bbox_of_element(elem, {})
        assert bbox is not None
        assert bbox.x == pytest.approx(0)
        assert bbox.y == pytest.approx(0)
        assert bbox.width == pytest.approx(20)
        assert bbox.height == pytest.approx(20)

    def test_rotate_90(self):
        from lxml import etree

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
        from lxml import etree

        elem = etree.Element("rect", x="0", y="0", width="10", height="10")
        elem.set("transform", "translate(50, 50) scale(2)")
        bbox = bbox_of_element(elem, {})
        assert bbox is not None
        assert bbox.x == pytest.approx(50)
        assert bbox.y == pytest.approx(50)
        assert bbox.width == pytest.approx(20)
        assert bbox.height == pytest.approx(20)

    def test_parent_transform(self):
        from lxml import etree

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
        from lxml import etree

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
        from lxml import etree

        elem = etree.Element("rect", x="5", y="10", width="100", height="50")
        bbox = bbox_of_element(elem, {})
        assert bbox == BBox(5, 10, 100, 50)

    def test_matrix_transform(self):
        from lxml import etree

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
        from lxml import etree

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
        from lxml import etree

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

    def test_parse_translate_single_arg(self):
        from pathy_svg.transform import _parse_transform
        import numpy as np

        m = _parse_transform("translate(10)")
        expected = np.array([[1, 0, 10], [0, 1, 0], [0, 0, 1]], dtype=np.float64)
        assert np.allclose(m, expected)

    def test_parse_scale_single_arg(self):
        from pathy_svg.transform import _parse_transform
        import numpy as np

        m = _parse_transform("scale(3)")
        expected = np.array([[3, 0, 0], [0, 3, 0], [0, 0, 1]], dtype=np.float64)
        assert np.allclose(m, expected)

    def test_multiple_transforms(self):
        from lxml import etree

        elem = etree.Element("rect", x="0", y="0", width="5", height="5")
        elem.set("transform", "translate(10, 10) rotate(45) scale(2)")
        bbox = bbox_of_element(elem, {})
        assert bbox is not None
        # Should have some non-trivial bounding box
        assert bbox.width > 0
        assert bbox.height > 0
