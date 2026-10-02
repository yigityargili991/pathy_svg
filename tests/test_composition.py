"""Regression tests for pathy_svg._composition and composition in svg_tools."""

import pytest
from lxml import etree

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


def _style_css(merged: SVGDocument, index: int = 0) -> str:
    panel = merged.root.xpath(f"./svg:g[@data-panel-index='{index}']", namespaces=NS)[0]
    return panel.xpath(".//svg:style", namespaces=NS)[0].text


def _unscoped_selectors(css: str, scope: str) -> list[str]:
    """Return the selectors a browser-grade CSS parser sees outside *scope*.

    tinycss2 implements CSS Syntax Level 3 tokenization, so it agrees with
    browsers on where strings, escapes and url() tokens end. Selector lists
    are split naively on commas, which suffices for the inputs tested here.
    """
    tinycss2 = pytest.importorskip("tinycss2")
    unscoped: list[str] = []

    def walk(rules) -> None:
        for rule in rules:
            if rule.type == "qualified-rule":
                for selector in tinycss2.serialize(rule.prelude).split(","):
                    if not selector.strip().startswith(scope):
                        unscoped.append(selector.strip())
            elif rule.type == "at-rule" and rule.lower_at_keyword in {
                "container",
                "layer",
                "media",
                "scope",
                "supports",
            }:
                walk(
                    tinycss2.parse_rule_list(
                        rule.content or [], skip_comments=True, skip_whitespace=True
                    )
                )

    walk(tinycss2.parse_stylesheet(css, skip_comments=True, skip_whitespace=True))
    return unscoped


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
        style = "<style>use[href^='#du']{stroke:red}</style>"
        body = '<rect id="dup" width="5" height="5"/><use href="#dup"/>'
        with pytest.raises(CompositionError, match="partial CSS attribute"):
            compose_svgs([_doc(style + body), other])
        with pytest.raises(CompositionError, match="partial CSS attribute"):
            compose_svgs([_doc(body + style), other])

    def test_repeated_unresolved_reference_maps_consistently(self):
        merged = merge_svgs([_doc(self.USE + self.USE)])
        hrefs = [use.get("href") for use in merged.root.iter(f"{{{SVG_NS}}}use")]
        assert hrefs == ["#pathy-panel-0--unresolved--missing"] * 2


# Each stylesheet hides `rect {fill:red}` from a scanner that disagrees with
# CSS Syntax Level 3 about escapes, bad strings, url() tokens or at-rule names.
DESYNC_CSS = {
    "escaped quote": r'.a\"b {fill:blue} rect {fill:red} .c {content:"x"}',
    "escaped brace": r".a\{b {fill:blue} rect {fill:red}",
    "newline ends string": '.a {content:"abc\n} rect {fill:red} .b {content:"y"}',
    "escaped url name": r'.a {b:u\72l(x"y)} rect {fill:red} .c {d:"z"}',
    "escaped at-rule name": r"@\6d edia screen { rect {fill:red} }",
}


