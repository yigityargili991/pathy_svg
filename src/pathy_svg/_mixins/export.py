"""Mixin for raster export and Jupyter display methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast, overload

if TYPE_CHECKING:
    from os import PathLike

    from PIL.Image import Image

    from pathy_svg.document import SVGDocument


class ExportMixin:
    """PNG, PDF, JPEG export and Jupyter display methods."""

    __slots__ = ()

    @overload
    def to_png(
        self,
        path: None = None,
        *,
        width: int | None = None,
        height: int | None = None,
        dpi: int = 96,
    ) -> bytes: ...

    @overload
    def to_png(
        self,
        path: str | PathLike,
        *,
        width: int | None = None,
        height: int | None = None,
        dpi: int = 96,
    ) -> None: ...

    def to_png(
        self,
        path: str | PathLike | None = None,
        *,
        width: int | None = None,
        height: int | None = None,
        dpi: int = 96,
    ) -> bytes | None:
        """Export to PNG. Requires pathy-svg[export].

        Args:
            path: File path to save the PNG to. If None, returns the PNG bytes.
            width: Optional output width in pixels.
            height: Optional output height in pixels.
            dpi: Rasterization resolution.

        Returns:
            The exported PNG as bytes if `path` is None, otherwise `None`.
        """
        from pathy_svg.export import to_png

        doc = cast("SVGDocument", self)
        if path is None:
            return to_png(doc, width=width, height=height, dpi=dpi)
        to_png(doc, path, width=width, height=height, dpi=dpi)
        return None

    @overload
    def to_pdf(self, path: None = None) -> bytes: ...

    @overload
    def to_pdf(self, path: str | PathLike) -> None: ...

    def to_pdf(self, path: str | PathLike | None = None) -> bytes | None:
        """Export to PDF. Requires pathy-svg[export].

        Args:
            path: File path to save the PDF to. If None, returns the PDF bytes.

        Returns:
            The exported PDF as bytes if `path` is None, otherwise `None`.
        """
        from pathy_svg.export import to_pdf

        doc = cast("SVGDocument", self)
        if path is None:
            return to_pdf(doc)
        to_pdf(doc, path)
        return None

    @overload
    def to_jpeg(
        self,
        path: None = None,
        *,
        quality: int = 90,
        width: int | None = None,
        height: int | None = None,
        dpi: int = 96,
    ) -> bytes: ...

    @overload
    def to_jpeg(
        self,
        path: str | PathLike,
        *,
        quality: int = 90,
        width: int | None = None,
        height: int | None = None,
        dpi: int = 96,
    ) -> None: ...

    def to_jpeg(
        self,
        path: str | PathLike | None = None,
        *,
        quality: int = 90,
        width: int | None = None,
        height: int | None = None,
        dpi: int = 96,
    ) -> bytes | None:
        """Export to JPEG. Requires pathy-svg[export].

        Args:
            path: File path to save the JPEG to. If None, returns the JPEG bytes.
            quality: JPEG quality from 1 to 100.
            width: Optional output width in pixels.
            height: Optional output height in pixels.
            dpi: Rasterization resolution.

        Returns:
            The exported JPEG as bytes if `path` is None, otherwise `None`.
        """
        from pathy_svg.export import to_jpeg

        doc = cast("SVGDocument", self)
        if path is None:
            return to_jpeg(
                doc,
                quality=quality,
                width=width,
                height=height,
                dpi=dpi,
            )
        to_jpeg(
            doc,
            path,
            quality=quality,
            width=width,
            height=height,
            dpi=dpi,
        )
        return None

    def thumbnail(self, *, width: int = 300) -> Image:
        """Return a PIL Image thumbnail. Requires pathy-svg[export].

        Args:
            width: Thumbnail width in pixels.

        Returns:
            A PIL Image representing the SVG.
        """
        from pathy_svg.export import thumbnail

        return thumbnail(cast("SVGDocument", self), width=width)

    def show(self, *, width: int | None = None) -> None:
        """Display in Jupyter. Requires pathy-svg[full].

        Args:
            width: Optional maximum display width in pixels.
        """
        from pathy_svg.export import show

        show(cast("SVGDocument", self), width=width)
