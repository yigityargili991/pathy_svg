"""Tests for key_attr parameter — matching elements by non-ID attributes."""

import re

import pytest
from lxml import etree

from pathy_svg.coloring import aggregate_by_group
from pathy_svg.document import SVGDocument


DATA_ATTR_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">'
    '<path id="p1" data-region="north" d="M 50 50 L 190 50 L 190 190 Z" fill="#fff"/>'
    '<path id="p2" data-region="south" d="M 50 210 L 190 210 L 190 350 Z" fill="#fff"/>'
    '<path id="p3" data-region="east" d="M 210 50 L 350 50 L 350 190 Z" fill="#fff"/>'
    "</svg>"
)

GROUPED_DATA_ATTR_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">'
    '<g id="grp" data-code="zone-a">'
    '<path id="a1" data-code="c1" d="M 50 50 L 190 50 L 190 190 Z" fill="#fff"/>'
    '<path id="a2" data-code="c2" d="M 210 50 L 350 50 L 350 190 Z" fill="#fff"/>'
    "</g>"
    '<g id="grp2" data-code="zone-b">'
    '<path id="b1" data-code="c3" d="M 50 210 L 190 210 L 190 350 Z" fill="#fff"/>'
    "</g>"
    "</svg>"
)


def _extract_fill(doc, eid):
    style = doc._find_by_id(eid).get("style", "")
    m = re.search(r"fill:(#[0-9a-fA-F]{6})", style)
    return m.group(1) if m else None


GROUP_BY_DATA_ATTR_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">'
    '<g data-region="north">'
    '<path id="na" data-region="north_a" d="M 50 50 L 190 50 L 190 190 Z" fill="#fff"/>'
    '<path id="nb" data-region="north_b" d="M 210 50 L 350 50 L 350 190 Z" fill="#fff"/>'
    "</g>"
    "</svg>"
)

NO_ID_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">'
    '<path data-region="north" d="M 50 50 L 190 50 L 190 190 Z" fill="#fff"/>'
    '<path data-region="south" d="M 50 210 L 190 210 L 190 350 Z" fill="#fff"/>'
    "</svg>"
)

SPACE_ATTR_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">'
    '<path id="s1" data-name="North America" d="M 50 50 L 190 50 L 190 190 Z" fill="#fff"/>'
    '<path id="s2" data-name="South America" d="M 50 210 L 190 210 L 190 350 Z" fill="#fff"/>'
    "</svg>"
)

DUPLICATE_ATTR_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">'
    '<path id="d1" data-region="north" d="M 50 50 L 190 50 L 190 190 Z" fill="#fff"/>'
    '<path id="d2" data-region="north" d="M 210 50 L 350 50 L 350 190 Z" fill="#fff"/>'
    '<path id="d3" data-region="south" d="M 50 210 L 190 210 L 190 350 Z" fill="#fff"/>'
    "</svg>"
)


class TestHeatmapKeyAttr:
    def test_match_by_data_attribute(self):
        doc = SVGDocument.from_string(DATA_ATTR_SVG)
        result = doc.heatmap(
            {"north": 0.0, "south": 1.0},
            key_attr="data-region",
        )
        p1_fill = _extract_fill(result, "p1")
        p2_fill = _extract_fill(result, "p2")
        assert p1_fill is not None
        assert p2_fill is not None
        assert p1_fill != p2_fill

    def test_default_key_attr_is_id(self):
        doc = SVGDocument.from_string(DATA_ATTR_SVG)
        result = doc.heatmap({"p1": 0.5})
        assert _extract_fill(result, "p1") is not None

    def test_unmatched_keys_ignored(self):
        doc = SVGDocument.from_string(DATA_ATTR_SVG)
        result = doc.heatmap(
            {"north": 0.5, "nonexistent": 1.0},
            key_attr="data-region",
        )
        assert _extract_fill(result, "p1") is not None

    def test_color_missing_runs_when_no_keys_match(self):
        """color_missing must still paint na_color even if no data keys matched."""
        doc = SVGDocument.from_string(DATA_ATTR_SVG)
        result = doc.heatmap(
            {"nonexistent": 1.0},
            key_attr="data-region",
            na_color="#aabbcc",
            color_missing=True,
        )
        p1_fill = _extract_fill(result, "p1")
        assert p1_fill == "#aabbcc"

    def test_group_children_not_overwritten_by_na_color(self):
        """Coloring a <g> via data-attr must not na_color its children."""
        doc = SVGDocument.from_string(GROUP_BY_DATA_ATTR_SVG)
        result = doc.heatmap(
            {"north": 1.0},
            key_attr="data-region",
            na_color="#aabbcc",
            color_missing=True,
        )
        na_fill = _extract_fill(result, "na")
        nb_fill = _extract_fill(result, "nb")
        assert na_fill != "#aabbcc"
        assert nb_fill != "#aabbcc"


