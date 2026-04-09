"""Mixin for raster export and Jupyter display methods."""

from __future__ import annotations


class ExportMixin:
    """PNG, PDF, JPEG export and Jupyter display methods."""

    __slots__ = ()

    def to_png(self, path=None, **kwargs) -> bytes | None:
        """Export to PNG. Requires pathy-svg[export].

        Args:
            path: File path to save the PNG to. If None, returns the PNG bytes.
            **kwargs: Additional parameters passed to `cairosvg.svg2png`.

        Returns:
            The exported PNG as bytes if `path` is None, otherwise `None`.
        """
        from pathy_svg.export import to_png

        return to_png(self, path, **kwargs)

    def to_pdf(self, path=None) -> bytes | None:
        """Export to PDF. Requires pathy-svg[export].

        Args:
            path: File path to save the PDF to. If None, returns the PDF bytes.

        Returns:
            The exported PDF as bytes if `path` is None, otherwise `None`.
        """
        from pathy_svg.export import to_pdf

        return to_pdf(self, path)

    def to_jpeg(self, path=None, **kwargs) -> bytes | None:
        """Export to JPEG. Requires pathy-svg[export].

        Args:
            path: File path to save the JPEG to. If None, returns the JPEG bytes.
            **kwargs: Additional parameters passed to `cairosvg.svg2png` and Pillow `Image.save`.

        Returns:
            The exported JPEG as bytes if `path` is None, otherwise `None`.
        """
        from pathy_svg.export import to_jpeg

        return to_jpeg(self, path, **kwargs)

    def thumbnail(self, **kwargs):
        """Return a PIL Image thumbnail. Requires pathy-svg[export].

        Args:
            **kwargs: Arguments passed to PIL Image.thumbnail (e.g. `size`).

        Returns:
            A PIL Image representing the SVG.
        """
        from pathy_svg.export import thumbnail

        return thumbnail(self, **kwargs)

    def show(self, **kwargs):
        """Display in Jupyter. Requires pathy-svg[full].

        Args:
            **kwargs: Additional arguments passed to IPython display.
        """
        from pathy_svg.export import show

        show(self, **kwargs)
