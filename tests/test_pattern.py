"""Tests for pathy_svg.pattern module."""

from lxml import etree

from pathy_svg.pattern import PatternSpec, CustomPatternSpec, apply_pattern_fill
from pathy_svg.document import SVGDocument


def _make_tree():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<path id="a" d="M 0 0 L 50 50 Z" fill="#fff"/>'
        '<path id="b" d="M 10 10 L 60 60 Z" fill="#fff"/>'
        "</svg>"
    )
    return etree.ElementTree(etree.fromstring(svg.encode()))


def _make_grouped_tree():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<g id="grp"><path id="c1" d="M 0 0 L 50 50 Z" fill="#fff"/>'
        '<path id="c2" d="M 10 10 L 60 60 Z" fill="#fff"/></g>'
        "</svg>"
    )
    return etree.ElementTree(etree.fromstring(svg.encode()))


class TestPatternSpec:
    def test_defaults(self):
        spec = PatternSpec(kind="crosshatch")
        assert spec.color == "#000000"
        assert spec.background is None
        assert spec.spacing == 6.0
        assert spec.thickness == 1.0

    def test_custom_values(self):
        spec = PatternSpec(kind="dots", color="#ff0000", spacing=10.0, thickness=2.0)
        assert spec.color == "#ff0000"
        assert spec.spacing == 10.0


class TestCustomPatternSpec:
    def test_defaults(self):
        spec = CustomPatternSpec(markup='<circle cx="5" cy="5" r="3"/>')
        assert spec.kind == "custom"
        assert spec.width == 10.0
        assert spec.height == 10.0


class TestApplyPatternFill:
    def test_creates_pattern_in_defs(self):
        tree = _make_tree()
        apply_pattern_fill(tree, {"a": PatternSpec(kind="crosshatch")})

        svg_str = etree.tostring(tree, encoding="unicode")
        assert "<pattern" in svg_str or "pattern" in svg_str

    def test_element_fill_references_pattern(self):
        tree = _make_tree()
        apply_pattern_fill(tree, {"a": PatternSpec(kind="dots")})

        ns = "{http://www.w3.org/2000/svg}"
        elem = tree.getroot().find(f".//{ns}path[@id='a']")
        fill = elem.get("fill", "")
        assert fill.startswith("url(#pathy-pat-")

    def test_string_shorthand(self):
        tree = _make_tree()
        apply_pattern_fill(tree, {"a": "crosshatch"})

        ns = "{http://www.w3.org/2000/svg}"
        elem = tree.getroot().find(f".//{ns}path[@id='a']")
        assert elem.get("fill", "").startswith("url(#pathy-pat-")

    def test_horizontal_lines_pattern(self):
        tree = _make_tree()
        apply_pattern_fill(tree, {"a": PatternSpec(kind="horizontal_lines")})

        ns = "{http://www.w3.org/2000/svg}"
        pattern = tree.getroot().find(f".//{ns}pattern")
        lines = pattern.findall(f"{ns}line")
        assert len(lines) == 1
        assert lines[0].get("x1") == "0"
        assert lines[0].get("x2") is not None

    def test_vertical_lines_pattern(self):
        tree = _make_tree()
        apply_pattern_fill(tree, {"a": PatternSpec(kind="vertical_lines")})

        ns = "{http://www.w3.org/2000/svg}"
        pattern = tree.getroot().find(f".//{ns}pattern")
        lines = pattern.findall(f"{ns}line")
        assert len(lines) == 1

    def test_diagonal_lines_pattern(self):
        tree = _make_tree()
        apply_pattern_fill(tree, {"a": PatternSpec(kind="diagonal_lines")})

        ns = "{http://www.w3.org/2000/svg}"
        pattern = tree.getroot().find(f".//{ns}pattern")
        lines = pattern.findall(f"{ns}line")
        assert len(lines) >= 1

    def test_crosshatch_pattern(self):
        tree = _make_tree()
        apply_pattern_fill(tree, {"a": PatternSpec(kind="crosshatch")})

        ns = "{http://www.w3.org/2000/svg}"
        pattern = tree.getroot().find(f".//{ns}pattern")
        lines = pattern.findall(f"{ns}line")
        assert len(lines) == 2

    def test_diagonal_crosshatch_pattern(self):
        tree = _make_tree()
        apply_pattern_fill(tree, {"a": PatternSpec(kind="diagonal_crosshatch")})

        ns = "{http://www.w3.org/2000/svg}"
        pattern = tree.getroot().find(f".//{ns}pattern")
        lines = pattern.findall(f"{ns}line")
        assert len(lines) == 2

    def test_dots_pattern(self):
        tree = _make_tree()
        apply_pattern_fill(tree, {"a": PatternSpec(kind="dots")})

        ns = "{http://www.w3.org/2000/svg}"
        pattern = tree.getroot().find(f".//{ns}pattern")
        circles = pattern.findall(f"{ns}circle")
        assert len(circles) == 1

    def test_background_color(self):
        tree = _make_tree()
        apply_pattern_fill(tree, {"a": PatternSpec(kind="dots", background="#eeeeee")})

        ns = "{http://www.w3.org/2000/svg}"
        pattern = tree.getroot().find(f".//{ns}pattern")
        rects = pattern.findall(f"{ns}rect")
        assert len(rects) == 1
        assert rects[0].get("fill") == "#eeeeee"

    def test_custom_pattern_markup(self):
        tree = _make_tree()
        spec = CustomPatternSpec(
            markup='<circle xmlns="http://www.w3.org/2000/svg" cx="5" cy="5" r="3" fill="red"/>',
            width=10,
            height=10,
        )
        apply_pattern_fill(tree, {"a": spec})

        ns = "{http://www.w3.org/2000/svg}"
        pattern = tree.getroot().find(f".//{ns}pattern")
        assert pattern is not None
        assert pattern.get("width") == "10"

    def test_multiple_elements(self):
        tree = _make_tree()
        apply_pattern_fill(tree, {
            "a": "crosshatch",
            "b": PatternSpec(kind="dots"),
        })

        svg_str = etree.tostring(tree, encoding="unicode")
        # Two patterns should be created
        ns = "{http://www.w3.org/2000/svg}"
        patterns = tree.getroot().findall(f".//{ns}pattern")
        assert len(patterns) == 2

    def test_nonexistent_id_skipped(self):
        tree = _make_tree()
        apply_pattern_fill(tree, {"nonexistent": "dots"})
        ns = "{http://www.w3.org/2000/svg}"
        patterns = tree.getroot().findall(f".//{ns}pattern")
        assert len(patterns) == 0

    def test_group_pattern(self):
        tree = _make_grouped_tree()
        apply_pattern_fill(tree, {"grp": "crosshatch"})

        ns = "{http://www.w3.org/2000/svg}"
        c1 = tree.getroot().find(f".//{ns}path[@id='c1']")
        c2 = tree.getroot().find(f".//{ns}path[@id='c2']")
        assert c1.get("fill", "").startswith("url(#pathy-pat-")
        assert c2.get("fill", "").startswith("url(#pathy-pat-")

    def test_opacity(self):
        tree = _make_tree()
        apply_pattern_fill(tree, {"a": "dots"}, opacity=0.5)

        ns = "{http://www.w3.org/2000/svg}"
        elem = tree.getroot().find(f".//{ns}path[@id='a']")
        assert elem.get("fill-opacity") == "0.5"
