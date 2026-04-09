"""Tests for pathy_svg._css module."""

from pathy_svg._css import set_style_property, style_property


class TestStyleProperty:
    def test_returns_none_for_none_style(self):
        assert style_property(None, "fill") is None

    def test_returns_none_for_empty_style(self):
        assert style_property("", "fill") is None

    def test_single_property(self):
        assert style_property("fill:#ff0000", "fill") == "#ff0000"

    def test_property_among_multiple(self):
        assert style_property("fill:#ff0000;stroke:black;opacity:0.5", "stroke") == "black"

    def test_first_property(self):
        assert style_property("fill:#ff0000;stroke:black", "fill") == "#ff0000"

    def test_last_property(self):
        assert style_property("fill:#ff0000;stroke:black", "stroke") == "black"

    def test_missing_property(self):
        assert style_property("fill:#ff0000;stroke:black", "opacity") is None

    def test_whitespace_around_value(self):
        assert style_property("fill: #ff0000 ; stroke: black", "fill") == "#ff0000"

    def test_whitespace_around_colon(self):
        assert style_property("fill : red", "fill") == "red"

    def test_url_value(self):
        result = style_property("fill:url(#gradient1);stroke:black", "fill")
        assert result == "url(#gradient1)"

    def test_partial_name_no_match(self):
        assert style_property("fill-opacity:0.5", "fill") is None


class TestSetStyleProperty:
    def test_none_style_creates_new(self):
        assert set_style_property(None, "fill", "red") == "fill:red"

    def test_empty_style_creates_new(self):
        assert set_style_property("", "fill", "red") == "fill:red"

    def test_replaces_existing_property(self):
        result = set_style_property("fill:blue;stroke:black", "fill", "red")
        assert "fill:red" in result
        assert "fill:blue" not in result
        assert "stroke:black" in result

    def test_adds_missing_property(self):
        result = set_style_property("fill:red", "stroke", "black")
        assert "stroke:black" in result
        assert "fill:red" in result

    def test_replaces_last_property(self):
        result = set_style_property("fill:red;stroke:blue", "stroke", "green")
        assert "stroke:green" in result
        assert "stroke:blue" not in result

    def test_replaces_with_url_value(self):
        result = set_style_property("fill:red", "fill", "url(#grad)")
        assert "fill:url(#grad)" in result
