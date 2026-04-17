"""Legend builder — gradient, discrete, and categorical legends injected as SVG elements."""

from __future__ import annotations

import uuid
from typing import Literal

from lxml import etree

from pathy_svg._constants import SVG_NS, svg_sub
from pathy_svg.themes import CategoricalPalette, ColorScale
from pathy_svg.transform import ViewBox

Direction = Literal["vertical", "horizontal"]
LegendKind = Literal["auto", "gradient", "discrete", "categorical"]


def build_gradient_legend(
    scale: ColorScale,
    viewbox: ViewBox,
    *,
    position: tuple[float, float] = (0.85, 0.1),
    size: tuple[float, float] = (0.04, 0.4),
    direction: Direction = "vertical",
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
        bg = svg_sub(g, "rect")
        bg.set("x", str(x - padding))
        bg.set("y", str(y - padding - (20 if title else 0)))
        bg.set("width", str(w + padding * 2 + 60))
        bg.set("height", str(h + padding * 2 + (20 if title else 0)))
        bg.set("fill", background)
        bg.set("rx", "3")

    # Gradient definition
    defs = svg_sub(g, "defs")

    if direction == "vertical":
        grad = etree.SubElement(
            defs, f"{{{SVG_NS}}}linearGradient", id=f"pathy-grad-{uid}"
        )
        grad.set("x1", "0")
        grad.set("y1", "1")
        grad.set("x2", "0")
        grad.set("y2", "0")
    else:
        grad = etree.SubElement(
            defs, f"{{{SVG_NS}}}linearGradient", id=f"pathy-grad-{uid}"
        )
        grad.set("x1", "0")
        grad.set("y1", "0")
        grad.set("x2", "1")
        grad.set("y2", "0")

    # Add color stops
    n_stops = 20
    vmin = scale.effective_vmin
    vmax = scale.effective_vmax
    for i in range(n_stops + 1):
        t = i / n_stops
        val = vmin + t * (vmax - vmin)
        color = scale(val)
        stop = etree.SubElement(grad, f"{{{SVG_NS}}}stop")
        stop.set("offset", f"{t:.3f}")
        stop.set("style", f"stop-color:{color}")

    # Color bar rect
    bar = svg_sub(g, "rect")
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
            tick_values = [
                vmin + i / (num_ticks - 1) * (vmax - vmin) for i in range(num_ticks)
            ]
        labels = [tick_format.format(v) for v in tick_values]

    for i, label in enumerate(labels):
        t = i / (len(labels) - 1) if len(labels) > 1 else 0.5
        if direction == "vertical":
            tx = x + w + 4
            ty = y + h - t * h + fs / 3
        else:
            tx = x + t * w
            ty = y + h + fs + 2

        txt = svg_sub(g, "text")
        txt.set("x", str(tx))
        txt.set("y", str(ty))
        txt.set(
            "style", f"fill:{font_color};font-size:{fs}px;font-family:{font_family}"
        )
        txt.text = label

    # Title
    if title:
        ttl = svg_sub(g, "text")
        ttl.set("x", str(x))
        ttl.set("y", str(y - 6))
        ttl.set(
            "style",
            f"fill:{font_color};font-size:{ts}px;font-family:{font_family};font-weight:bold",
        )
        ttl.text = title

    return g


def build_discrete_legend(
    colors: list[str],
    labels: list[str],
    viewbox: ViewBox,
    *,
    position: tuple[float, float] = (0.85, 0.1),
    size: tuple[float, float] = (0.04, 0.4),
    direction: Direction = "vertical",
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
        ttl = svg_sub(g, "text")
        ttl.set("x", str(x))
        ttl.set("y", str(y - 6))
        ttl.set(
            "style",
            f"fill:{font_color};font-size:{ts}px;font-family:{font_family};font-weight:bold",
        )
        ttl.text = title

    for i, (color, label) in enumerate(zip(colors, labels)):
        sy = y + i * swatch_h

        rect = svg_sub(g, "rect")
        rect.set("x", str(x))
        rect.set("y", str(sy))
        rect.set("width", str(w))
        rect.set("height", str(swatch_h))
        rect.set("fill", color)
        if border:
            rect.set("stroke", border_color)
            rect.set("stroke-width", "0.5")

        txt = svg_sub(g, "text")
        txt.set("x", str(x + w + 4))
        txt.set("y", str(sy + swatch_h / 2 + fs / 3))
        txt.set(
            "style", f"fill:{font_color};font-size:{fs}px;font-family:{font_family}"
        )
        txt.text = label

    return g


def resolve_legend_kind(
    kind: LegendKind,
    scale: ColorScale | None,
    cat_pal: CategoricalPalette | None,
) -> LegendKind:
    """Resolve ``"auto"`` to a concrete legend kind.

    Raises:
        ValueError: If ``kind="auto"`` and no prior coloring has been applied.
    """
    if kind != "auto":
        return kind
    if cat_pal is not None:
        return "categorical"
    if scale is None:
        raise ValueError(
            "Cannot auto-detect legend kind: no prior .heatmap() or "
            ".recolor_by_category() call. Pass kind='gradient', "
            "'discrete', or 'categorical' explicitly, or call a "
            "coloring method first."
        )
    if scale.breaks is not None:
        return "discrete"
    return "gradient"


def build_legend(
    kind: LegendKind,
    scale: ColorScale | None,
    cat_pal: CategoricalPalette | None,
    vb: ViewBox,
    *,
    position: tuple[float, float] = (0.85, 0.1),
    size: tuple[float, float] = (0.04, 0.4),
    direction: Direction = "vertical",
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
) -> etree._Element:
    """Dispatch to the appropriate legend builder.

    Args:
        kind: One of ``"gradient"``, ``"discrete"``, ``"categorical"``.
        scale: The ColorScale from a prior heatmap call, or None.
        cat_pal: The CategoricalPalette from a prior categorical call, or None.
        vb: The document's ViewBox.

    Returns:
        An SVG ``<g>`` element containing the legend.
    """
    shared = dict(
        position=position,
        size=size,
        direction=direction,
        font_size=font_size,
        font_color=font_color,
        font_family=font_family,
        title=title,
        title_size=title_size,
        border=border,
        border_color=border_color,
    )

    if kind == "gradient":
        if scale is None:
            raise ValueError(
                "Cannot build gradient legend without a ColorScale. "
                "Call .heatmap() first or pass kind='categorical'."
            )
        return build_gradient_legend(
            scale,
            vb,
            num_ticks=num_ticks,
            tick_format=tick_format,
            labels=labels,
            background=background,
            padding=padding,
            **shared,
        )

    if kind == "discrete":
        if scale is not None and scale.breaks is not None:
            breaks = scale.breaks
            colors = [
                scale((breaks[i] + breaks[i + 1]) / 2) for i in range(len(breaks) - 1)
            ]
            bin_labels = labels or [
                f"{tick_format.format(breaks[i])} \u2013 {tick_format.format(breaks[i + 1])}"
                for i in range(len(breaks) - 1)
            ]
            return build_discrete_legend(colors, bin_labels, vb, **shared)
        if scale is None:
            raise ValueError(
                "Cannot build discrete legend without a ColorScale. "
                "Call .heatmap() first."
            )
        return build_gradient_legend(
            scale,
            vb,
            num_ticks=num_ticks,
            tick_format=tick_format,
            labels=labels,
            background=background,
            padding=padding,
            **shared,
        )

    if kind == "categorical":
        if cat_pal is not None:
            colors = list(cat_pal.mapping.values())
            cat_labels = labels or list(cat_pal.mapping.keys())
            return build_discrete_legend(colors, cat_labels, vb, **shared)
        if scale is None:
            raise ValueError(
                "Cannot build categorical legend without a CategoricalPalette. "
                "Call .recolor_by_category() first."
            )
        return build_gradient_legend(
            scale,
            vb,
            num_ticks=num_ticks,
            tick_format=tick_format,
            labels=labels,
            background=background,
            padding=padding,
            **shared,
        )

    raise ValueError(f"Unknown legend kind: {kind!r}")