class TestRecolorKeyAttr:
    def test_recolor_by_data_attribute(self):
        doc = SVGDocument.from_string(DATA_ATTR_SVG)
        result = doc.recolor(
            {"north": "#ff0000", "south": "#0000ff"},
            key_attr="data-region",
        )
        assert result._find_by_id("p1").get("fill") == "#ff0000"
        assert result._find_by_id("p2").get("fill") == "#0000ff"


class TestRecolorByCategoryKeyAttr:
    def test_categorical_by_data_attribute(self):
        doc = SVGDocument.from_string(DATA_ATTR_SVG)
        result = doc.recolor_by_category(
            {"north": "warm", "south": "cold"},
            palette={"warm": "#ff0000", "cold": "#0000ff"},
            key_attr="data-region",
        )
        assert result._find_by_id("p1").get("fill") == "#ff0000"
        assert result._find_by_id("p2").get("fill") == "#0000ff"


class TestStrokeMapKeyAttr:
    def test_stroke_by_data_attribute(self):
        doc = SVGDocument.from_string(DATA_ATTR_SVG)
        result = doc.stroke_map(
            {"north": 1.0, "south": 5.0},
            key_attr="data-region",
        )
        p1 = result._find_by_id("p1")
        p2 = result._find_by_id("p2")
        assert p1.get("stroke-width") is not None
        assert p2.get("stroke-width") is not None


class TestHighlightKeyAttr:
    def test_highlight_by_data_attribute(self):
        doc = SVGDocument.from_string(DATA_ATTR_SVG)
        result = doc.highlight(["north"], key_attr="data-region")
        p2 = result._find_by_id("p2")
        assert "fill-opacity" in (p2.get("style") or "")


class TestAnnotateKeyAttr:
    def test_annotate_by_data_attribute(self):
        doc = SVGDocument.from_string(DATA_ATTR_SVG)
        result = doc.annotate({"north": "N"}, key_attr="data-region")
        svg_str = result.to_string()
        assert ">N<" in svg_str

    def test_tooltip_by_data_attribute(self):
        doc = SVGDocument.from_string(DATA_ATTR_SVG)
        result = doc.add_tooltips(
            {"north": "Northern region"},
            key_attr="data-region",
        )
        svg_str = result.to_string()
        assert "Northern region" in svg_str

    def test_css_tooltip_selector_works_without_id(self):
        """CSS tooltips must use [data-tooltip]:hover, not [id]:hover."""
        doc = SVGDocument.from_string(NO_ID_SVG)
        result = doc.add_tooltips(
            {"north": "Northern region"},
            method="css",
            key_attr="data-region",
        )
        svg_str = result.to_string()
        assert "[data-tooltip]:hover" in svg_str
        assert "[id]:hover" not in svg_str


class TestHeatmapGroupsKeyAttr:
    def test_aggregate_children_by_data_attribute(self):
        """Groups are identified by id, children matched by key_attr."""
        tree = etree.ElementTree(etree.fromstring(GROUPED_DATA_ATTR_SVG.encode()))
        data = {"c1": 10.0, "c2": 20.0, "c3": 30.0}
        result = aggregate_by_group(tree, data, agg="mean", key_attr="data-code")
        assert result["grp"] == pytest.approx(15.0)
        assert result["grp2"] == pytest.approx(30.0)

    def test_heatmap_groups_by_data_attribute(self):
        doc = SVGDocument.from_string(GROUPED_DATA_ATTR_SVG)
        result = doc.heatmap_groups(
            {"c1": 10.0, "c2": 20.0, "c3": 30.0},
            agg="mean",
            key_attr="data-code",
        )
        assert result._last_scale is not None