class TestCssTokensMatchBrowsers:
    @pytest.mark.parametrize("css", DESYNC_CSS.values(), ids=DESYNC_CSS.keys())
    def test_escapes_and_bad_tokens_cannot_unscope_rules(self, css):
        merged = merge_svgs([_doc(f"<style>{css}</style><rect/>")])
        assert "#pathy-panel-0 rect {fill:red}" in _style_css(merged)

    @pytest.mark.parametrize("css", DESYNC_CSS.values(), ids=DESYNC_CSS.keys())
    def test_browser_tokenizer_sees_only_scoped_rules(self, css):
        merged = merge_svgs([_doc(f"<style>{css}</style><rect/>")])
        assert _unscoped_selectors(_style_css(merged), "#pathy-panel-0") == []

    @pytest.mark.parametrize(
        ("css", "expected"),
        [
            ('.p {q:url (x")" ) } rect {fill:url(#a)}', "url(#pathy-panel-0--a)"),
            ('.p {q:url/**/(x/*)"*/) } rect {fill:url(#a)}', "url(#pathy-panel-0--a)"),
            (r"rect {fill:\75rl(#a)}", r"\75rl(#pathy-panel-0--a)"),
        ],
        ids=[
            "url-space-paren hides quote",
            "url-comment-paren hides comment",
            "escaped",
        ],
    )
    def test_url_references_browsers_resolve_are_rewritten(self, css, expected):
        doc = _doc(f'<linearGradient id="a"/><style>{css}</style><rect/>')
        assert expected in _style_css(merge_svgs([doc, doc]))

    @pytest.mark.parametrize(
        "rule",
        [
            '@property --c {syntax:"*";inherits:false;initial-value:red}',
            "@layer theme {rect {fill:red}}",
            "@pathy-custom {}",
        ],
    )
    def test_bad_url_cannot_hide_document_global_at_rules(self, rule):
        doc = _doc(f'<style>.a {{background:url(x"y)}} {rule}</style><rect/>')
        with pytest.raises(CompositionError, match="Cannot safely compose"):
            merge_svgs([doc])

    def test_bad_url_cannot_hide_keyframes_from_namespacing(self):
        doc = _doc(
            '<style>.a {background:url(x"y)} @keyframes spin {to {opacity:0}} '
            ".b {animation:spin 1s}</style><rect class='b'/>"
        )
        merged = merge_svgs([doc, doc])
        for index in range(2):
            css = _style_css(merged, index)
            assert f"@keyframes pathy-panel-{index}--keyframe--spin" in css
            assert f"animation:pathy-panel-{index}--keyframe--spin 1s" in css

    def test_escaped_keyframes_keyword_is_namespaced(self):
        doc = _doc(
            r"<style>@\6b eyframes spin {to {opacity:0}} .b {animation:spin 1s}"
            "</style><rect class='b'/>"
        )
        css = _style_css(merge_svgs([doc]))
        assert r"@\6b eyframes pathy-panel-0--keyframe--spin" in css
        assert "animation:pathy-panel-0--keyframe--spin 1s" in css

    def test_escaped_at_sign_in_class_name_is_not_an_at_rule(self):
        css = _style_css(
            merge_svgs([_doc(r"<style>.md\@lg {fill:red}</style><rect/>")])
        )
        assert r"#pathy-panel-0 .md\@lg {fill:red}" in css

    def test_long_identifiers_are_scanned_in_linear_time(self):
        import time

        doc = _doc(f"<style>.a{'b' * 20_000} {{fill:red}}</style><rect/>")
        started = time.perf_counter()
        merge_svgs([doc])
        assert time.perf_counter() - started < 3.0

    @pytest.mark.parametrize("escape", [r"\D800", r"\DFFF", r"\FFFE", r"\FFFF"])
    def test_invalid_code_point_escapes_become_replacement_characters(self, escape):
        doc = _doc(
            f"<style>#{escape} {{fill:red}} [id='{escape}'] {{fill:red}} "
            f"@keyframes {escape} {{to {{opacity:0}}}} "
            f".a {{animation-name:{escape}}}</style>"
            f'<rect fill="url(#{escape})"/>'
        )
        out = merge_svgs([doc]).to_string()
        assert "\N{REPLACEMENT CHARACTER}" in out
        SVGDocument.from_string(out)


class TestAnimationValueReferences:
    def test_animation_values_rewrite_url_references(self):
        doc = _doc(
            '<linearGradient id="g"/><rect fill="red">'
            '<set attributeName="fill" to="url(#g)"/>'
            '<animate attributeName="fill" from="url(#g)" by="url(#g)" '
            'values="url(#g);red" dur="1s"/></rect>'
        )
        merged = merge_svgs([doc, doc])
        for index in range(2):
            panel = merged.root.xpath(
                f"./svg:g[@data-panel-index='{index}']", namespaces=NS
            )[0]
            expected = f"url(#pathy-panel-{index}--g)"
            assert panel.xpath(".//svg:set", namespaces=NS)[0].get("to") == expected
            animate = panel.xpath(".//svg:animate", namespaces=NS)[0]
            assert animate.get("from") == expected
            assert animate.get("by") == expected
            assert animate.get("values") == f"{expected};red"

    def test_animation_values_cannot_bind_another_panels_ids(self):
        first = _doc(
            '<rect fill="url(#only1)"><set attributeName="fill" to="url(#only1)"/>'
            "</rect>"
        )
        second = _doc('<linearGradient id="only1"/>')
        merged = merge_svgs([first, second])
        set_elem = merged.root.xpath(
            "./svg:g[@data-panel-index='0']//svg:set", namespaces=NS
        )[0]
        assert set_elem.get("to") == "url(#pathy-panel-0--unresolved--only1)"


