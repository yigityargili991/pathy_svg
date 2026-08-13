"""Legend builder — gradient, discrete, and categorical legends injected as SVG elements."""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from typing import Literal

from lxml import etree

from pathy_svg._constants import SVG_NS, svg_sub
from pathy_svg.themes import CategoricalPalette, ColorScale
from pathy_svg.transform import BBox, ViewBox, bbox_union

Direction = Literal["vertical", "horizontal"]
LegendKind = Literal["auto", "gradient", "discrete", "categorical"]
_GENERATED_LEGEND_ATTR = "data-pathy-legend"
_GENERATED_LEGEND_VALUE = "generated"


@dataclass(frozen=True)
class _BuiltLegend:
    element: etree._Element
    bounds: BBox


def _validate_layout_parameters(
    position: tuple[float, float],
    size: tuple[float, float],
    direction: Direction,
    padding: float,
    font_size: float | None,
    title_size: float | None,
) -> None:
    if direction not in ("vertical", "horizontal"):
        raise ValueError("direction must be 'vertical' or 'horizontal'")
    if len(position) != 2 or not all(math.isfinite(value) for value in position):
        raise ValueError("position must contain two finite numbers")
    if len(size) != 2 or not all(math.isfinite(value) for value in size):
        raise ValueError("size must contain two finite numbers")
    if not all(value > 0 for value in size):
        raise ValueError("size values must be greater than zero")
    if not math.isfinite(padding) or padding < 0:
        raise ValueError("padding must be a finite, non-negative number")
    if font_size is not None and (not math.isfinite(font_size) or font_size <= 0):
        raise ValueError("font_size must be a finite, positive number")
    if title_size is not None and (not math.isfinite(title_size) or title_size <= 0):
        raise ValueError("title_size must be a finite, positive number")


def _validate_labels(labels: list[str], *, expected: int | None = None) -> None:
    if not labels:
        raise ValueError("labels must contain at least one label")
    if not all(isinstance(label, str) for label in labels):
        raise TypeError("labels must contain only strings")
    if expected is not None and len(labels) != expected:
        raise ValueError(f"labels must contain exactly {expected} entries")


def _with_stroke(bounds: BBox, border: bool) -> BBox:
    if not border:
        return bounds
    half_stroke = 0.25
    return BBox(
        bounds.x - half_stroke,
        bounds.y - half_stroke,
        bounds.width + half_stroke * 2,
        bounds.height + half_stroke * 2,
    )


def _text_bounds(
    text: str, x: float, baseline: float, font_size: float, *, anchor: str = "start"
) -> BBox:
    # SVG does not expose font metrics without a renderer.  This conservative
    # one-em-per-codepoint estimate covers wide glyphs as well as the common
    # sans-serif families used by the API and keeps expansion deterministic.
    advance = max(font_size * 0.6, len(text) * font_size)
    if anchor == "middle":
        x -= advance / 2
    elif anchor == "end":
        x -= advance
    return BBox(
        x - font_size * 0.1,
        baseline - font_size * 1.05,
        advance + font_size * 0.2,
        font_size * 1.4,
    )


def _add_background(
    group: etree._Element,
    content_bounds: BBox,
    background: str | None,
    padding: float,
) -> BBox:
    if background is None:
        return content_bounds
    bounds = BBox(
        content_bounds.x - padding,
        content_bounds.y - padding,
        content_bounds.width + padding * 2,
        content_bounds.height + padding * 2,
    )
    bg = etree.Element(f"{{{SVG_NS}}}rect")
    bg.set("x", str(bounds.x))
    bg.set("y", str(bounds.y))
    bg.set("width", str(bounds.width))
    bg.set("height", str(bounds.height))
    bg.set("fill", background)
    bg.set("rx", "3")
    group.insert(0, bg)
    return bounds


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
    return _build_gradient_legend(
        scale,
        viewbox,
        position=position,
        size=size,
        direction=direction,
        num_ticks=num_ticks,
        tick_format=tick_format,
        labels=labels,
        font_size=font_size,
        font_color=font_color,
        font_family=font_family,
        title=title,
        title_size=title_size,
        border=border,
        border_color=border_color,
        background=background,
        padding=padding,
    ).element


def _build_gradient_legend(
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
) -> _BuiltLegend:
    _validate_layout_parameters(
        position, size, direction, padding, font_size, title_size
    )
    # Calculate pixel positions from fractional coords
    x = viewbox.x + position[0] * viewbox.width
    y = viewbox.y + position[1] * viewbox.height
    w = size[0] * viewbox.width
    h = size[1] * viewbox.height

    if direction == "horizontal":
        w, h = h, w  # swap for horizontal

    uid = uuid.uuid4().hex[:8]

    g = etree.Element(
        f"{{{SVG_NS}}}g",
        id="pathy-legend",
        attrib={_GENERATED_LEGEND_ATTR: _GENERATED_LEGEND_VALUE},
    )

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
    _validate_labels(labels)

    rendered_bounds = [_with_stroke(BBox(x, y, w, h), border)]

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
        if direction == "horizontal":
            txt.set("text-anchor", "middle")
        txt.text = label
        rendered_bounds.append(
            _text_bounds(
                label,
                tx,
                ty,
                fs,
                anchor="middle" if direction == "horizontal" else "start",
            )
        )

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
        rendered_bounds.append(_text_bounds(title, x, y - 6, ts))

    bounds = _add_background(g, bbox_union(rendered_bounds), background, padding)
    return _BuiltLegend(g, bounds)


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
    background: str | None = None,
    padding: float = 5,
) -> etree._Element:
    """Build a discrete/categorical legend as an SVG <g> element."""
    return _build_discrete_legend(
        colors,
        labels,
        viewbox,
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
        background=background,
        padding=padding,
    ).element


