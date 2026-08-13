"""Comprehensive tests for pathy_svg.utils."""

from __future__ import annotations

import pytest

from pathy_svg.color import hex_to_rgb, interpolate_color, parse_svg_color, rgb_to_hex
from pathy_svg.data import bin_values, normalize_values
from pathy_svg.svg_tools import (
    compose_svgs,
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
    SVG_WITH_REFERENCES = """<svg xmlns="http://www.w3.org/2000/svg"
        xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 100 100">
      <defs>
        <linearGradient id="paint"><stop offset="1" stop-color="red"/></linearGradient>
        <clipPath id="clip"><use href="#shape"/></clipPath>
        <mask id="mask"><use xlink:href="#shape"/></mask>
        <style>
          #shape, [id="shape"] { fill: url(#paint); clip-path: url('#clip') }
          [href="#shape"] { mask: url(#mask) }
        </style>
      </defs>
      <title id="label">Panel shape</title>
      <desc id="description">Description</desc>
      <path id="shape" d="M0 0h10v10z" fill="url(#paint)"
            clip-path="url(#clip)" style="mask:url(#mask)"
            aria-labelledby="label description"/>
      <use id="instance" href="#shape" xlink:href="#shape"/>
      <animate id="animation" begin="shape.click; instance.end" dur="1s"/>
    </svg>"""

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

    def test_invalid_layout_raises(self):
        a, b = self._docs()
        with pytest.raises(ValueError, match="layout must be"):
            merge_svgs([a, b], layout="diagonal")

    def test_single_svg(self):
        from pathy_svg.document import SVGDocument

        a, _ = self._docs()
        result = merge_svgs([a])
        assert isinstance(result, SVGDocument)
        vb = result.viewbox
        assert vb.width == pytest.approx(100.0)
        assert result._find_by_id("a") is not None

    def test_children_preserved(self):
        a, b = self._docs()
        result = merge_svgs([a, b])
        svg_str = result.to_string()
        assert 'id="a"' in svg_str
        assert 'id="b"' in svg_str
        assert 'data-original-id="a"' not in svg_str
        assert 'data-original-id="b"' not in svg_str

    def test_rebases_nonzero_viewbox_origins(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="100 50 20 30">'
            '<rect id="region" x="100" y="50" width="20" height="30"/>'
            "</svg>"
        )

        horizontal = merge_svgs([doc], layout="horizontal")
        vertical = merge_svgs([doc], layout="vertical")

        for result in (horizontal, vertical):
            panel = result.root[0]
            nested = panel.find("{http://www.w3.org/2000/svg}svg")
            assert panel.get("transform") == "translate(0.0, 0.0)"
            assert nested.get("viewBox") == "100 50 20 30"
            assert nested.get("width") == "20.0"
            assert nested.get("height") == "30.0"

    def test_namespaces_a_source_id_reserved_for_panel_wrappers(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
            '<path id="pathy-panel-0" d="M0 0h1v1z"/>'
            '<use id="copy" href="#pathy-panel-0"/>'
            "</svg>"
        )
        result = merge_svgs([doc])
        panel = result.root[0]
        path = panel.find(".//{http://www.w3.org/2000/svg}path")
        use = panel.find(".//{http://www.w3.org/2000/svg}use")

        assert panel.get("id") == "pathy-panel-0"
        assert path.get("id") == "pathy-panel-0--pathy-panel-0"
        assert path.get("data-original-id") == "pathy-panel-0"
        assert use.get("href") == "#pathy-panel-0--pathy-panel-0"

    def test_duplicate_ids_within_one_source_are_still_globally_unique(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" id="canvas" '
            'viewBox="0 0 10 10">'
            '<path id="duplicate"/><path id="duplicate"/>'
            '<use id="copy" href="#duplicate"/>'
            "</svg>"
        )
        result = merge_svgs([doc])
        ids = [elem.get("id") for elem in result.root.xpath(".//*[@id]")]
        use = result.root.find(".//{http://www.w3.org/2000/svg}use")

        assert len(ids) == len(set(ids))
        assert "canvas" in ids
        assert "pathy-panel-0--duplicate" in ids
        assert "pathy-panel-0--duplicate--duplicate-1" in ids
        assert use.get("href") == "#pathy-panel-0--duplicate"

    def test_generated_collision_id_never_displaces_a_unique_source_id(self):
        from pathy_svg.document import SVGDocument

        first = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
            '<path id="shared"/><use id="copy" href="#shared"/>'
            "</svg>"
        )
        second = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
            '<path id="shared"/><path id="pathy-panel-0--shared"/>'
            "</svg>"
        )
        result = merge_svgs([first, second])
        ids = [elem.get("id") for elem in result.root.xpath(".//*[@id]")]
        first_use = result.root[0].find(".//{http://www.w3.org/2000/svg}use")

        assert len(ids) == len(set(ids))
        assert "pathy-panel-0--shared" in ids
        assert "pathy-panel-0--shared--duplicate-1" in ids
        assert first_use.get("href") == "#pathy-panel-0--shared--duplicate-1"

    def test_preserves_root_state_and_maps_root_id_to_panel_wrapper(self):
        from pathy_svg.document import SVGDocument

        source = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" id="canvas" '
            'viewBox="10 20 30 40" class="theme" fill="red" stroke="blue" '
            'opacity="0.5" color="purple" font-family="serif" visibility="hidden" '
            'style="filter:url(#effect)" clip-path="url(#clip)" '
            'shape-inside="url(#clip)" transform="scale(2)" '
            'transform-origin="center" transform-box="view-box" '
            'preserveAspectRatio="xMinYMin slice" overflow="visible">'
            '<defs><filter id="effect"/><clipPath id="clip"/></defs>'
            '<use id="root-copy" href="#canvas"/>'
            "</svg>"
        )
        single = merge_svgs([source])
        single_panel = single.root[0]
        single_svg = single_panel.find("{http://www.w3.org/2000/svg}svg")
        single_use = single_svg.find("{http://www.w3.org/2000/svg}use")

        assert single_panel.get("id") == "pathy-panel-0"
        assert single_svg.get("id") == "canvas"
        assert single_svg.get("data-original-id") is None
        assert single_use.get("href") == "#canvas"

        result = merge_svgs([source, source])
        ns = {"svg": "http://www.w3.org/2000/svg"}

        for index in range(2):
            prefix = f"pathy-panel-{index}"
            panel = result.root.xpath(
                f"./svg:g[@data-panel-index='{index}']", namespaces=ns
            )[0]
            nested = panel.xpath("./svg:svg", namespaces=ns)[0]
            use = nested.xpath("./svg:use", namespaces=ns)[0]

            assert panel.get("id") == prefix
            assert nested.get("id") == f"{prefix}--canvas"
            assert nested.get("data-original-id") == "canvas"
            assert nested.get("viewBox") == "10 20 30 40"
            assert nested.get("class") == "theme"
            assert nested.get("fill") == "red"
            assert nested.get("stroke") == "blue"
            assert nested.get("opacity") == "0.5"
            assert nested.get("color") == "purple"
            assert nested.get("font-family") == "serif"
            assert nested.get("visibility") == "hidden"
            assert nested.get("style") == f"filter:url(#{prefix}--effect)"
            assert nested.get("clip-path") == f"url(#{prefix}--clip)"
            assert nested.get("shape-inside") == f"url(#{prefix}--clip)"
            assert nested.get("transform") == "scale(2)"
            assert nested.get("transform-origin") == "center"
            assert nested.get("transform-box") == "view-box"
            assert nested.get("preserveAspectRatio") == "xMinYMin slice"
            assert nested.get("overflow") == "visible"
            assert panel.get("transform").startswith("translate(")
            assert use.get("href") == f"#{prefix}--canvas"

    def test_localizes_unresolved_fragments_that_exist_in_another_panel(self):
        from pathy_svg.document import SVGDocument

        first = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
            '<use id="copy" href="#only-in-second"/>'
            '<path id="paint" fill="url(#only-in-second)"/>'
            "</svg>"
        )
        second = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
            '<linearGradient id="only-in-second"/>'
            "</svg>"
        )
        result = merge_svgs([first, second])
        first_panel = result.root[0]
        use = first_panel.find(".//{http://www.w3.org/2000/svg}use")
        path = first_panel.find(".//{http://www.w3.org/2000/svg}path")

        assert use.get("href") == "#pathy-panel-0--unresolved--only-in-second"
        assert path.get("fill") == "url(#pathy-panel-0--unresolved--only-in-second)"
        assert result._find_by_id("only-in-second") is not None
        assert result._find_by_id("pathy-panel-0--unresolved--only-in-second") is None

    def test_unresolved_fragments_cannot_bind_generated_output_ids(self):
        from pathy_svg.document import SVGDocument

        first = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
            '<use id="wrapper-copy" href="#pathy-panel-1"/>'
            '<use id="generated-copy" href="#pathy-panel-1--shared"/>'
            '<path id="shared"/>'
            "</svg>"
        )
        second = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
            '<path id="shared"/>'
            "</svg>"
        )
        result = merge_svgs([first, second])
        uses = result.root[0].findall(".//{http://www.w3.org/2000/svg}use")

        assert uses[0].get("href").startswith("#pathy-panel-0--unresolved--")
        assert uses[1].get("href").startswith("#pathy-panel-0--unresolved--")
        assert result._find_by_id(uses[0].get("href")[1:]) is None
        assert result._find_by_id(uses[1].get("href")[1:]) is None

    @pytest.mark.parametrize("malformed_id", ["", "bad id", "  "])
    def test_sanitizes_malformed_source_ids(self, malformed_id):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
            f'<path id="{malformed_id}"/><use id="copy" href="#{malformed_id}"/>'
            f"""<rect fill='url("#{malformed_id}")'/>"""
            "</svg>"
        )
        first = merge_svgs([doc]).to_string()
        second = merge_svgs([doc]).to_string()
        reparsed = SVGDocument.from_string(first)
        ids = [elem.get("id") for elem in reparsed.root.xpath(".//*[@id]")]
        path = reparsed.root.find(".//{http://www.w3.org/2000/svg}path")
        use = reparsed.root.find(".//{http://www.w3.org/2000/svg}use")
        rect = reparsed.root.find(".//{http://www.w3.org/2000/svg}rect")

        assert first == second
        assert len(ids) == len(set(ids))
        assert all(
            elem_id and not any(char.isspace() for char in elem_id) for elem_id in ids
        )
        assert use.get("href") == f"#{path.get('id')}"
        assert rect.get("fill") == f'url("#{path.get("id")}")'

    def test_scopes_panel_css_and_namespaces_keyframes(self):
        from pathy_svg.document import SVGDocument

        red = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
            "<style>.region, text {fill:red} @keyframes pulse {"
            "from {opacity:0} to {opacity:1}} "
            ".region {animation:pulse 1s; animation-name:pulse}</style>"
            '<path class="region"/><text>inside red</text>'
            "</svg>"
        )
        blue = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
            "<style>.region, text {fill:blue} @keyframes pulse {"
            "from {opacity:1} to {opacity:0}} "
            ".region {animation:pulse 2s}</style>"
            '<path class="region"/><text>inside blue</text>'
            "</svg>"
        )
        result = merge_svgs([red, blue])
        ns = {"svg": "http://www.w3.org/2000/svg"}

        for index, color in enumerate(("red", "blue")):
            panel = result.root.xpath(
                f"./svg:g[@data-panel-index='{index}']", namespaces=ns
            )[0]
            css = panel.xpath(".//svg:style", namespaces=ns)[0].text
            prefix = f"pathy-panel-{index}"

            assert f"#{prefix} .region" in css
            assert f"#{prefix} text" in css
            assert f"fill:{color}" in css
            assert f"@keyframes {prefix}--keyframe--pulse" in css
            assert f"animation:{prefix}--keyframe--pulse" in css
            if index == 0:
                assert f"animation-name:{prefix}--keyframe--pulse" in css

    def test_css_comment_tokens_and_case_insensitive_selector_expansion(self):
        from pathy_svg.document import SVGDocument

        source = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
            '<defs><linearGradient id="paint"/><style>'
            '[id/**/="shape" i] {fill:url/**/(#paint)}'
            "</style></defs>"
            '<path id="shape"/><path id="Shape"/>'
            "</svg>"
        )
        result = merge_svgs([source, source])
        ns = {"svg": "http://www.w3.org/2000/svg"}

        for index in range(2):
            prefix = f"pathy-panel-{index}"
            panel = result.root.xpath(
                f"./svg:g[@data-panel-index='{index}']", namespaces=ns
            )[0]
            css = panel.xpath(".//svg:style", namespaces=ns)[0].text

            assert f'#{prefix} [id/**/="{prefix}--shape" i]' in css
            assert f'#{prefix} [id/**/="{prefix}--Shape" i]' in css
            assert f"url/**/(#{prefix}--paint)" in css

    def test_collision_planning_fuzz_is_deterministic(self):
        import random

        from pathy_svg.document import SVGDocument

        randomizer = random.Random(731)
        pool = [
            "",
            " ",
            "shared",
            "Shape",
            "shape",
            "dots.and:punctuation",
            "pathy-panel-0",
            "pathy-panel-7",
            "unique-a",
            "unique-b",
        ]
        docs = []
        for _ in range(12):
            ids = [randomizer.choice(pool) for _ in range(5)]
            target = randomizer.choice(pool)
            paths = "".join(f'<path id="{elem_id}"/>' for elem_id in ids)
            docs.append(
                SVGDocument.from_string(
                    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
                    f'{paths}<use id="copy-{len(docs)}" href="#{target}"/>'
                    "</svg>"
                )
            )

        first = merge_svgs(docs).to_string()
        second = merge_svgs(docs).to_string()
        reparsed = SVGDocument.from_string(first)
        ids = [elem.get("id") for elem in reparsed.root.xpath(".//*[@id]")]

        assert first == second
        assert len(ids) == len(set(ids))
        assert all(
            elem_id and not any(char.isspace() for char in elem_id) for elem_id in ids
        )

    def test_root_pseudo_targets_nested_svg_in_functional_and_compound_selectors(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
            "<style>"
            ":root, svg:root, .theme:root, :where(:root), "
            r":is(:root, .region), :not(:root), :where(:\72 oot) { color: red }"
            '</style><path class="region"/>'
            "</svg>"
        )
        result = merge_svgs([doc])
        css = result.root.find(".//{http://www.w3.org/2000/svg}style").text

        assert ":root" not in css
        assert "#pathy-panel-0 > svg" in css
        assert "#pathy-panel-0 > svg.theme" in css
        assert ":where(#pathy-panel-0 > svg)" in css
        assert ":is(#pathy-panel-0 > svg, .region)" in css
        assert ":not(#pathy-panel-0 > svg)" in css
        assert r":\72 oot" not in css
        assert "svg#pathy-panel-0" not in css

    def test_animation_shorthand_does_not_rewrite_component_keywords(self):
        from pathy_svg.document import SVGDocument

        keywords = "linear ease infinite reverse both running"
        keyframes = "".join(
            f"@keyframes {name} {{ from {{opacity:0}} to {{opacity:1}} }}"
            for name in (*keywords.split(), "pulse")
        )
        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
            f"<style>{keyframes}.region {{ animation:1s linear infinite reverse "
            "both running pulse; animation-name:linear, pulse }</style>"
            '<path class="region"/>'
            "</svg>"
        )
        css = merge_svgs([doc]).root.find(".//{http://www.w3.org/2000/svg}style").text

        assert (
            "animation:1s linear infinite reverse both running "
            "pathy-panel-0--keyframe--pulse" in css
        )
        assert (
            "animation-name:pathy-panel-0--keyframe--linear, "
            "pathy-panel-0--keyframe--pulse" in css
        )
        for keyword in keywords.split():
            assert f"@keyframes pathy-panel-0--keyframe--{keyword}" in css

    @pytest.mark.parametrize(
        "keyword",
        [
            "linear",
            "ease",
            "ease-in",
            "ease-in-out",
            "ease-out",
            "step-start",
            "step-end",
            "infinite",
            "normal",
            "reverse",
            "alternate",
            "alternate-reverse",
            "forwards",
            "backwards",
            "both",
            "running",
            "paused",
            "auto",
        ],
    )
    def test_repeated_animation_keyword_uses_final_token_as_name(self, keyword):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
            f"<style>@keyframes {keyword} {{from {{opacity:0}}}}"
            f".x {{animation:1s {keyword} {keyword}}}</style></svg>"
        )
        css = merge_svgs([doc]).root.find(".//{http://www.w3.org/2000/svg}style").text

        assert f"animation:1s {keyword} pathy-panel-0--keyframe--{keyword}" in css

    @pytest.mark.parametrize(
        "keyword", ["none", "inherit", "initial", "unset", "revert", "revert-layer"]
    )
    def test_reserved_animation_names_fail_closed_in_shorthand(self, keyword):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
            f"<style>@keyframes {keyword} {{from {{opacity:0}}}}"
            f".x {{animation:1s {keyword} {keyword}}}</style></svg>"
        )

        with pytest.raises(ValueError, match="reserved keyframe name"):
            merge_svgs([doc])

    def test_localizes_every_encountered_unknown_fragment_on_demand(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" '
            'aria-labelledby="missing-label">'
            "<style>#missing-selector {fill:url(#missing-css-paint)}</style>"
            '<path id="owned" fill="url(#missing-paint)" '
            'style="filter:url(#missing-filter)"/>'
            '<use href="#missing-use"/>'
            '<animate begin="missing-trigger.click" end="missing-end.end"/>'
            "</svg>"
        )
        result = merge_svgs([doc])
        serialized = result.to_string()

        for fragment in (
            "missing-label",
            "missing-selector",
            "missing-css-paint",
            "missing-paint",
            "missing-filter",
            "missing-use",
            "missing-trigger",
            "missing-end",
        ):
            dead_id = f"pathy-panel-0--unresolved--{fragment}"
            assert dead_id in serialized
            assert result._find_by_id(dead_id) is None

    def test_nested_css_rules_inherit_scope_without_duplicate_prefix(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
            "<style>.parent { &amp; #child {fill:red} #child {stroke:blue} }</style>"
            '<g class="parent"><path id="child"/></g>'
            "</svg>"
        )
        css = (
            merge_svgs([doc, doc])
            .root.find(".//{http://www.w3.org/2000/svg}style")
            .text
        )

        assert "#pathy-panel-0 .parent" in css
        assert "& #pathy-panel-0--child" in css
        assert "#pathy-panel-0--child {stroke:blue}" in css
        assert "#pathy-panel-0 &" not in css
        assert "#pathy-panel-0 #pathy-panel-0--child {stroke:blue}" not in css

    def test_panel_planning_stays_linear_for_many_panels(self):
        import time

        from pathy_svg._composition import plan_svg_panels
        from pathy_svg.document import SVGDocument

        roots = [
            SVGDocument.from_string(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
                f'<path id="unique-{index}"/><use href="#dangling-{index}"/>'
                "</svg>"
            ).root
            for index in range(300)
        ]

        started = time.perf_counter()
        plans = plan_svg_panels(roots)
        elapsed = time.perf_counter() - started

        assert sum(len(plan.reference_map) for plan in plans) == 300
        assert len({id(plan.blocked_ids) for plan in plans}) == 1
        assert elapsed < 3.0

    def test_smil_preserves_clock_values_and_rewrites_eventbases(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
            '<path id="target.with.dot"/>'
            '<animate begin="1.5s; -0.25s; 00:00:01.5; '
            "wallclock(2020-01-01T00:00:00Z); indefinite; accessKey(a); "
            'target.with.dot.click+0.5s; missing.end-0.2s"/>'
            "</svg>"
        )
        begin = (
            merge_svgs([doc, doc])
            .root.find(".//{http://www.w3.org/2000/svg}animate")
            .get("begin")
        )

        assert begin.startswith(
            "1.5s; -0.25s; 00:00:01.5; "
            "wallclock(2020-01-01T00:00:00Z); indefinite; accessKey(a); "
        )
        assert "pathy-panel-0--target.with.dot.click+0.5s" in begin
        assert "pathy-panel-0--unresolved--missing.end-0.2s" in begin

    def test_nested_conditional_rules_and_scope_inherit_panel_scope(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
            "<style>.parent {"
            "@media (width > 0px) { #child {fill:red} }"
            "@supports (fill:red) { #child {stroke:red} }"
            "@layer { #child {opacity:.5} }"
            "@container (width > 0px) { #child {color:red} }"
            "@starting-style { opacity:0 }"
            "} @scope (.parent) to (#child) { #child {display:block} }"
            '</style><g class="parent"><path id="child"/></g>'
            "</svg>"
        )
        css = (
            merge_svgs([doc, doc])
            .root.find(".//{http://www.w3.org/2000/svg}style")
            .text
        )

        assert "#pathy-panel-0 .parent" in css
        assert css.count("#pathy-panel-0 #pathy-panel-0--child") == 0
        assert "@media (width > 0px) { #pathy-panel-0--child" in css
        assert "@supports (fill:red) { #pathy-panel-0--child" in css
        assert "@layer { #pathy-panel-0--child" in css
        assert "@container (width > 0px) { #pathy-panel-0--child" in css
        assert "@starting-style { opacity:0 }" in css
        assert "@scope (#pathy-panel-0 .parent) to (#pathy-panel-0--child)" in css

    @pytest.mark.parametrize("rule", ["@import url(x.css);", "@property --x {}"])
    def test_rejects_document_global_css_at_rules(self, rule):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
            f"<style>{rule}</style></svg>"
        )

        with pytest.raises(ValueError, match="Cannot safely compose SVG CSS"):
            merge_svgs([doc])

    def test_rejects_named_layers_before_they_can_leak_between_panels(self):
        from pathy_svg.document import SVGDocument

        first = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
            "<style>@layer reset, theme; @layer reset {.x {fill:red}}</style></svg>"
        )
        second = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
            "<style>@layer theme, reset; @layer reset {.x {fill:blue}}</style></svg>"
        )

        with pytest.raises(ValueError, match="named CSS @layer"):
            merge_svgs([first, second])

    def test_css_scanners_do_not_enter_unquoted_function_payloads(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
            "<style>@keyframes pulse {from {opacity:0}} .x {"
            "background:url(data:text/plain,animation:pulse);"
            "mask:url(data:text/plain,@keyframes/**/payload{x:y});"
            "animation-name:pulse}</style></svg>"
        )
        css = merge_svgs([doc]).root.find(".//{http://www.w3.org/2000/svg}style").text

        assert "url(data:text/plain,animation:pulse)" in css
        assert "url(data:text/plain,@keyframes/**/payload{x:y})" in css
        assert "keyframe--payload" not in css
        assert "animation-name:pathy-panel-0--keyframe--pulse" in css

    @pytest.mark.parametrize("operator", ["^=", "$=", "*=", "|="])
    def test_partial_href_selectors_fail_when_target_ids_are_rewritten(self, operator):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
            f'<style>[href{operator}"#shape"] {{fill:red}}</style>'
            '<path id="shape"/><use href="#shape"/></svg>'
        )

        with pytest.raises(ValueError, match="partial CSS attribute selector"):
            merge_svgs([doc, doc])

    @pytest.mark.parametrize(
        ("operator", "selector_value"),
        [("^=", "a "), ("$=", " b"), ("*=", "a b")],
    )
    def test_partial_aria_idref_selectors_fail_atomically(
        self, operator, selector_value
    ):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
            f'<style>[aria-labelledby{operator}"{selector_value}"] '
            "{fill:red}</style>"
            '<title id="a"/><title id="b"/>'
            '<path aria-labelledby="a b"/></svg>'
        )

        with pytest.raises(
            ValueError, match="partial CSS attribute selector on ARIA IDREF"
        ):
            merge_svgs([doc, doc])

    def test_partial_aria_idref_selector_rejects_without_id_rebasing(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
            '<style>[aria-labelledby*="a b"] {fill:red}</style>'
            '<title id="a"/><title id="b"/>'
            '<path aria-labelledby="a b"/></svg>'
        )

        with pytest.raises(
            ValueError, match="partial CSS attribute selector on ARIA IDREF"
        ):
            merge_svgs([doc])

    def test_animation_parser_skips_function_arguments_and_rejects_variables(self):
        from pathy_svg.document import SVGDocument

        names = ("pulse", "end", "root", "linear", "steps", "view")
        keyframes = "".join(
            f"@keyframes {name} {{from {{opacity:0}}}}" for name in names
        )
        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
            f"<style>{keyframes}.x {{animation:1s steps(2,end) "
            "cubic-bezier(0,0,1,1) scroll(root x) view() pulse;"
            "animation-name:linear, steps, view}}</style></svg>"
        )
        css = merge_svgs([doc]).root.find(".//{http://www.w3.org/2000/svg}style").text

        assert "steps(2,end)" in css
        assert "scroll(root x)" in css
        assert "view()" in css
        assert "pathy-panel-0--keyframe--pulse" in css
        assert "animation-name:pathy-panel-0--keyframe--linear" in css
        assert "pathy-panel-0--keyframe--steps" in css
        assert "pathy-panel-0--keyframe--view" in css

        variable_doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
            "<style>.x {animation:1s var(--animation-name)}</style></svg>"
        )
        with pytest.raises(ValueError, match=r"animation using var\(\)"):
            merge_svgs([variable_doc])

    def test_keyframe_aliases_are_unique_and_foreign_styles_are_scoped(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(
            r"""<svg xmlns="http://www.w3.org/2000/svg"
                xmlns:xhtml="http://www.w3.org/1999/xhtml" viewBox="0 0 1 1">
              <style>@keyframes a\ b {from{opacity:0}} @keyframes a-b {to{opacity:1}}
                .one {animation-name:a\ b,a-b}</style>
              <foreignObject><xhtml:style>.foreign {color:red}</xhtml:style>
                <xhtml:div class="foreign">x</xhtml:div></foreignObject>
            </svg>"""
        )
        result = merge_svgs([doc])
        styles = [
            elem.text
            for elem in result.root.iter()
            if isinstance(elem.tag, str) and elem.tag.endswith("style")
        ]

        assert "@keyframes pathy-panel-0--keyframe--a-b " in styles[0]
        assert "@keyframes pathy-panel-0--keyframe--a-b--duplicate-1" in styles[0]
        assert "#pathy-panel-0 .foreign" in styles[1]

    def test_composed_animation_provenance_remains_replaceable(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
            '<path id="region" d="M0 0h1v1z"/></svg>'
        ).animate(effect="pulse")
        composed = merge_svgs([doc, doc])
        replaced = composed.animate(effect="blink")
        serialized = replaced.to_string()

        assert serialized.count('data-pathy-animation="true"') == 1
        assert "--keyframe--pathy-pulse-" not in serialized
        assert "@keyframes pathy-blink-" in serialized

    def test_namespace_qualified_root_selectors_target_nested_svg(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
            "<style>@namespace s url(http://www.w3.org/2000/svg); "
            "s|svg:root, *|svg:root {fill:red}</style></svg>"
        )
        css = merge_svgs([doc]).root.find(".//{http://www.w3.org/2000/svg}style").text

        assert "@namespace s" in css
        assert "s|svg:root" not in css
        assert "*|svg:root" not in css
        assert css.count("#pathy-panel-0 > svg") == 2

    def test_case_insensitive_idref_expansion_is_bounded(self):
        from pathy_svg.document import SVGDocument

        selectors = "".join(
            '[aria-labelledby="shape shape shape shape shape shape shape" i]'
            for _ in range(1)
        )
        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
            f"<style>{selectors} {{fill:red}}</style>"
            '<title id="shape"/><title id="Shape"/></svg>'
        )

        with pytest.raises(ValueError, match="expansion exceeds 64 variants"):
            merge_svgs([doc, doc])

    def test_unresolved_fragment_suffix_allocation_is_linear(self):
        import time

        from pathy_svg.document import SVGDocument

        uses = "".join(f'<use href="#{" " * size}"/>' for size in range(1, 400))
        doc = SVGDocument.from_string(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">{uses}</svg>'
        )

        started = time.perf_counter()
        result = merge_svgs([doc])
        elapsed = time.perf_counter() - started

        hrefs = [
            elem.get("href")
            for elem in result.root.iter()
            if isinstance(elem.tag, str) and elem.tag.endswith("use")
        ]
        assert len(hrefs) == len(set(hrefs))
        assert elapsed < 3.0

    def test_duplicate_id_suffix_planning_is_linear(self):
        import time

        from pathy_svg._composition import plan_svg_panels
        from pathy_svg.document import SVGDocument

        paths = '<path id="same"/>' * 8000
        root = SVGDocument.from_string(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">{paths}</svg>'
        ).root

        started = time.perf_counter()
        plan = plan_svg_panels([root])[0]
        elapsed = time.perf_counter() - started
        planned_ids = [new_id for _, new_id in plan.descendant_ids]

        assert len(planned_ids) == len(set(planned_ids)) == 8000
        assert planned_ids[-1] == "pathy-panel-0--same--duplicate-7999"
        assert elapsed < 3.0

    def test_css_rewriting_handles_escapes_flags_idrefs_and_literals(self):
        from pathy_svg.document import SVGDocument

        source = SVGDocument.from_string(
            r"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">
              <defs>
                <linearGradient id="paint"/>
                <style>
                  /* url(#paint) #shape\.one\:two */
                  #shape\.one\:two,
                  [id="shape\2e one\:two" i],
                  [href="#shape.one:two" s],
                  [aria-labelledby~="title.one" i] {
                    fill: url(#paint);
                    content: "url(#paint) #shape\.one\:two";
                  }
                </style>
              </defs>
              <title id="title.one">Title</title>
              <path id="shape.one:two" aria-labelledby="title.one"/>
            </svg>"""
        )
        result = merge_svgs([source, source])
        ns = {"svg": "http://www.w3.org/2000/svg"}

        for index in range(2):
            prefix = f"pathy-panel-{index}"
            panel = result.root.xpath(
                f"./svg:g[@data-panel-index='{index}']", namespaces=ns
            )[0]
            css = panel.xpath(".//svg:style", namespaces=ns)[0].text

            assert f"#{prefix}--shape\\.one\\:two" in css
            assert f'[id="{prefix}--shape.one:two" i]' in css
            assert f'[href="#{prefix}--shape.one:two" s]' in css
            assert f'[aria-labelledby~="{prefix}--title.one" i]' in css
            assert f"fill: url(#{prefix}--paint)" in css
            assert "/* url(#paint) #shape\\.one\\:two */" in css
            assert 'content: "url(#paint) #shape\\.one\\:two"' in css

    def test_namespaces_ids_and_rewrites_panel_local_references(self):
        from lxml import etree

        from pathy_svg.document import SVGDocument

        source = SVGDocument.from_string(self.SVG_WITH_REFERENCES)
        before = source.to_string()
        result = merge_svgs([source, source])
        root = result.root

        ids = [elem.get("id") for elem in root.xpath(".//*[@id]")]
        assert len(ids) == len(set(ids))
        assert "pathy-panel-0--shape" in ids
        assert "pathy-panel-1--shape" in ids

        ns = {"svg": "http://www.w3.org/2000/svg"}
        xlink_href = "{http://www.w3.org/1999/xlink}href"
        for index in range(2):
            prefix = f"pathy-panel-{index}"
            panel = root.xpath(f".//svg:g[@id='{prefix}']", namespaces=ns)[0]
            path = panel.xpath(f".//svg:path[@id='{prefix}--shape']", namespaces=ns)[0]
            use = panel.xpath(f".//svg:use[@id='{prefix}--instance']", namespaces=ns)[0]
            animation = panel.xpath(
                f".//svg:animate[@id='{prefix}--animation']", namespaces=ns
            )[0]
            style = panel.xpath(".//svg:style", namespaces=ns)[0].text

            assert path.get("fill") == f"url(#{prefix}--paint)"
            assert path.get("clip-path") == f"url(#{prefix}--clip)"
            assert path.get("style") == f"mask:url(#{prefix}--mask)"
            assert path.get("aria-labelledby") == (
                f"{prefix}--label {prefix}--description"
            )
            assert use.get("href") == f"#{prefix}--shape"
            assert use.get(xlink_href) == f"#{prefix}--shape"
            assert animation.get("begin") == (
                f"{prefix}--shape.click; {prefix}--instance.end"
            )
            assert f"#{prefix}--shape" in style
            assert f'[id="{prefix}--shape"]' in style
            assert f'[href="#{prefix}--shape"]' in style
            assert f"url(#{prefix}--paint)" in style
            assert f"url('#{prefix}--clip')" in style

        assert source.to_string() == before
        reparsed = etree.fromstring(result.to_string().encode())
        assert reparsed.tag == "{http://www.w3.org/2000/svg}svg"

    def test_serialized_result_is_valid_xml(self):
        from pathy_svg.document import SVGDocument

        a, b = self._docs()
        svg_str = merge_svgs([a, b]).to_string()

        reparsed = SVGDocument.from_string(svg_str)
        assert reparsed.root.tag == "{http://www.w3.org/2000/svg}svg"
        assert svg_str.count('xmlns="http://www.w3.org/2000/svg"') == 1


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

    def test_namespace_rebuild_preserves_subclass_and_isolates_custom_state(self):
        from pathy_svg.document import SVGDocument

        class CustomDocument(SVGDocument):
            __slots__ = ("slot_state",)
            init_calls = 0

            def __init__(self, tree):
                type(self).init_calls += 1
                super().__init__(tree)
                self.slot_state = ["initialized"]
                self.dict_state = {"history": ["initialized"]}

        doc = CustomDocument.from_string(self.INKSCAPE_SVG)
        doc.slot_state.append("source")
        doc.dict_state["history"].append("source")

        result = strip_metadata(doc)

        assert isinstance(result, CustomDocument)
        assert CustomDocument.init_calls == 1
        assert result.slot_state == ["initialized", "source"]
        assert result.slot_state is not doc.slot_state
        assert result.dict_state == {"history": ["initialized", "source"]}
        assert result.dict_state is not doc.dict_state
        assert result.dict_state["history"] is not doc.dict_state["history"]
        result_svg = result.to_string()
        assert "inkscape" not in result_svg
        assert "sodipodi" not in result_svg

        result.slot_state.append("result")
        result.dict_state["history"].append("result")
        assert doc.slot_state == ["initialized", "source"]
        assert doc.dict_state == {"history": ["initialized", "source"]}

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


class TestDeprecatedUtilsModule:
    def test_import_emits_deprecation_warning(self):
        import importlib

        with pytest.warns(DeprecationWarning, match="pathy_svg.utils is deprecated"):
            importlib.import_module("pathy_svg.utils")

    def test_re_exports_hex_to_rgb(self):
        import pathy_svg.utils as deprecated
        from pathy_svg.color import hex_to_rgb

        assert deprecated.hex_to_rgb is hex_to_rgb

    def test_re_exports_normalize_values(self):
        import pathy_svg.utils as deprecated
        from pathy_svg.data import normalize_values

        assert deprecated.normalize_values is normalize_values

    def test_re_exports_viewbox_to_pixel(self):
        import pathy_svg.utils as deprecated
        from pathy_svg.svg_tools import viewbox_to_pixel

        assert deprecated.viewbox_to_pixel is viewbox_to_pixel


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
            "compose_svgs",
            "merge_svgs",
            "strip_metadata",
            "optimize_svg",
            "extract_styles",
        ]:
            assert hasattr(pathy_svg, name), f"Missing from pathy_svg: {name}"


class TestCompositionResult:
    def test_public_result_and_error_types_are_top_level_exports(self):
        import pathy_svg

        for name in ("CompositionError", "CompositionResult", "PanelComposition"):
            assert name in pathy_svg.__all__
            assert hasattr(pathy_svg, name)

    def test_public_result_annotations_are_runtime_resolvable(self):
        from typing import get_type_hints

        from pathy_svg.composition import CompositionResult, PanelComposition
        from pathy_svg.document import SVGDocument

        assert get_type_hints(CompositionResult)["document"] is SVGDocument
        assert get_type_hints(PanelComposition)["id_map"] is not None

    def test_validation_errors_remain_value_error_compatible(self):
        from pathy_svg.exceptions import (
            CompositionError,
            DataMappingError,
            PathySVGError,
            ValidationError,
        )

        for error in (CompositionError, DataMappingError, ValidationError):
            assert issubclass(error, PathySVGError)
            assert issubclass(error, ValueError)

    def test_exposes_per_panel_id_mappings_without_mutating_inputs(self):
        from pathy_svg.composition import CompositionResult, PanelComposition
        from pathy_svg.document import SVGDocument

        first = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
            '<path id="shared"/></svg>'
        )
        second = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
            '<path id="shared"/></svg>'
        )
        before = (first.to_bytes(), second.to_bytes())

        result = compose_svgs([first, second])

        assert isinstance(result, CompositionResult)
        assert isinstance(result.panel(0), PanelComposition)
        assert isinstance(result.document, SVGDocument)
        assert result.panel(0).wrapper_id == "pathy-panel-0"
        assert result.panel(0).output_id("shared") == "pathy-panel-0--shared"
        assert result.panel(1).output_id("shared") == "pathy-panel-1--shared"
        assert result.document._find_by_id("pathy-panel-0--shared") is not None
        assert (first.to_bytes(), second.to_bytes()) == before

    def test_panel_mapping_is_read_only(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
            '<path id="region"/></svg>'
        )
        panel = compose_svgs([doc]).panel(0)

        with pytest.raises(TypeError):
            panel.id_map["region"] = "changed"

    def test_unique_ids_are_reported_unchanged(self):
        from pathy_svg.document import SVGDocument

        doc = SVGDocument.from_string(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
            '<path id="region"/></svg>'
        )

        result = compose_svgs([doc])

        assert result.panel(0).id_map == {"region": "region"}

    def test_empty_composition_uses_public_exception(self):
        from pathy_svg.exceptions import CompositionError

        with pytest.raises(CompositionError):
            compose_svgs([])
