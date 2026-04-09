"""Heatmap and recolor logic — the heart of pathy_svg."""

from __future__ import annotations

import re

import numpy as np
from lxml import etree

from pathy_svg.exceptions import ColorScaleError
from pathy_svg.themes import CategoricalPalette, ColorScale
from pathy_svg.transform import _local_tag

COLORABLE_TAGS = frozenset({"path", "rect", "circle", "ellipse", "polygon", "polyline"})


def _build_id_index(tree: etree._ElementTree) -> dict[str, etree._Element]:
    """Build a dict mapping element id -> element. First element wins for duplicate IDs."""
    index: dict[str, etree._Element] = {}
    for elem in tree.iter():
        eid = elem.get("id")
        if eid:
            index.setdefault(eid, elem)
    return index


def _set_fill(
    element: etree._Element,
    color: str,
    *,
    opacity: float | None = None,
    preserve_stroke: bool = True,
):
    """Set the fill color on an element, handling both style attr and fill attr."""
    style = element.get("style")

    # Keep SVG presentation attributes aligned with CSS so renderers that
    # sanitize inline styles still preserve the intended fill color.
    element.set("fill", color)
    if opacity is not None and opacity < 1.0:
        element.set("fill-opacity", str(opacity))

    # Fast path: no existing style, create minimal style string
    if style is None:
        if opacity is not None and opacity < 1.0:
            style = f"fill:{color};fill-opacity:{opacity}"
        else:
            style = f"fill:{color}"
        element.set("style", style)
        return

    if "fill:" in style or "fill :" in style:
        style = re.sub(r"fill\s*:\s*[^;]+", f"fill:{color}", style)
    else:
        style = f"fill:{color};{style}"

    if opacity is not None and opacity < 1.0:
        if "fill-opacity:" in style:
            style = re.sub(
                r"fill-opacity\s*:\s*[^;]+", f"fill-opacity:{opacity}", style
            )
        else:
            style += f";fill-opacity:{opacity}"

    element.set("style", style)


def _set_fill_on_group(element: etree._Element, color: str, **kwargs):
    """Set fill on all colorable children of a group."""
    for child in element.iter():
        if child is element:
            continue
        if _local_tag(child.tag) in COLORABLE_TAGS:
            _set_fill(child, color, **kwargs)


def _style_property(style: str | None, prop: str) -> str | None:
    """Return a CSS property value from an inline style string."""
    if not style:
        return None
    match = re.search(rf"(?:^|;)\s*{re.escape(prop)}\s*:\s*([^;]+)", style)
    if match is None:
        return None
    return match.group(1).strip()


def _has_explicit_none_fill(element: etree._Element) -> bool:
    """Whether the element is explicitly marked as unfilled."""
    style_fill = _style_property(element.get("style"), "fill")
    if style_fill is not None:
        return style_fill.lower() == "none"

    attr_fill = element.get("fill")
    if attr_fill is not None:
        return attr_fill.lower() == "none"

    return False


