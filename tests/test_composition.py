"""Regression tests for pathy_svg._composition and composition in svg_tools."""

import pytest

from pathy_svg.document import SVGDocument
from pathy_svg.exceptions import CompositionError
from pathy_svg.svg_tools import compose_svgs, merge_svgs

SVG_NS = "http://www.w3.org/2000/svg"
NS = {"svg": SVG_NS}


def _doc(body: str, attrs: str = 'viewBox="0 0 100 100"') -> SVGDocument:
    return SVGDocument.from_string(f'<svg xmlns="{SVG_NS}" {attrs}>{body}</svg>')


def _nested_svg(merged: SVGDocument, index: int = 0):
    panel = merged.root.xpath(f"./svg:g[@data-panel-index='{index}']", namespaces=NS)[0]
    return panel.xpath("./svg:svg", namespaces=NS)[0]


class TestPanelViewportDimensions:
    def test_percentage_dimensions_do_not_fabricate_viewport(self):
        doc = _doc(
            '<rect id="r" x="0" y="0" width="800" height="600" fill="red"/>',
            attrs='width="100%" height="100%"',
        )
        merged = merge_svgs([doc])
        nested = _nested_svg(merged)
        assert nested.get("width") == "100%"
        assert nested.get("height") == "100%"
        out = merged.to_string()
        assert 'width="100.0"' not in out
        assert '<rect id="r"' in out

    def test_physical_unit_dimensions_do_not_fabricate_viewport(self):
        doc = _doc(
            '<rect id="r" width="800" height="600" fill="red"/>',
            attrs='width="5cm" height="5cm"',
        )
        nested = _nested_svg(merge_svgs([doc]))
        assert nested.get("width") == "5cm"
        assert nested.get("height") == "5cm"

    def test_pixel_dimensions_still_size_panel(self):
        doc = _doc(
            '<rect id="r" width="10" height="10"/>',
            attrs='width="800px" height="600"',
        )
        merged = merge_svgs([doc])
        nested = _nested_svg(merged)
        assert nested.get("width") == "800.0"
        assert nested.get("height") == "600.0"
        assert merged.root.get("viewBox") == "0 0 800.0 600.0"

    def test_viewbox_dimensions_still_size_panel(self):
        doc = _doc('<rect id="r" width="10" height="10"/>')
        nested = _nested_svg(merge_svgs([doc]))
        assert nested.get("width") == "100.0"
        assert nested.get("height") == "100.0"

    def test_uppercase_px_dimensions_size_panel(self):
        doc = _doc(
            '<rect id="r" width="10" height="10"/>',
            attrs='width="800PX" height="600Px"',
        )
        nested = _nested_svg(merge_svgs([doc]))
        assert nested.get("width") == "800.0"
        assert nested.get("height") == "600.0"


class TestReferenceAttributeRewriting:
    def test_external_href_with_url_text_not_rewritten(self):
        doc = _doc(
            '<defs><linearGradient id="a"/></defs>'
            '<a href="https://example.com/?q=url(#a)">'
            '<rect width="5" height="5"/></a>'
        )
        out = merge_svgs([doc, doc]).to_string()
        assert "https://example.com/?q=url(#a)" in out

    def test_external_href_with_unresolved_fragment_not_rewritten(self):
        doc = _doc('<a href="https://example.com/?q=url(#nope)"><rect/></a>')
        out = merge_svgs([doc]).to_string()
        assert "https://example.com/?q=url(#nope)" in out
        assert "unresolved" not in out

    def test_data_attribute_not_rewritten(self):
        doc = _doc(
            '<defs><linearGradient id="a"/></defs>'
            '<rect data-note="see url(#a)" width="5" height="5"/>'
        )
        out = merge_svgs([doc, doc]).to_string()
        assert 'data-note="see url(#a)"' in out

    def test_funciri_attributes_still_rewritten(self):
        doc = _doc(
            '<defs><linearGradient id="a"/><clipPath id="c"/></defs>'
            '<rect fill="url(#a)" shape-inside="url(#c)" width="5" height="5"/>'
        )
        out = merge_svgs([doc, doc]).to_string()
        assert 'fill="url(#pathy-panel-0--a)"' in out
        assert 'shape-inside="url(#pathy-panel-0--c)"' in out


class TestStyleContentCollection:
    def test_css_after_comment_is_validated_and_rewritten(self):
        doc = _doc(
            "<style>#a{fill:red}<!--x-->.leak{fill:url(#grad)}</style>"
            '<defs><linearGradient id="grad"/></defs>'
            '<rect id="a" width="5" height="5"/>'
        )
        out = merge_svgs([doc, doc]).to_string()
        assert "url(#grad)" not in out
        assert "#pathy-panel-0 .leak{fill:url(#pathy-panel-0--grad)}" in out
        assert "#pathy-panel-1 .leak{fill:url(#pathy-panel-1--grad)}" in out
        assert "<!--" not in out

    def test_import_after_comment_is_rejected(self):
        doc = _doc("<style>a{}<!--x-->@import url(evil.css)</style><rect/>")
        with pytest.raises(CompositionError, match="@import"):
            merge_svgs([doc, doc])


