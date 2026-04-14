"""Tests for pathy_svg.annotations module."""

from lxml import etree

from pathy_svg.annotations import add_text_labels, add_tooltips, replace_text
from pathy_svg.document import SVGDocument


class TestAnnotate:
    def test_adds_text_labels(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.annotate({"stomach": "Stomach", "liver": "Liver"})
        svg_str = result.to_string()
        assert "Stomach" in svg_str
        assert "Liver" in svg_str

    def test_has_annotations_group(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.annotate({"stomach": "S"})
        g = result._find_by_id("pathy-annotations")
        assert g is not None

    def test_immutability(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.annotate({"stomach": "S"})
        assert doc._find_by_id("pathy-annotations") is None
        assert result._find_by_id("pathy-annotations") is not None

    def test_nonexistent_id_ignored(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.annotate({"nonexistent": "X"})
        assert result._find_by_id("pathy-annotations") is not None

    def test_with_background(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.annotate({"stomach": "S"}, background="rgba(0,0,0,0.5)")
        svg_str = result.to_string()
        assert "rgba(0,0,0,0.5)" in svg_str

    def test_placement_above(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.annotate({"stomach": "S"}, placement="above")
        assert result._find_by_id("pathy-annotations") is not None

    def test_placement_below(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.annotate({"stomach": "S"}, placement="below")
        g = result._find_by_id("pathy-annotations")
        assert g is not None

    def test_placement_bbox_corner(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.annotate({"stomach": "S"}, placement="bbox_corner")
        g = result._find_by_id("pathy-annotations")
        assert g is not None

    def test_chaining_with_heatmap(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.heatmap({"stomach": 0.5, "liver": 0.8}).annotate(
            {"stomach": "50%", "liver": "80%"}
        )
        svg_str = result.to_string()
        assert "50%" in svg_str
        assert "80%" in svg_str


class TestTooltips:
    def test_title_tooltips(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.add_tooltips({"stomach": "The stomach organ"})
        svg_str = result.to_string()
        assert "The stomach organ" in svg_str

    def test_css_tooltips(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.add_tooltips({"stomach": "Stomach info"}, method="css")
        elem = result._find_by_id("stomach")
        tooltip = result.root.xpath('//*[@data-tooltip-for="stomach"]')
        assert elem.get("data-tooltip") == "Stomach info"
        assert elem.get("tabindex") == "0"
        assert elem.get("aria-label") == "Stomach info"
        assert tooltip
        assert "Stomach info" in result.to_string()
        # Verify focus CSS rule was injected
        style = result.root.xpath("//svg:style[@id='pathy-tooltip-style']", namespaces={"svg": "http://www.w3.org/2000/svg"})
        assert style
        assert "[data-tooltip]:focus" in style[0].text

    def test_immutability(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        doc.add_tooltips({"stomach": "tip"})
        orig_stomach = doc._find_by_id("stomach")
        has_title = any(c.tag.endswith("title") for c in orig_stomach)
        assert not has_title


class TestTooltipsDirect:
    def _make_tree(self):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            '<path id="p1" d="M 0 0 L 50 50 Z" fill="#fff"/>'
            '<path id="p2" d="M 10 10 L 60 60 Z" fill="#fff"/>'
            "</svg>"
        )
        root = etree.fromstring(svg.encode())
        return etree.ElementTree(root), root.nsmap

    def test_title_tooltip_nonexistent_id_skipped(self):
        tree, nsmap = self._make_tree()
        add_tooltips(tree, nsmap, {"nonexistent": "tip"})
        titles = tree.xpath(
            "//svg:title", namespaces={"svg": "http://www.w3.org/2000/svg"}
        )
        assert len(titles) == 0

    def test_title_replaces_existing(self):
        tree, nsmap = self._make_tree()
        p1 = tree.getroot().find(".//{http://www.w3.org/2000/svg}path")
        existing_title = etree.SubElement(p1, "{http://www.w3.org/2000/svg}title")
        existing_title.text = "old"
        add_tooltips(tree, nsmap, {"p1": "new"})
        titles = p1.findall("{http://www.w3.org/2000/svg}title")
        assert len(titles) == 1
        assert titles[0].text == "new"

    def test_css_tooltip_nonexistent_id_skipped(self):
        tree, nsmap = self._make_tree()
        add_tooltips(tree, nsmap, {"nonexistent": "tip"}, method="css")
        data_tooltips = tree.xpath("//*[@data-tooltip-for]")
        assert len(data_tooltips) == 0

    def test_css_tooltip_removes_existing(self):
        tree, nsmap = self._make_tree()
        add_tooltips(tree, nsmap, {"p1": "first"}, method="css")
        add_tooltips(tree, nsmap, {"p1": "second"}, method="css")
        tooltips = tree.xpath('//*[@data-tooltip-for="p1"]')
        assert len(tooltips) == 1


class TestReplaceText:
    def test_replace_legend_text(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.heatmap({"stomach": 0.0, "liver": 1.0}).legend(num_ticks=3)
        svg_before = result.to_string()
        assert "0.00" in svg_before, "Precondition: legend should contain '0.00'"
        replaced = result.replace_text({"0.00": "Low", "1.00": "High"})
        svg_after = replaced.to_string()
        assert "Low" in svg_after
        assert "High" in svg_after

    def test_replace_text_with_color(self):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            '<text id="t1">Hello</text>'
            '<text id="t2">World</text>'
            "</svg>"
        )
        tree = etree.ElementTree(etree.fromstring(svg.encode()))
        replace_text(tree, {"Hello": "Foo"}, text_color="#ff0000")
        t1 = tree.getroot().find(".//{http://www.w3.org/2000/svg}text")
        assert t1.text == "Foo"
        assert "#ff0000" in t1.get("style", "")