def apply_heatmap(
    tree: etree._ElementTree,
    data: dict[str, float],
    *,
    palette: str | list[str] = "RdYlBu_r",
    vmin: float | None = None,
    vmax: float | None = None,
    vcenter: float | None = None,
    na_color: str = "#cccccc",
    breaks: list[float] | None = None,
    opacity: float | None = None,
    preserve_stroke: bool = True,
    color_missing: bool = True,
    clip: bool = True,
) -> ColorScale | None:
    """Apply data-driven coloring to SVG elements. Modifies tree in-place.

    Args:
        tree: The lxml ElementTree representation of the SVG.
        data: A dictionary mapping element IDs to numeric values.
        palette: Name of a matplotlib colormap or a list of hex colors.
        vmin: Minimum value for the color scale.
        vmax: Maximum value for the color scale.
        vcenter: Center value for diverging color scales.
        na_color: Color to use for missing or NaN values.
        breaks: List of boundary values for discrete color scales.
        opacity: Opacity for the filled paths.
        preserve_stroke: Whether to preserve original stroke styling.
        color_missing: Whether to color paths that are not in the data with `na_color`.
        clip: Whether to clip values outside the `vmin` and `vmax` bounds.

    Returns:
        The fitted ColorScale object used for coloring, or None if data is empty.
    """
    if not data:
        return None

    try:
        scale = ColorScale(
            palette, vmin=vmin, vmax=vmax, vcenter=vcenter, breaks=breaks
        )
    except (ValueError, KeyError) as exc:
        raise ColorScaleError(f"Invalid palette or color scale config: {exc}") from exc

    scale.fit(list(data.values()))

    fill_kwargs = {"opacity": opacity, "preserve_stroke": preserve_stroke}
    protected_ids = set(data.keys())
    id_to_elem = _build_id_index(tree)

    # Color elements that have data
    for eid, value in data.items():
        elem = id_to_elem.get(eid)
        if elem is None:
            continue
        if np.isfinite(value):
            color = scale(value)
        else:
            color = na_color
        if _local_tag(elem.tag) == "g":
            for child in elem.iter():
                if child is elem:
                    continue
                if _local_tag(child.tag) in COLORABLE_TAGS:
                    child_id = child.get("id")
                    if child_id:
                        protected_ids.add(child_id)
            _set_fill_on_group(elem, color, **fill_kwargs)
        else:
            _set_fill(elem, color, **fill_kwargs)

    # Color paths with no data
    if color_missing:
        for eid, elem in id_to_elem.items():
            if eid not in protected_ids:
                local = _local_tag(elem.tag)
                if local in COLORABLE_TAGS and not _has_explicit_none_fill(elem):
                    _set_fill(elem, na_color, **fill_kwargs)

    return scale


def apply_recolor(
    tree: etree._ElementTree,
    colors: dict[str, str],
    *,
    opacity: float | None = None,
    preserve_stroke: bool = True,
) -> None:
    """Apply manual color mapping to SVG elements. Modifies tree in-place.

    Args:
        tree: The lxml ElementTree representation of the SVG.
        colors: A dictionary mapping element IDs to hex color strings.
        opacity: Opacity for the filled paths.
        preserve_stroke: Whether to preserve original stroke styling.
    """
    fill_kwargs = {"opacity": opacity, "preserve_stroke": preserve_stroke}
    id_to_elem = _build_id_index(tree)

    for eid, color in colors.items():
        elem = id_to_elem.get(eid)
        if elem is None:
            continue
        if _local_tag(elem.tag) == "g":
            _set_fill_on_group(elem, color, **fill_kwargs)
        else:
            _set_fill(elem, color, **fill_kwargs)


def apply_categorical(
    tree: etree._ElementTree,
    data: dict[str, str],
    *,
    palette: dict[str, str] | str = "tab10",
    na_color: str = "#cccccc",
    opacity: float | None = None,
    preserve_stroke: bool = True,
) -> CategoricalPalette:
    """Apply categorical coloring to SVG elements. Modifies tree in-place.

    Args:
        tree: The lxml ElementTree representation of the SVG.
        data: A dictionary mapping element IDs to categorical labels.
        palette: A dictionary mapping categories to hex colors, or the name of a matplotlib colormap.
        na_color: Color to use for missing or NaN categories.
        opacity: Opacity for the filled paths.
        preserve_stroke: Whether to preserve original stroke styling.

    Returns:
        The CategoricalPalette object used for coloring.
    """
    cat_palette = CategoricalPalette(palette)
    fill_kwargs = {"opacity": opacity, "preserve_stroke": preserve_stroke}
    id_to_elem = _build_id_index(tree)

    for eid, category in data.items():
        elem = id_to_elem.get(eid)
        if elem is None:
            continue
        color = cat_palette(category)
        if _local_tag(elem.tag) == "g":
            _set_fill_on_group(elem, color, **fill_kwargs)
        else:
            _set_fill(elem, color, **fill_kwargs)

    return cat_palette
