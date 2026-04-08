"""Tests for pathy_svg.inspect module."""

import pytest

from pathy_svg.document import SVGDocument


class TestInspectPaths:
    def test_returns_path_info(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        infos = doc.inspect_paths()
        ids = [p.id for p in infos]
        assert "stomach" in ids
        assert "liver" in ids
        assert "heart" in ids

    def test_path_info_fields(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        infos = doc.inspect_paths()
        stomach = next(p for p in infos if p.id == "stomach")
        assert stomach.tag == "path"
        assert stomach.fill == "#ffffff"
        assert stomach.stroke == "#333333"
        assert stomach.bbox is not None
        assert stomach.d_length is not None
        assert stomach.parent_group == "organs"

    def test_rect_included(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        infos = doc.inspect_paths()
        border = next((p for p in infos if p.id == "border"), None)
        assert border is not None
        assert border.tag == "rect"

    def test_styled_svg(self, styled_svg_path):
        doc = SVGDocument.from_file(styled_svg_path)
        infos = doc.inspect_paths()
        region_a = next(p for p in infos if p.id == "region_a")
        assert region_a.fill == "#aaaaaa"
        assert region_a.stroke == "#000000"

    def test_grouped_svg(self, grouped_svg_path):
        doc = SVGDocument.from_file(grouped_svg_path)
        infos = doc.inspect_paths()
        north_a = next(p for p in infos if p.id == "north_a")
        assert north_a.parent_group == "north"


class TestValidateIds:
    def test_all_matched(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.validate_ids(["stomach", "liver", "heart"])
        assert result.is_valid
        assert len(result.matched) == 3
        assert len(result.unmatched) == 0

    def test_some_unmatched(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.validate_ids(["stomach", "typo_organ", "missing"])
        assert not result.is_valid
        assert "stomach" in result.matched
        assert "typo_organ" in result.unmatched
        assert "missing" in result.unmatched

    def test_unused_reported(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.validate_ids(["stomach"])
        assert len(result.unused) > 0
        assert "liver" in result.unused

    def test_empty_ids(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.validate_ids([])
        assert result.is_valid
        assert len(result.unused) > 0


class TestXYGuide:
    def test_returns_new_doc(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        guide = doc.xy_guide()
        assert guide is not doc

    def test_has_guide_group(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        guide = doc.xy_guide()
        g = guide._find_by_id("pathy-guide")
        assert g is not None

    def test_guide_has_lines(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        guide = doc.xy_guide(step=100)
        g = guide._find_by_id("pathy-guide")
        lines = g.findall(".//{http://www.w3.org/2000/svg}line")
        assert len(lines) > 0

    def test_custom_color(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        guide = doc.xy_guide(color="blue")
        g = guide._find_by_id("pathy-guide")
        assert "blue" in g.get("style", "")
