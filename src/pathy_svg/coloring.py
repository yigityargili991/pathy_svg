"""Heatmap and recolor logic — the heart of pathy_svg."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from lxml import etree

from pathy_svg._constants import COLORABLE_TAGS, build_id_index, local_tag
from pathy_svg._css import set_style_property, style_property as _style_property
from pathy_svg.exceptions import ColorScaleError
from pathy_svg.themes import CategoricalPalette, ColorScale


def _set_fill(
    element: etree._Element,
    color: str,
    *,
    opacity: float | None = None,
    preserve_stroke: bool = True,
):
    """Set the fill color on an element, handling both style attr and fill attr."""
    # Keep SVG presentation attributes aligned with CSS so renderers that
    # sanitize inline styles still preserve the intended fill color.
    element.set("fill", color)
    if opacity is not None and opacity < 1.0:
        element.set("fill-opacity", str(opacity))

    style = set_style_property(element.get("style"), "fill", color)
    if opacity is not None and opacity < 1.0:
        style = set_style_property(style, "fill-opacity", str(opacity))
    if not preserve_stroke:
        element.set("stroke", "none")
        style = set_style_property(style, "stroke", "none")

    element.set("style", style)


def _colorable_children(element: etree._Element):
    """Yield all colorable descendant elements of a group."""
    for child in element.iter():
        if child is not element and local_tag(child.tag) in COLORABLE_TAGS:
            yield child


def _set_fill_on_group(element: etree._Element, color: str, **kwargs):
    """Set fill on all colorable children of a group."""
    for child in _colorable_children(element):
        _set_fill(child, color, **kwargs)


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
    id_to_elem: dict[str, etree._Element] | None = None,
) -> ColorScale | None:
    """Apply data-driven coloring to SVG elements. Modifies tree in-place.

    Args:
        tree: The lxml ElementTree representation of the SVG.
        data: A dictionary whose keys match entries in *id_to_elem*.
        palette: Name of a matplotlib colormap or a list of hex colors.
        vmin: Minimum value for the color scale.
        vmax: Maximum value for the color scale.
        vcenter: Center value for diverging color scales.
        na_color: Color to use for missing or NaN values.
        breaks: List of boundary values for discrete color scales.
        opacity: Opacity for the filled paths.
        preserve_stroke: Whether to preserve original stroke styling.
        color_missing: Whether to color paths that are not in the data with `na_color`.

    Returns:
        The fitted ColorScale object used for coloring, or None if data is empty.
    """
    if not data:
        return None

    fill_kwargs = {"opacity": opacity, "preserve_stroke": preserve_stroke}
    if id_to_elem is None:
        id_to_elem = build_id_index(tree)

    scale = None
    protected_keys: set[str] = set()
    protected_elems: set[int] = set()

    if data:
        try:
            scale = ColorScale(
                palette, vmin=vmin, vmax=vmax, vcenter=vcenter, breaks=breaks
            )
        except (ValueError, KeyError) as exc:
            raise ColorScaleError(
                f"Invalid palette or color scale config: {exc}"
            ) from exc

        scale.fit(list(data.values()))
        protected_keys = set(data.keys())

        # Color elements that have data
        for eid, value in data.items():
            elem = id_to_elem.get(eid)
            if elem is None:
                continue
            if np.isfinite(value):
                color = scale(value)
            else:
                color = na_color
            if local_tag(elem.tag) == "g":
                for child in _colorable_children(elem):
                    protected_elems.add(id(child))
                _set_fill_on_group(elem, color, **fill_kwargs)
            else:
                _set_fill(elem, color, **fill_kwargs)

    # Color paths with no data
    if color_missing:
        for eid, elem in id_to_elem.items():
            if eid not in protected_keys and id(elem) not in protected_elems:
                local = local_tag(elem.tag)
                if local in COLORABLE_TAGS and not _has_explicit_none_fill(elem):
                    _set_fill(elem, na_color, **fill_kwargs)

    return scale


def apply_recolor(
    tree: etree._ElementTree,
    colors: dict[str, str],
    *,
    opacity: float | None = None,
    preserve_stroke: bool = True,
    id_to_elem: dict[str, etree._Element] | None = None,
) -> None:
    """Apply manual color mapping to SVG elements. Modifies tree in-place.

    Args:
        tree: The lxml ElementTree representation of the SVG.
        colors: A dictionary mapping element IDs to hex color strings.
        opacity: Opacity for the filled paths.
        preserve_stroke: Whether to preserve original stroke styling.
    """
    fill_kwargs = {"opacity": opacity, "preserve_stroke": preserve_stroke}
    if id_to_elem is None:
        id_to_elem = build_id_index(tree)

    for eid, color in colors.items():
        elem = id_to_elem.get(eid)
        if elem is None:
            continue
        if local_tag(elem.tag) == "g":
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
    id_to_elem: dict[str, etree._Element] | None = None,
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
    if id_to_elem is None:
        id_to_elem = build_id_index(tree)

    for eid, category in data.items():
        elem = id_to_elem.get(eid)
        if elem is None:
            continue
        color = cat_palette(category)
        if local_tag(elem.tag) == "g":
            _set_fill_on_group(elem, color, **fill_kwargs)
        else:
            _set_fill(elem, color, **fill_kwargs)

    return cat_palette


def aggregate_by_group(
    tree: etree._ElementTree,
    data: dict[str, float],
    agg: str | Callable = "mean",
    key_attr: str = "id",
) -> dict[str, float]:
    """Walk <g> elements, aggregate matched children's values.

    Returns a dict of {group_id: aggregated_value} for groups that have
    at least one child with data.

    Args:
        tree: The lxml ElementTree.
        data: Mapping of child element attribute values to numeric values.
        agg: Aggregation function name or a callable accepting a list of floats.
        key_attr: Element attribute used to match child elements to *data*
            keys (default ``"id"``).  Group lookup and output keys always
            use the group's ``id`` attribute.
    """
    agg_funcs = {
        "mean": np.mean,
        "sum": np.sum,
        "min": np.min,
        "max": np.max,
        "median": np.median,
    }
    if callable(agg):
        func = agg
    elif agg in agg_funcs:
        func = agg_funcs[agg]
    else:
        raise ValueError(f"Unknown aggregation: {agg!r}. Choose from {list(agg_funcs)}")

    result = {}
    for elem in tree.iter():
        if local_tag(elem.tag) != "g":
            continue
        gid = elem.get("id")
        if not gid:
            continue

        child_vals = []
        for child in elem.iter():
            if child is elem:
                continue
            cid = child.get(key_attr)
            if cid and cid in data and local_tag(child.tag) in COLORABLE_TAGS:
                val = data[cid]
                if np.isfinite(val):
                    child_vals.append(val)

        if child_vals:
            result[gid] = float(func(child_vals))

    return result
