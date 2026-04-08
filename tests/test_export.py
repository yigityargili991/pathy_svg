"""Tests for pathy_svg.export module."""

import pytest

try:
    import cairosvg  # noqa: F401

    HAS_CAIRO = True
except (ImportError, OSError):
    HAS_CAIRO = False

pytestmark = pytest.mark.skipif(not HAS_CAIRO, reason="cairosvg/libcairo not available")

from pathy_svg.document import SVGDocument


class TestPNGExport:
    def test_to_png_bytes(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        data = doc.to_png()
        assert isinstance(data, bytes)
        assert data[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic bytes

    def test_to_png_file(self, simple_svg_path, tmp_path):
        doc = SVGDocument.from_file(simple_svg_path)
        out = tmp_path / "test.png"
        result = doc.to_png(out)
        assert result is None
        assert out.exists()
        assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

    def test_to_png_with_width(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        data = doc.to_png(width=200)
        assert isinstance(data, bytes)

    def test_heatmap_then_png(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        result = doc.heatmap({"stomach": 0.5, "liver": 0.8})
        data = result.to_png()
        assert isinstance(data, bytes)


class TestPDFExport:
    def test_to_pdf_bytes(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        data = doc.to_pdf()
        assert isinstance(data, bytes)
        assert b"%PDF" in data[:20]

    def test_to_pdf_file(self, simple_svg_path, tmp_path):
        doc = SVGDocument.from_file(simple_svg_path)
        out = tmp_path / "test.pdf"
        doc.to_pdf(out)
        assert out.exists()


class TestJPEGExport:
    def test_to_jpeg_bytes(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        data = doc.to_jpeg()
        assert isinstance(data, bytes)
        assert data[:2] == b"\xff\xd8"  # JPEG magic bytes

    def test_to_jpeg_file(self, simple_svg_path, tmp_path):
        doc = SVGDocument.from_file(simple_svg_path)
        out = tmp_path / "test.jpg"
        doc.to_jpeg(out)
        assert out.exists()
