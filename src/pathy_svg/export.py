"""Export SVG to raster formats (PNG, PDF, JPEG) and Jupyter display."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pathy_svg._compat import require_cairosvg, require_ipython_display, require_pillow
from pathy_svg.exceptions import ExportError

if TYPE_CHECKING:
    from pathy_svg.document import SVGDocument


def to_png(
    doc: SVGDocument,
    path: str | Path | None = None,
    *,
    width: int | None = None,
    height: int | None = None,
    dpi: int = 96,
) -> bytes | None:
    """Render SVG to PNG. Returns bytes if path is None, else writes to file."""
    cairosvg = require_cairosvg()
    svg_bytes = doc.to_bytes()
    try:
        png_data = cairosvg.svg2png(
            bytestring=svg_bytes,
            output_width=width,
            output_height=height,
            dpi=dpi,
        )
    except Exception as exc:
        raise ExportError(f"PNG export failed: {exc}") from exc

    if path is not None:
        Path(path).write_bytes(png_data)
        return None
    return png_data


def to_pdf(
    doc: SVGDocument,
    path: str | Path | None = None,
) -> bytes | None:
    """Render SVG to PDF. Returns bytes if path is None, else writes to file."""
    cairosvg = require_cairosvg()
    svg_bytes = doc.to_bytes()
    try:
        pdf_data = cairosvg.svg2pdf(bytestring=svg_bytes)
    except Exception as exc:
        raise ExportError(f"PDF export failed: {exc}") from exc

    if path is not None:
        Path(path).write_bytes(pdf_data)
        return None
    return pdf_data


def to_jpeg(
    doc: SVGDocument,
    path: str | Path | None = None,
    *,
    quality: int = 90,
    width: int | None = None,
    height: int | None = None,
    dpi: int = 96,
) -> bytes | None:
    """Render SVG to JPEG via PNG intermediate. Returns bytes if path is None."""
    import io

    PIL = require_pillow()
    png_data = to_png(doc, width=width, height=height, dpi=dpi)

    img = PIL.Image.open(io.BytesIO(png_data))
    if img.mode == "RGBA":
        bg = PIL.Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    jpeg_data = buf.getvalue()

    if path is not None:
        Path(path).write_bytes(jpeg_data)
        return None
    return jpeg_data


def thumbnail(
    doc: SVGDocument,
    *,
    width: int = 300,
):
    """Return a PIL Image thumbnail of the SVG."""
    import io

    PIL = require_pillow()
    png_data = to_png(doc, width=width)
    return PIL.Image.open(io.BytesIO(png_data))


def show(doc: SVGDocument, *, width: int | None = None):
    """Display the SVG in a Jupyter notebook."""
    display_mod = require_ipython_display()
    svg_str = doc.to_string()
    if width:
        display_mod.display(display_mod.HTML(
            f'<div style="max-width:{width}px">{svg_str}</div>'
        ))
    else:
        display_mod.display(display_mod.SVG(data=svg_str))
