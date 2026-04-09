"""Legend builder — gradient, discrete, and categorical legends injected as SVG elements."""

from __future__ import annotations

import uuid

from lxml import etree

from pathy_svg.themes import ColorScale
from pathy_svg.transform import ViewBox


SVG_NS = "http://www.w3.org/2000/svg"


def _ns_elem(parent: etree._Element, tag: str) -> etree._Element:
    """Create a namespaced SVG sub-element."""
    ns = parent.nsmap.get(None, SVG_NS)
    return etree.SubElement(parent, f"{{{ns}}}{tag}" if ns else tag)


def build_gradient_legend(
    scale: ColorScale,
    viewbox: ViewBox,
    *,
    position: tuple[float, float] = (0.85, 0.1),
    size: tuple[float, float] = (0.04, 0.4),
    direction: str = "vertical",
    num_ticks: int = 5,
    tick_format: str = "{:.2f}",
    labels: list[str] | None = None,
    font_size: float | None = None,
    font_color: str = "black",
    font_family: str = "sans-serif",
    title: str | None = None,
    title_size: float | None = None,
    border: bool = False,
    border_color: str = "#333",
    background: str | None = None,
    padding: float = 5,
    parent_ns: dict | None = None,
) -> etree._Element:
    """Build a gradient legend as an SVG <g> element."""
    # Calculate pixel positions from fractional coords
    x = viewbox.x + position[0] * viewbox.width
    y = viewbox.y + position[1] * viewbox.height
    w = size[0] * viewbox.width
    h = size[1] * viewbox.height

    if direction == "horizontal":
        w, h = h, w  # swap for horizontal

    uid = uuid.uuid4().hex[:8]

    # Create group
    g = etree.Element(f"{{{SVG_NS}}}g", id="pathy-legend")

    # Optional background
    if background:
        bg = _sub(g, "rect")
        bg.set("x", str(x - padding))
        bg.set("y", str(y - padding - (20 if title else 0)))
        bg.set("width", str(w + padding * 2 + 60))
        bg.set("height", str(h + padding * 2 + (20 if title else 0)))
        bg.set("fill", background)
        bg.set("rx", "3")

    # Gradient definition
    defs = _sub(g, "defs")

    if direction == "vertical":
        grad = etree.SubElement(defs, f"{{{SVG_NS}}}linearGradient", id=f"pathy-grad-{uid}")
        grad.set("x1", "0")
        grad.set("y1", "1")
        grad.set("x2", "0")
        grad.set("y2", "0")
    else:
        grad = etree.SubElement(defs, f"{{{SVG_NS}}}linearGradient", id=f"pathy-grad-{uid}")
        grad.set("x1", "0")
        grad.set("y1", "0")
        grad.set("x2", "1")
        grad.set("y2", "0")

    # Add color stops
    n_stops = 20
    vmin = float(scale._norm.vmin or 0) if hasattr(scale._norm, "vmin") else 0.0
    vmax = float(scale._norm.vmax or 1) if hasattr(scale._norm, "vmax") else 1.0
    for i in range(n_stops + 1):
        t = i / n_stops
        val = vmin + t * (vmax - vmin)
        color = scale(val)
        stop = etree.SubElement(grad, f"{{{SVG_NS}}}stop")
        stop.set("offset", f"{t:.3f}")
        stop.set("style", f"stop-color:{color}")

    # Color bar rect
    bar = _sub(g, "rect")
    bar.set("x", str(x))
    bar.set("y", str(y))
    bar.set("width", str(w))
    bar.set("height", str(h))
    bar.set("fill", f"url(#pathy-grad-{uid})")
    if border:
        bar.set("stroke", border_color)
        bar.set("stroke-width", "0.5")

    # Font size
    fs = font_size or max(6, min(14, viewbox.height * 0.025))
    ts = title_size or fs * 1.2

    # Tick labels
    if labels is None:
        if num_ticks < 1:
            raise ValueError("num_ticks must be at least 1")
        if num_ticks == 1:
            tick_values = [(vmin + vmax) / 2]
        else:
            tick_values = [vmin + i / (num_ticks - 1) * (vmax - vmin) for i in range(num_ticks)]
        labels = [tick_format.format(v) for v in tick_values]

    for i, label in enumerate(labels):
        t = i / (len(labels) - 1) if len(labels) > 1 else 0.5
        if direction == "vertical":
            tx = x + w + 4
            ty = y + h - t * h + fs / 3
        else:
            tx = x + t * w
            ty = y + h + fs + 2

        txt = _sub(g, "text")
        txt.set("x", str(tx))
        txt.set("y", str(ty))
        txt.set("style", f"fill:{font_color};font-size:{fs}px;font-family:{font_family}")
        txt.text = label

    # Title
    if title:
        ttl = _sub(g, "text")
        if direction == "vertical":
            ttl.set("x", str(x))
            ttl.set("y", str(y - 6))
        else:
            ttl.set("x", str(x))
            ttl.set("y", str(y - 6))
        ttl.set("style", f"fill:{font_color};font-size:{ts}px;font-family:{font_family};font-weight:bold")
        ttl.text = title

    return g


def build_discrete_legend(
    colors: list[str],
    labels: list[str],
    viewbox: ViewBox,
    *,
    position: tuple[float, float] = (0.85, 0.1),
    size: tuple[float, float] = (0.04, 0.4),
    direction: str = "vertical",
    font_size: float | None = None,
    font_color: str = "black",
    font_family: str = "sans-serif",
    title: str | None = None,
    title_size: float | None = None,
    border: bool = False,
    border_color: str = "#333",
) -> etree._Element:
    """Build a discrete/categorical legend as an SVG <g> element."""
    x = viewbox.x + position[0] * viewbox.width
    y = viewbox.y + position[1] * viewbox.height
    w = size[0] * viewbox.width
    total_h = size[1] * viewbox.height
    n = len(colors)
    swatch_h = total_h / n if n > 0 else total_h

    fs = font_size or max(6, min(14, viewbox.height * 0.025))
    ts = title_size or fs * 1.2

    g = etree.Element(f"{{{SVG_NS}}}g", id="pathy-legend")

    if title:
        ttl = _sub(g, "text")
        ttl.set("x", str(x))
        ttl.set("y", str(y - 6))
        ttl.set("style", f"fill:{font_color};font-size:{ts}px;font-family:{font_family};font-weight:bold")
        ttl.text = title

    for i, (color, label) in enumerate(zip(colors, labels)):
        sy = y + i * swatch_h

        rect = _sub(g, "rect")
        rect.set("x", str(x))
        rect.set("y", str(sy))
        rect.set("width", str(w))
        rect.set("height", str(swatch_h))
        rect.set("fill", color)
        if border:
            rect.set("stroke", border_color)
            rect.set("stroke-width", "0.5")

        txt = _sub(g, "text")
        txt.set("x", str(x + w + 4))
        txt.set("y", str(sy + swatch_h / 2 + fs / 3))
        txt.set("style", f"fill:{font_color};font-size:{fs}px;font-family:{font_family}")
        txt.text = label

    return g


def _sub(parent: etree._Element, tag: str) -> etree._Element:
    """Create a namespaced SVG sub-element."""
    return etree.SubElement(parent, f"{{{SVG_NS}}}{tag}")