class TestPanelOverflow:
    def test_nested_panel_defaults_to_visible_overflow(self):
        doc = _doc('<rect id="out" x="110" y="10" width="20" height="20"/>')
        nested = _nested_svg(merge_svgs([doc]))
        assert nested.get("overflow") == "visible"

    def test_explicit_overflow_attribute_preserved(self):
        doc = _doc("<rect/>", attrs='viewBox="0 0 100 100" overflow="hidden"')
        nested = _nested_svg(merge_svgs([doc]))
        assert nested.get("overflow") == "hidden"

    def test_explicit_style_overflow_preserved(self):
        doc = _doc("<rect/>", attrs='viewBox="0 0 100 100" style="overflow:hidden"')
        nested = _nested_svg(merge_svgs([doc]))
        assert nested.get("overflow") is None


class TestSmilTimingRewrites:
    def test_syncbase_on_id_with_keyword_prefix_is_rewritten(self):
        doc = _doc(
            '<rect id="mediaBtn" width="5" height="5">'
            '<animate attributeName="x" to="1" dur="1s" begin="mediaBtn.click"/>'
            "</rect>"
        )
        out = merge_svgs([doc, doc]).to_string()
        assert 'begin="pathy-panel-0--mediaBtn.click"' in out
        assert 'begin="pathy-panel-1--mediaBtn.click"' in out

    def test_unitless_offset_is_not_rewritten(self):
        doc = _doc(
            '<rect id="5" width="5" height="5">'
            '<animate attributeName="x" to="1" dur="1s" begin="5.5"/>'
            "</rect>"
        )
        out = merge_svgs([doc, doc]).to_string()
        assert 'begin="5.5"' in out
        assert "unresolved" not in out

    def test_non_syncbase_keywords_are_untouched(self):
        doc = _doc(
            '<rect id="repeatBox" width="5" height="5">'
            '<animate attributeName="x" to="1" dur="1s"'
            ' begin="indefinite; repeat(2)+2s"/>'
            '<animate attributeName="y" to="1" dur="1s" begin="repeatBox.begin"/>'
            "</rect>"
        )
        out = merge_svgs([doc, doc]).to_string()
        assert 'begin="indefinite; repeat(2)+2s"' in out
        assert 'begin="pathy-panel-0--repeatBox.begin"' in out


class TestAnimationShorthandNumbers:
    @pytest.mark.parametrize("delay", ["-.5s", "+.5s", ".5s", "-0.5s"])
    def test_sign_then_dot_delay_composes(self, delay):
        doc = _doc(
            "<style>@keyframes spin{from{opacity:0}} "
            f"#a{{animation: spin 1s {delay} linear;}}</style>"
            '<rect id="a" width="5" height="5"/>'
        )
        out = merge_svgs([doc, doc]).to_string()
        assert f"pathy-panel-0--keyframe--spin 1s {delay} linear" in out


class TestFontFaceComposition:
    def test_font_face_passes_through(self):
        doc = _doc(
            "<style>@font-face{font-family:MyFont;src:url(font.woff)} "
            "text{font-family:MyFont}</style><text>hi</text>"
        )
        out = merge_svgs([doc, doc]).to_string()
        assert "@font-face{font-family:MyFont;src:url(font.woff)}" in out

    def test_font_face_with_local_fragment_is_rejected(self):
        doc = _doc(
            "<style>@font-face{font-family:F;src:url(#localfont)}</style>"
            "<text>hi</text>"
        )
        with pytest.raises(CompositionError, match="font-face"):
            merge_svgs([doc])

    def test_import_still_rejected(self):
        doc = _doc("<style>@import url(x.css);</style><text>hi</text>")
        with pytest.raises(CompositionError, match="@import"):
            merge_svgs([doc])

    def test_unknown_at_rule_still_rejected(self):
        doc = _doc("<style>@pathy-custom {}</style><text>hi</text>")
        with pytest.raises(CompositionError, match="unsupported"):
            merge_svgs([doc])


class TestUnresolvedReferenceIsolation:
    STYLE = "<style>use[href*='mis']{stroke:red}</style>"
    USE = '<use href="#missing"/>'

    def test_partial_selector_succeeds_with_style_before_use(self):
        result = compose_svgs([_doc(self.STYLE + self.USE)])
        assert "missing" not in result.panels[0].id_map

    def test_partial_selector_succeeds_with_use_before_style(self):
        result = compose_svgs([_doc(self.USE + self.STYLE)])
        assert "missing" not in result.panels[0].id_map

    def test_partial_selector_on_rewritten_id_raises_in_both_orders(self):
        other = _doc('<rect id="dup" width="5" height="5"/>')
        style = "<style>use[href*='du']{stroke:red}</style>"
        body = '<rect id="dup" width="5" height="5"/><use href="#dup"/>'
        with pytest.raises(CompositionError, match="partial CSS attribute"):
            compose_svgs([_doc(style + body), other])
        with pytest.raises(CompositionError, match="partial CSS attribute"):
            compose_svgs([_doc(body + style), other])

    def test_repeated_unresolved_reference_maps_consistently(self):
        merged = merge_svgs([_doc(self.USE + self.USE)])
        hrefs = [use.get("href") for use in merged.root.iter(f"{{{SVG_NS}}}use")]
        assert hrefs == ["#pathy-panel-0--unresolved--missing"] * 2
