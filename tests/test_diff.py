"""Tests for pathy_svg.diff module."""

import pytest

from pathy_svg.diff import compose_side_by_side, compute_diff
from pathy_svg.document import SVGDocument


class TestComputeDiff:
    def test_delta(self):
        b = {"a": 10, "b": 20}
        t = {"a": 15, "b": 10}
        result = compute_diff(b, t, mode="delta")
        assert result["a"] == 5
        assert result["b"] == -10

    def test_ratio(self):
        b = {"a": 10, "b": 20}
        t = {"a": 30, "b": 10}
        result = compute_diff(b, t, mode="ratio")
        assert result["a"] == pytest.approx(3.0)
        assert result["b"] == pytest.approx(0.5)

    def test_log2ratio(self):
        b = {"a": 1, "b": 4}
        t = {"a": 4, "b": 1}
        result = compute_diff(b, t, mode="log2ratio")
        assert result["a"] == pytest.approx(2.0)
        assert result["b"] == pytest.approx(-2.0)

    def test_percent_change(self):
        b = {"a": 100}
        t = {"a": 150}
        result = compute_diff(b, t, mode="percent_change")
        assert result["a"] == pytest.approx(50.0)

    def test_only_common_keys(self):
        b = {"a": 10, "c": 30}
        t = {"a": 20, "b": 40}
        result = compute_diff(b, t, mode="delta")
        assert "a" in result
        assert "b" not in result
        assert "c" not in result

    def test_invalid_mode(self):
        with pytest.raises(ValueError):
            compute_diff({"a": 1}, {"a": 2}, mode="invalid")


class TestDocDiff:
    def test_diff_returns_doc(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        b = {"stomach": 0.5, "liver": 0.3}
        t = {"stomach": 0.9, "liver": 0.1}
        result = doc.diff(b, t)
        assert result is not doc
        style = result._find_by_id("stomach").get("style", "")
        assert "fill:" in style


class TestComputeDiffEdgeCases:
    def test_ratio_division_by_zero(self):
        result = compute_diff({"a": 0}, {"a": 10}, mode="ratio")
        assert result["a"] == float("inf")

    def test_log2ratio_zero_baseline(self):
        import math

        result = compute_diff({"a": 0}, {"a": 10}, mode="log2ratio")
        assert math.isnan(result["a"])

    def test_percent_change_zero_baseline(self):
        result = compute_diff({"a": 0}, {"a": 10}, mode="percent_change")
        assert result["a"] == float("inf")

    def test_empty_dicts(self):
        result = compute_diff({}, {}, mode="delta")
        assert result == {}


class TestDocCompare:
    SVG_WITH_REFERENCES = """<svg xmlns="http://www.w3.org/2000/svg"
        xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 100 100">
      <defs>
        <linearGradient id="paint"><stop offset="1" stop-color="red"/></linearGradient>
        <clipPath id="clip"><use href="#shape"/></clipPath>
        <style>#shape, [id="shape"] { clip-path:url(#clip); fill:url(#paint) }</style>
      </defs>
      <path id="shape" d="M0 0h10v10z" clip-path="url(#clip)"/>
      <use id="instance" href="#shape" xlink:href="#shape"/>
    </svg>"""

    def test_compare_returns_doc(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.compare(
            {
                "Baseline": {"stomach": 0.3, "liver": 0.5},
                "Treatment": {"stomach": 0.9, "liver": 0.1},
            }
        )
        svg_str = result.to_string()
        assert "Baseline" in svg_str
        assert "Treatment" in svg_str

    def test_compare_vertical_layout(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.compare(
            {
                "A": {"stomach": 0.3},
                "B": {"stomach": 0.9},
            },
            layout="vertical",
        )
        vb = result.viewbox
        assert vb is not None
        assert vb.height > doc.viewbox.height

    def test_compose_rebases_non_zero_viewbox(self):
        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="100 100 50 50">'
            '<rect id="r" x="100" y="100" width="50" height="50"/>'
            "</svg>"
        )

        tree = compose_side_by_side([doc], titles=None)
        group = tree.getroot().find("{http://www.w3.org/2000/svg}g")

        assert group is not None
        nested = group.find("{http://www.w3.org/2000/svg}svg")
        assert group.get("transform") == "translate(0.0,0)"
        assert nested.get("viewBox") == "100 100 50 50"
        assert nested.get("width") == "50.0"
        assert nested.get("height") == "50.0"

    def test_compose_rejects_invalid_layout(self):
        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"/>'
        )

        with pytest.raises(ValueError, match="layout must be"):
            compose_side_by_side([doc], layout="diagonal")

    def test_compare_namespaces_duplicate_source_ids_and_references(self):
        from lxml import etree

        doc = SVGDocument.from_string(self.SVG_WITH_REFERENCES)
        before = doc.to_string()
        result = doc.compare({"Baseline": {"shape": 0.2}, "Treatment": {"shape": 0.8}})
        root = result.root

        ids = [elem.get("id") for elem in root.xpath(".//*[@id]")]
        assert len(ids) == len(set(ids))
        ns = {"svg": "http://www.w3.org/2000/svg"}
        xlink_href = "{http://www.w3.org/1999/xlink}href"
        for index in range(2):
            prefix = f"pathy-panel-{index}"
            panel = root.xpath(f".//svg:g[@id='{prefix}']", namespaces=ns)[0]
            path = panel.xpath(f".//svg:path[@id='{prefix}--shape']", namespaces=ns)[0]
            use = panel.xpath(f".//svg:use[@id='{prefix}--instance']", namespaces=ns)[0]
            css = panel.xpath(".//svg:style", namespaces=ns)[0].text

            assert path.get("clip-path") == f"url(#{prefix}--clip)"
            assert use.get("href") == f"#{prefix}--shape"
            assert use.get(xlink_href) == f"#{prefix}--shape"
            assert f"#{prefix}--shape" in css
            assert f'[id="{prefix}--shape"]' in css
            assert f"url(#{prefix}--clip)" in css
            assert f"url(#{prefix}--paint)" in css

        assert doc.to_string() == before
        reparsed = etree.fromstring(result.to_string().encode())
        assert reparsed.tag == "{http://www.w3.org/2000/svg}svg"

    def test_compose_side_by_side_namespaces_each_panel(self):
        doc = SVGDocument.from_string(self.SVG_WITH_REFERENCES)
        tree = compose_side_by_side([doc, doc], titles=None)
        ids = [elem.get("id") for elem in tree.getroot().xpath(".//*[@id]")]

        assert len(ids) == len(set(ids))
        assert "pathy-panel-0--shape" in ids
        assert "pathy-panel-1--shape" in ids

    def test_compare_titles_are_outside_panel_scoped_text_css(self):
        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
            "<style>.region, text {fill:red}</style>"
            '<path id="region"/><text>source text</text>'
            "</svg>"
        )
        result = doc.compare({"First": {"region": 0.2}, "Second": {"region": 0.8}})
        root = result.root
        ns = {"svg": "http://www.w3.org/2000/svg"}
        title_texts = root.xpath("./svg:text", namespaces=ns)
        styles = root.xpath(".//svg:style", namespaces=ns)

        assert [title.text for title in title_texts] == ["First", "Second"]
        assert "#pathy-panel-0 text" in styles[0].text
        assert "#pathy-panel-1 text" in styles[1].text
        assert all(style.getparent().tag.endswith("svg") for style in styles)
