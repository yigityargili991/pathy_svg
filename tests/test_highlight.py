"""Tests for pathy_svg.highlight module."""

import re

from lxml import etree

from pathy_svg.document import SVGDocument
from pathy_svg.highlight import apply_highlight


def _make_tree():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<path id="a" d="M 0 0 L 50 50 Z" fill="#ff0000"/>'
        '<path id="b" d="M 10 10 L 60 60 Z" fill="#00ff00"/>'
        '<path id="c" d="M 20 20 L 70 70 Z" fill="#0000ff"/>'
        "</svg>"
    )
    return etree.ElementTree(etree.fromstring(svg.encode()))


def _make_grouped_tree():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<g id="grp"><path id="c1" d="M 0 0 L 50 50 Z" fill="#ff0000"/>'
        '<path id="c2" d="M 10 10 L 60 60 Z" fill="#00ff00"/></g>'
        '<path id="d" d="M 20 20 L 70 70 Z" fill="#0000ff"/>'
        "</svg>"
    )
    return etree.ElementTree(etree.fromstring(svg.encode()))


def _extract_fill(elem):
    style = elem.get("style", "")
    m = re.search(r"fill:(#[0-9a-fA-F]{6})", style)
    if m:
        return m.group(1)
    return elem.get("fill")


class TestApplyHighlight:
    def test_highlighted_element_unchanged(self):
        tree = _make_tree()
        apply_highlight(tree, {"a"})

        ns = "{http://www.w3.org/2000/svg}"
        a = tree.getroot().find(f".//{ns}path[@id='a']")
        assert a.get("fill") == "#ff0000"
        assert a.get("fill-opacity") is None

    def test_dimmed_element_has_low_opacity(self):
        tree = _make_tree()
        apply_highlight(tree, {"a"}, dim_opacity=0.2)

        ns = "{http://www.w3.org/2000/svg}"
        b = tree.getroot().find(f".//{ns}path[@id='b']")
        assert b.get("fill-opacity") == "0.2"

    def test_dimmed_element_desaturated(self):
        tree = _make_tree()
        apply_highlight(tree, {"a"}, desaturate=True)

        ns = "{http://www.w3.org/2000/svg}"
        b = tree.getroot().find(f".//{ns}path[@id='b']")
        fill = _extract_fill(b)
        # Green (#00ff00) desaturated: R=G=B (greyscale)
        r, g, b_val = int(fill[1:3], 16), int(fill[3:5], 16), int(fill[5:7], 16)
        assert abs(r - g) <= 1
        assert abs(g - b_val) <= 1

    def test_desaturate_false_keeps_original_color(self):
        tree = _make_tree()
        apply_highlight(tree, {"a"}, desaturate=False)

        ns = "{http://www.w3.org/2000/svg}"
        b = tree.getroot().find(f".//{ns}path[@id='b']")
        fill = _extract_fill(b)
        assert fill == "#00ff00"

    def test_multiple_highlighted_ids(self):
        tree = _make_tree()
        apply_highlight(tree, {"a", "b"})

        ns = "{http://www.w3.org/2000/svg}"
        a = tree.getroot().find(f".//{ns}path[@id='a']")
        b = tree.getroot().find(f".//{ns}path[@id='b']")
        c = tree.getroot().find(f".//{ns}path[@id='c']")
        assert a.get("fill-opacity") is None
        assert b.get("fill-opacity") is None
        assert c.get("fill-opacity") == "0.2"

    def test_group_highlight(self):
        tree = _make_grouped_tree()
        apply_highlight(tree, {"grp"})

        ns = "{http://www.w3.org/2000/svg}"
        c1 = tree.getroot().find(f".//{ns}path[@id='c1']")
        c2 = tree.getroot().find(f".//{ns}path[@id='c2']")
        d = tree.getroot().find(f".//{ns}path[@id='d']")
        assert c1.get("fill-opacity") is None
        assert c2.get("fill-opacity") is None
        assert d.get("fill-opacity") == "0.2"

    def test_no_ids_highlighted_dims_all(self):
        tree = _make_tree()
        apply_highlight(tree, set())

        ns = "{http://www.w3.org/2000/svg}"
        for eid in ("a", "b", "c"):
            elem = tree.getroot().find(f".//{ns}path[@id='{eid}']")
            assert elem.get("fill-opacity") == "0.2"

    def test_resource_shapes_are_not_dimmed(self):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs>'
            '<pattern id="hatch" width="4" height="4">'
            '<rect id="tile" width="4" height="4" fill="#00ff00"/></pattern>'
            '<mask id="m"><rect id="cutout" width="100" height="100" fill="#ffffff"/>'
            "</mask></defs>"
            '<path id="a" d="M 0 0 L 50 50 Z" fill="url(#hatch)" mask="url(#m)"/>'
            '<path id="b" d="M 10 10 L 60 60 Z" fill="#0000ff"/>'
            "</svg>"
        )
        tree = etree.ElementTree(etree.fromstring(svg.encode()))

        apply_highlight(tree, {"a"})

        ns = "{http://www.w3.org/2000/svg}"
        root = tree.getroot()
        for rect_id, fill in (("tile", "#00ff00"), ("cutout", "#ffffff")):
            rect = root.find(f".//{ns}rect[@id='{rect_id}']")
            assert rect.get("fill") == fill
            assert rect.get("fill-opacity") is None
        assert root.find(f".//{ns}path[@id='b']").get("fill-opacity") == "0.2"


class TestHighlightMixin:
    def test_returns_new_document(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.highlight(["stomach"])

        assert result is not doc
        assert isinstance(result, SVGDocument)

    def test_original_unchanged(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        doc.highlight(["stomach"])

        assert doc._find_by_id("liver").get("fill-opacity") is None

    def test_generated_legend_annotations_and_tooltips_are_not_dimmed(
        self, simple_svg_path
    ):
        doc = SVGDocument.from_file(simple_svg_path)
        decorated = (
            doc.heatmap({"stomach": 1.0, "liver": 5.0}, breaks=[0, 3, 6])
            .legend()
            .annotate({"liver": "L"}, background="white")
            .add_tooltips({"heart": "Heart"}, method="css")
        )
        overlay_rects = (
            "//*[@data-pathy-legend or @id='pathy-annotations' or @data-tooltip-for]"
            "//*[local-name()='rect']"
        )

        result = decorated.highlight(["liver"])

        def paint(document):
            return [
                (rect.get("fill"), rect.get("fill-opacity"), rect.get("style"))
                for rect in document.xpath(overlay_rects)
            ]

        assert len(paint(decorated)) >= 4  # 2 swatches, label and tooltip boxes
        assert paint(result) == paint(decorated)
        assert result._find_by_id("stomach").get("fill-opacity") == "0.2"
