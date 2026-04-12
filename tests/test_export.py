"""Tests for pathy_svg.export module."""

import io
from unittest.mock import MagicMock, patch

import pytest

from pathy_svg.document import SVGDocument
from pathy_svg.exceptions import ExportError

try:
    import cairosvg  # noqa: F401

    HAS_CAIRO = True
except (ImportError, OSError):
    HAS_CAIRO = False


class TestExportMissingDependency:
    def test_png_raises_import_error_without_cairo(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        with patch(
            "pathy_svg._compat.importlib.import_module", side_effect=ImportError
        ):
            with pytest.raises(ImportError, match="pathy-svg"):
                doc.to_png()

    def test_pdf_raises_import_error_without_cairo(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        with patch(
            "pathy_svg._compat.importlib.import_module", side_effect=ImportError
        ):
            with pytest.raises(ImportError, match="pathy-svg"):
                doc.to_pdf()

    def test_jpeg_raises_import_error_without_cairo(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        with patch(
            "pathy_svg._compat.importlib.import_module", side_effect=ImportError
        ):
            with pytest.raises(ImportError, match="pathy-svg"):
                doc.to_jpeg()


@pytest.mark.skipif(not HAS_CAIRO, reason="cairosvg/libcairo not available")
class TestPNGExport:
    def test_to_png_bytes(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        data = doc.to_png()
        assert isinstance(data, bytes)
        assert data[:8] == b"\x89PNG\r\n\x1a\n"

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


@pytest.mark.skipif(not HAS_CAIRO, reason="cairosvg/libcairo not available")
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


@pytest.mark.skipif(not HAS_CAIRO, reason="cairosvg/libcairo not available")
class TestJPEGExport:
    def test_to_jpeg_bytes(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        data = doc.to_jpeg()
        assert isinstance(data, bytes)
        assert data[:2] == b"\xff\xd8"

    def test_to_jpeg_file(self, simple_svg_path, tmp_path):
        doc = SVGDocument.from_file(simple_svg_path)
        out = tmp_path / "test.jpg"
        doc.to_jpeg(out)
        assert out.exists()


class TestPNGExportMocked:
    def test_to_png_returns_bytes(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        fake_png = b"\x89PNG\r\n\x1a\nfake"
        mock_cairo = MagicMock()
        mock_cairo.svg2png.return_value = fake_png
        with patch("pathy_svg.export.require_cairosvg", return_value=mock_cairo):
            result = doc.to_png()
        assert result == fake_png

    def test_to_png_writes_file(self, simple_svg_path, tmp_path):
        doc = SVGDocument.from_file(simple_svg_path)
        fake_png = b"\x89PNG\r\n\x1a\nfake"
        mock_cairo = MagicMock()
        mock_cairo.svg2png.return_value = fake_png
        out = tmp_path / "out.png"
        with patch("pathy_svg.export.require_cairosvg", return_value=mock_cairo):
            result = doc.to_png(str(out))
        assert result is None
        assert out.read_bytes() == fake_png

    def test_to_png_raises_export_error(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        mock_cairo = MagicMock()
        mock_cairo.svg2png.side_effect = RuntimeError("cairo failed")
        with patch("pathy_svg.export.require_cairosvg", return_value=mock_cairo):
            with pytest.raises(ExportError, match="PNG export failed"):
                doc.to_png()

    def test_to_png_passes_dimensions(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        mock_cairo = MagicMock()
        mock_cairo.svg2png.return_value = b"\x89PNG"
        with patch("pathy_svg.export.require_cairosvg", return_value=mock_cairo):
            doc.to_png(width=300, height=200, dpi=150)
        mock_cairo.svg2png.assert_called_once()
        call_kwargs = mock_cairo.svg2png.call_args
        assert call_kwargs.kwargs["output_width"] == 300
        assert call_kwargs.kwargs["output_height"] == 200
        assert call_kwargs.kwargs["dpi"] == 150


class TestPDFExportMocked:
    def test_to_pdf_returns_bytes(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        fake_pdf = b"%PDF-1.4 fake"
        mock_cairo = MagicMock()
        mock_cairo.svg2pdf.return_value = fake_pdf
        with patch("pathy_svg.export.require_cairosvg", return_value=mock_cairo):
            result = doc.to_pdf()
        assert result == fake_pdf

    def test_to_pdf_writes_file(self, simple_svg_path, tmp_path):
        doc = SVGDocument.from_file(simple_svg_path)
        fake_pdf = b"%PDF-1.4 fake"
        mock_cairo = MagicMock()
        mock_cairo.svg2pdf.return_value = fake_pdf
        out = tmp_path / "out.pdf"
        with patch("pathy_svg.export.require_cairosvg", return_value=mock_cairo):
            result = doc.to_pdf(str(out))
        assert result is None
        assert out.read_bytes() == fake_pdf

    def test_to_pdf_raises_export_error(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        mock_cairo = MagicMock()
        mock_cairo.svg2pdf.side_effect = ValueError("bad svg")
        with patch("pathy_svg.export.require_cairosvg", return_value=mock_cairo):
            with pytest.raises(ExportError, match="PDF export failed"):
                doc.to_pdf()


class TestJPEGExportMocked:
    def _make_mock_png(self):
        from PIL import Image

        buf = io.BytesIO()
        img = Image.new("RGBA", (10, 10), (255, 0, 0, 255))
        img.save(buf, format="PNG")
        return buf.getvalue()

    def test_to_jpeg_returns_bytes(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        fake_png = self._make_mock_png()
        mock_cairo = MagicMock()
        mock_cairo.svg2png.return_value = fake_png
        with (
            patch("pathy_svg.export.require_cairosvg", return_value=mock_cairo),
            patch("pathy_svg.export.require_pillow", return_value=__import__("PIL")),
        ):
            data = doc.to_jpeg()
        assert data[:2] == b"\xff\xd8"

    def test_to_jpeg_writes_file(self, simple_svg_path, tmp_path):
        doc = SVGDocument.from_file(simple_svg_path)
        fake_png = self._make_mock_png()
        mock_cairo = MagicMock()
        mock_cairo.svg2png.return_value = fake_png
        out = tmp_path / "out.jpg"
        with (
            patch("pathy_svg.export.require_cairosvg", return_value=mock_cairo),
            patch("pathy_svg.export.require_pillow", return_value=__import__("PIL")),
        ):
            result = doc.to_jpeg(str(out))
        assert result is None
        assert out.read_bytes()[:2] == b"\xff\xd8"

    def test_to_jpeg_rgba_converts_to_rgb(self, simple_svg_path):
        from PIL import Image

        doc = SVGDocument.from_file(simple_svg_path)
        fake_png = self._make_mock_png()
        mock_cairo = MagicMock()
        mock_cairo.svg2png.return_value = fake_png
        with (
            patch("pathy_svg.export.require_cairosvg", return_value=mock_cairo),
            patch("pathy_svg.export.require_pillow", return_value=__import__("PIL")),
        ):
            data = doc.to_jpeg()
        img = Image.open(io.BytesIO(data))
        assert img.mode == "RGB"

    def test_to_jpeg_raises_on_no_png_data(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        mock_cairo = MagicMock()
        mock_cairo.svg2png.side_effect = RuntimeError("fail")
        with (
            patch("pathy_svg.export.require_cairosvg", return_value=mock_cairo),
            patch("pathy_svg.export.require_pillow", return_value=__import__("PIL")),
        ):
            with pytest.raises(ExportError, match="PNG export failed"):
                doc.to_jpeg()


class TestThumbnailMocked:
    def test_thumbnail_returns_pil_image(self, simple_svg_path):
        from PIL import Image

        doc = SVGDocument.from_file(simple_svg_path)
        fake_png = self._make_png_bytes()
        mock_cairo = MagicMock()
        mock_cairo.svg2png.return_value = fake_png
        with (
            patch("pathy_svg.export.require_cairosvg", return_value=mock_cairo),
            patch("pathy_svg.export.require_pillow", return_value=__import__("PIL")),
        ):
            img = doc.thumbnail(width=100)
        assert isinstance(img, Image.Image)

    def test_thumbnail_raises_on_no_data(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        mock_cairo = MagicMock()
        mock_cairo.svg2png.side_effect = RuntimeError("fail")
        with (
            patch("pathy_svg.export.require_cairosvg", return_value=mock_cairo),
            patch("pathy_svg.export.require_pillow", return_value=__import__("PIL")),
        ):
            with pytest.raises(ExportError, match="PNG export failed"):
                doc.thumbnail()

    def _make_png_bytes(self):
        from PIL import Image

        buf = io.BytesIO()
        img = Image.new("RGB", (10, 10), (0, 255, 0))
        img.save(buf, format="PNG")
        return buf.getvalue()


class TestShowMocked:
    def test_show_without_width(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        mock_display_mod = MagicMock()
        with patch(
            "pathy_svg.export.require_ipython_display", return_value=mock_display_mod
        ):
            doc.show()
        mock_display_mod.display.assert_called_once()
        assert mock_display_mod.SVG.called

    def test_show_with_width(self, simple_svg_path):
        doc = SVGDocument.from_file(simple_svg_path)
        mock_display_mod = MagicMock()
        with patch(
            "pathy_svg.export.require_ipython_display", return_value=mock_display_mod
        ):
            doc.show(width=500)
        mock_display_mod.display.assert_called_once()
        assert mock_display_mod.HTML.called