class TestValidCssIsNotRejected:
    def test_important_animation_shorthand_composes(self):
        doc = _doc(
            "<style>@keyframes spin {to {opacity:0}} "
            ".b {animation:spin 1s linear infinite !important}</style>"
            "<rect class='b'/>"
        )
        css = _style_css(merge_svgs([doc]))
        assert (
            "animation:pathy-panel-0--keyframe--spin 1s linear infinite !important"
            in css
        )

    def test_charset_rule_composes(self):
        doc = _doc('<style>@charset "UTF-8"; rect {fill:red}</style><rect/>')
        css = _style_css(merge_svgs([doc]))
        assert '@charset "UTF-8";' in css
        assert "#pathy-panel-0 rect {fill:red}" in css

    def test_partial_href_selector_whose_matches_survive_renaming_composes(self):
        doc = _doc(
            '<style>use[href^="#"] {stroke:red}</style><path id="p"/><use href="#p"/>'
        )
        css = _style_css(merge_svgs([doc, doc]))
        assert '#pathy-panel-0 use[href^="#"] {stroke:red}' in css


class TestEntityReferences:
    DTD = (
        '<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY css "rect {fill:red}">'
        '<!ENTITY paint "url(#g)">]>'
    )

    BODIES = pytest.mark.parametrize(
        "body",
        [
            "<style>&css;</style><rect/>",
            '<linearGradient id="g"/><rect fill="&paint;"/>',
        ],
        ids=["element content", "attribute value"],
    )

    @pytest.mark.parametrize(
        ("body", "expected"),
        [
            ("<style>&css;</style><rect/>", "#pathy-panel-1 rect {fill:red}"),
            (
                '<linearGradient id="g"/><rect fill="&paint;"/>',
                'fill="url(#pathy-panel-1--g)"',
            ),
        ],
        ids=["element content", "attribute value"],
    )
    def test_parsed_internal_entities_compose_well_formed(self, body, expected):
        doc = SVGDocument.from_string(
            f'{self.DTD}<svg xmlns="{SVG_NS}" viewBox="0 0 10 10">{body}</svg>'
        )

        out = merge_svgs([doc, doc]).to_string()

        # Expanded at parse time, so the output needs no DTD and is scoped.
        assert expected in out
        SVGDocument.from_string(out)

    @BODIES
    @pytest.mark.parametrize("rewrap", [False, True], ids=["tree", "rewrapped"])
    def test_unexpanded_entity_references_are_rejected(self, body, rewrap):
        # Trees parsed by callers can still hold entity references.
        source = f'{self.DTD}<svg xmlns="{SVG_NS}" viewBox="0 0 10 10">{body}</svg>'
        parser = etree.XMLParser(resolve_entities=False)
        doc = SVGDocument.from_tree(
            etree.ElementTree(etree.fromstring(source.encode(), parser))
        )
        if rewrap:
            # Copying the root drops the DTD but keeps the entity references.
            doc = SVGDocument.from_tree(etree.ElementTree(doc.root_copy()))
        with pytest.raises(CompositionError, match="entity references"):
            merge_svgs([doc])

    def test_entity_declared_namespace_still_composes(self):
        doc = SVGDocument.from_string(
            '<?xml version="1.0"?><!DOCTYPE svg ['
            '<!ENTITY ns_ai "http://ns.adobe.com/AdobeIllustrator/10.0/">]>'
            f'<svg xmlns="{SVG_NS}" xmlns:i="&ns_ai;" viewBox="0 0 10 10">'
            '<rect i:knockout="Off"/></svg>'
        )
        out = merge_svgs([doc]).to_string()
        assert "http://ns.adobe.com/AdobeIllustrator/10.0/" in out
        SVGDocument.from_string(out)