def _build_discrete_legend(
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
    background: str | None = None,
    padding: float = 5,
) -> _BuiltLegend:
    _validate_layout_parameters(
        position, size, direction, padding, font_size, title_size
    )
    if not colors:
        raise ValueError("colors must contain at least one color")
    if not all(isinstance(color, str) for color in colors):
        raise TypeError("colors must contain only strings")
    _validate_labels(labels, expected=len(colors))
    x = viewbox.x + position[0] * viewbox.width
    y = viewbox.y + position[1] * viewbox.height
    w = size[0] * viewbox.width
    h = size[1] * viewbox.height
    if direction == "horizontal":
        w, h = h, w
    n = len(colors)

    fs = font_size or max(6, min(14, viewbox.height * 0.025))
    ts = title_size or fs * 1.2

    g = etree.Element(
        f"{{{SVG_NS}}}g",
        id="pathy-legend",
        attrib={_GENERATED_LEGEND_ATTR: _GENERATED_LEGEND_VALUE},
    )
    rendered_bounds: list[BBox] = []

    if title:
        ttl = svg_sub(g, "text")
        ttl.set("x", str(x))
        ttl.set("y", str(y - 6))
        ttl.set(
            "style",
            f"fill:{font_color};font-size:{ts}px;font-family:{font_family};font-weight:bold",
        )
        ttl.text = title
        rendered_bounds.append(_text_bounds(title, x, y - 6, ts))

    for i, (color, label) in enumerate(zip(colors, labels)):
        if direction == "vertical":
            swatch_w, swatch_h = w, h / n
            sx, sy = x, y + i * swatch_h
            tx, ty = sx + swatch_w + 4, sy + swatch_h / 2 + fs / 3
            anchor = "start"
        else:
            swatch_w, swatch_h = w / n, h
            sx, sy = x + i * swatch_w, y
            tx, ty = sx + swatch_w / 2, sy + swatch_h + fs + 2
            anchor = "middle"

        rect = svg_sub(g, "rect")
        rect.set("x", str(sx))
        rect.set("y", str(sy))
        rect.set("width", str(swatch_w))
        rect.set("height", str(swatch_h))
        rect.set("fill", color)
        if border:
            rect.set("stroke", border_color)
            rect.set("stroke-width", "0.5")

        txt = svg_sub(g, "text")
        txt.set("x", str(tx))
        txt.set("y", str(ty))
        txt.set(
            "style", f"fill:{font_color};font-size:{fs}px;font-family:{font_family}"
        )
        if anchor == "middle":
            txt.set("text-anchor", anchor)
        txt.text = label
        rendered_bounds.append(_with_stroke(BBox(sx, sy, swatch_w, swatch_h), border))
        rendered_bounds.append(_text_bounds(label, tx, ty, fs, anchor=anchor))

    bounds = _add_background(g, bbox_union(rendered_bounds), background, padding)
    return _BuiltLegend(g, bounds)


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
    return _build_legend_layout(
        kind,
        scale,
        cat_pal,
        vb,
        position=position,
        size=size,
        direction=direction,
        num_ticks=num_ticks,
        tick_format=tick_format,
        labels=labels,
        font_size=font_size,
        font_color=font_color,
        font_family=font_family,
        title=title,
        title_size=title_size,
        border=border,
        border_color=border_color,
        background=background,
        padding=padding,
    ).element


def _build_legend_layout(
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
) -> _BuiltLegend:
    """Build a legend and return the rendered bounds used by the mixin."""
    shared = {
        "position": position,
        "size": size,
        "direction": direction,
        "font_size": font_size,
        "font_color": font_color,
        "font_family": font_family,
        "title": title,
        "title_size": title_size,
        "border": border,
        "border_color": border_color,
    }

    if kind == "gradient":
        if scale is None:
            raise ValueError(
                "Cannot build gradient legend without a ColorScale. "
                "Call .heatmap() first or pass kind='categorical'."
            )
        return _build_gradient_legend(
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
            bin_labels = (
                labels
                if labels is not None
                else [
                    f"{tick_format.format(breaks[i])} \u2013 "
                    f"{tick_format.format(breaks[i + 1])}"
                    for i in range(len(breaks) - 1)
                ]
            )
            return _build_discrete_legend(
                colors,
                bin_labels,
                vb,
                background=background,
                padding=padding,
                **shared,
            )
        if scale is None:
            raise ValueError(
                "Cannot build discrete legend without a ColorScale. "
                "Call .heatmap() first."
            )
        return _build_gradient_legend(
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
            cat_labels = labels if labels is not None else list(cat_pal.mapping.keys())
            return _build_discrete_legend(
                colors,
                cat_labels,
                vb,
                background=background,
                padding=padding,
                **shared,
            )
        if scale is None:
            raise ValueError(
                "Cannot build categorical legend without a CategoricalPalette. "
                "Call .recolor_by_category() first."
            )
        return _build_gradient_legend(
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