class TestDuplicateKeyAttr:
    """Duplicate attribute values must all be colored, not just the first."""

    def test_heatmap_colors_all_duplicates(self):
        doc = SVGDocument.from_string(DUPLICATE_ATTR_SVG)
        result = doc.heatmap(
            {"north": 1.0},
            key_attr="data-region",
        )
        d1_fill = _extract_fill(result, "d1")
        d2_fill = _extract_fill(result, "d2")
        assert d1_fill is not None
        assert d2_fill is not None
        assert d1_fill == d2_fill

    def test_recolor_colors_all_duplicates(self):
        doc = SVGDocument.from_string(DUPLICATE_ATTR_SVG)
        result = doc.recolor(
            {"north": "#ff0000"},
            key_attr="data-region",
        )
        assert result._find_by_id("d1").get("fill") == "#ff0000"
        assert result._find_by_id("d2").get("fill") == "#ff0000"

    def test_stroke_map_all_duplicates(self):
        doc = SVGDocument.from_string(DUPLICATE_ATTR_SVG)
        result = doc.stroke_map(
            {"north": 5.0},
            key_attr="data-region",
        )
        d1 = result._find_by_id("d1")
        d2 = result._find_by_id("d2")
        assert d1.get("stroke-width") is not None
        assert d2.get("stroke-width") is not None

    def test_highlight_all_duplicates(self):
        doc = SVGDocument.from_string(DUPLICATE_ATTR_SVG)
        result = doc.highlight(["north"], key_attr="data-region")
        d3 = result._find_by_id("d3")
        assert "fill-opacity" in (d3.get("style") or "")
        d1 = result._find_by_id("d1")
        assert "fill-opacity:0.2" not in (d1.get("style") or "")

    def test_categorical_all_duplicates(self):
        doc = SVGDocument.from_string(DUPLICATE_ATTR_SVG)
        result = doc.recolor_by_category(
            {"north": "warm"},
            palette={"warm": "#ff0000"},
            key_attr="data-region",
        )
        assert result._find_by_id("d1").get("fill") == "#ff0000"
        assert result._find_by_id("d2").get("fill") == "#ff0000"


class TestUnsafeAttrValues:
    """Attribute values with spaces/punctuation must produce valid SVG IDs."""

    def test_gradient_fill_with_spaces(self):
        from pathy_svg.gradient import GradientSpec

        doc = SVGDocument.from_string(SPACE_ATTR_SVG)
        result = doc.gradient_fill(
            {"North America": GradientSpec(start="#ff0000", end="#0000ff")},
            key_attr="data-name",
        )
        svg_str = result.to_string()
        assert "url(#pathy-grad-" in svg_str
        assert "North America" not in svg_str.split("url(#")[1].split(")")[0]

    def test_pattern_fill_with_spaces(self):
        doc = SVGDocument.from_string(SPACE_ATTR_SVG)
        result = doc.pattern_fill(
            {"North America": "dots"},
            key_attr="data-name",
        )
        svg_str = result.to_string()
        assert "url(#pathy-pat-" in svg_str

    def test_gradient_collision_safe(self):
        """Keys that sanitise to the same string must get distinct defs."""
        from pathy_svg.gradient import GradientSpec

        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">'
            '<path id="a" data-name="a/b" d="M 0 0 L 50 50 Z" fill="#fff"/>'
            '<path id="b" data-name="a b" d="M 60 0 L 110 50 Z" fill="#fff"/>'
            "</svg>"
        )
        doc = SVGDocument.from_string(svg)
        result = doc.gradient_fill(
            {
                "a/b": GradientSpec(start="#ff0000", end="#0000ff"),
                "a b": GradientSpec(start="#00ff00", end="#ffff00"),
            },
            key_attr="data-name",
        )
        svg_str = result.to_string()
        a_elem = result._find_by_id("a")
        b_elem = result._find_by_id("b")
        a_ref = a_elem.get("fill")
        b_ref = b_elem.get("fill")
        assert a_ref.startswith("url(#pathy-grad-")
        assert b_ref.startswith("url(#pathy-grad-")
        assert a_ref != b_ref

    def test_css_tooltip_with_quote_in_attr(self):
        """CSS tooltips must not break on attribute values with quotes."""
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">'
            """<path id="q1" data-name='say "hi"' d="M 0 0 L 50 50 Z" fill="#fff"/>"""
            "</svg>"
        )
        doc = SVGDocument.from_string(svg)
        result = doc.add_tooltips(
            {'say "hi"': "greeting"},
            method="css",
            key_attr="data-name",
        )
        svg_str = result.to_string()
        assert "greeting" in svg_str
