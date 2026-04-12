"""Stroke-based visualization — map data to stroke width and/or color."""

from __future__ import annotations

import numpy as np
from lxml import etree

from pathy_svg._constants import COLORABLE_TAGS, build_id_index, local_tag
from pathy_svg._css import set_style_property
from pathy_svg.themes import ColorScale


def _set_stroke(
    element: etree._Element,
    *,
    color: str | None = None,
    width: float | None = None,
    opacity: float | None = None,
) -> None:
    """Set stroke properties on an element."""
    style = element.get("style")
    if color is not None:
        element.set("stroke", color)
        style = set_style_property(style, "stroke", color)
    if width is not None:
        element.set("stroke-width", str(width))
        style = set_style_property(style, "stroke-width", str(width))
    if opacity is not None and opacity < 1.0:
        element.set("stroke-opacity", str(opacity))
        style = set_style_property(style, "stroke-opacity", str(opacity))
    if style is not None:
        element.set("style", style)


def apply_stroke_map(
    tree: etree._ElementTree,
    data: dict[str, float],
    *,
    width_range: tuple[float, float] | None = (1.0, 5.0),
    palette: str | None = None,
    vmin: float | None = None,
    vmax: float | None = None,
    opacity: float | None = None,
    na_width: float = 1.0,
    na_color: str | None = None,
    id_to_elem: dict[str, etree._Element] | None = None,
) -> ColorScale | None:
    """Map data to stroke width and/or color on SVG elements. Modifies tree in-place.

    Returns the fitted ColorScale if palette was used, else None.
    """
    if not data:
        return None

    if id_to_elem is None:
        id_to_elem = build_id_index(tree)

    values = np.array(list(data.values()), dtype=float)
    finite_vals = values[np.isfinite(values)]

    # Set up width normalization
    if width_range is not None and len(finite_vals) > 0:
        w_min, w_max = width_range
        d_min = float(finite_vals.min()) if vmin is None else vmin
        d_max = float(finite_vals.max()) if vmax is None else vmax
    else:
        w_min = w_max = d_min = d_max = 0.0

    # Set up color scale
    scale = None
    if palette is not None:
        scale = ColorScale(palette, vmin=vmin, vmax=vmax)
        scale.fit(list(data.values()))

    for eid, value in data.items():
        elem = id_to_elem.get(eid)
        if elem is None:
            continue

        is_nan = not np.isfinite(value)

        # Compute stroke width
        sw = None
        if width_range is not None:
            if is_nan:
                sw = na_width
            else:
                span = d_max - d_min
                if span == 0:
                    t = 0.5
                else:
                    t = (value - d_min) / span
                t = max(0.0, min(1.0, t))
                sw = w_min + t * (w_max - w_min)

        # Compute stroke color
        sc = None
        if palette is not None:
            if is_nan:
                sc = na_color
            else:
                sc = scale(value)

        kwargs = {"color": sc, "width": sw, "opacity": opacity}

        if local_tag(elem.tag) == "g":
            for child in elem.iter():
                if child is not elem and local_tag(child.tag) in COLORABLE_TAGS:
                    _set_stroke(child, **kwargs)
        else:
            _set_stroke(elem, **kwargs)

    return scale
