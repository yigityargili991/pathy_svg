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
