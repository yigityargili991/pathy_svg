"""Heatmap and recolor logic — the heart of pathy_svg."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TypedDict, cast

import numpy as np
from lxml import etree

from pathy_svg._constants import (
    COLORABLE_TAGS,
    build_id_index,
    local_tag,
    rendered_colorable_elements,
)
from pathy_svg._css import style_property as _style_property
from pathy_svg._paint import (
    matched_items_ancestor_first,
    paint_targets,
    set_fill,
    validate_opacity,
)
from pathy_svg.exceptions import ValidationError
from pathy_svg.themes import CategoricalPalette, ColorScale


def _protect_explicit_match(element: etree._Element, protected_paths: set[str]) -> None:
    """Protect a mapped element, including colorable descendants of groups."""
    protected_paths.update(_stable_element_path(t) for t in paint_targets(element))


def _stable_element_path(element: etree._Element) -> str:
    """Return a tree-stable identity unaffected by lxml Python wrapper reuse."""
    return element.getroottree().getpath(element)


class _FillKwargs(TypedDict, total=False):
    opacity: float | None
    preserve_stroke: bool


def _library_generated(element: etree._Element) -> bool:
    """Whether pathy_svg itself injected the element into the document.

    Library-generated elements (legend internals, annotation backgrounds,
    guides, ...) are marked with reserved ``pathy-`` prefixed ids or
    ``data-pathy-`` attributes. Only the element's own markers are
    consulted — never its ancestors' — because composition wraps ordinary
    user geometry in ``pathy-panel-*`` groups.
    """
    elem_id = element.get("id")
    if elem_id is not None and elem_id.startswith("pathy-"):
        return True
    return any(
        isinstance(name, str) and name.startswith("data-pathy-")
        for name in element.attrib
    )


def _color_missing_indexed(
    tree: etree._ElementTree,
    data: Mapping[str, object],
    id_to_elem: dict[str, etree._Element],
    protected_paths: set[str],
    na_color: str,
    fill_kwargs: _FillKwargs,
) -> None:
    """Paint indexed rendered elements absent from *data* with *na_color*.

    Only data-addressable elements (those present in *id_to_elem*) are
    repainted; ID-less geometry and elements injected by the library
    itself (legends, annotations, ...) are left untouched.
    """
    rendered_paths = {
        _stable_element_path(elem)
        for elem in rendered_colorable_elements(tree.getroot())
    }

    def _sweep(elem: etree._Element) -> None:
        path = _stable_element_path(elem)
        if path in protected_paths or path not in rendered_paths:
            return
        if _library_generated(elem) or _has_explicit_none_fill(elem):
            return
        set_fill(elem, na_color, **fill_kwargs)

    for eid, elem in id_to_elem.items():
        if eid in data:
            continue
        if _library_generated(elem):
            continue
        for target in paint_targets(elem):
            _sweep(target)


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
        opacity: Opacity in the range 0–1. ``None`` preserves existing opacity.
        preserve_stroke: Whether to preserve original stroke styling.
        color_missing: Whether to color paths that are not in the data with `na_color`.

    Returns:
        The fitted ColorScale object used for coloring, or None if data is empty.
    """
    opacity = validate_opacity(opacity)

    if not data:
        return None

    fill_kwargs: _FillKwargs = {"opacity": opacity, "preserve_stroke": preserve_stroke}
    if id_to_elem is None:
        id_to_elem = build_id_index(tree)

    protected_paths: set[str] = set()

    # ColorScale reports invalid configurations as ColorScaleError itself.
    scale = ColorScale(palette, vmin=vmin, vmax=vmax, vcenter=vcenter, breaks=breaks)
    scale.fit(list(data.values()))
    # Color elements that have data
    for _, value, elem in matched_items_ancestor_first(data, id_to_elem):
        _protect_explicit_match(elem, protected_paths)
        if np.isfinite(value):
            color = scale(value)
        else:
            color = na_color
        for target in paint_targets(elem):
            set_fill(target, color, **fill_kwargs)

    # Color paths with no data
    if color_missing:
        _color_missing_indexed(
            tree, data, id_to_elem, protected_paths, na_color, fill_kwargs
        )

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
        opacity: Opacity in the range 0–1. ``None`` preserves existing opacity.
        preserve_stroke: Whether to preserve original stroke styling.
    """
    opacity = validate_opacity(opacity)
    fill_kwargs: _FillKwargs = {"opacity": opacity, "preserve_stroke": preserve_stroke}
    if id_to_elem is None:
        id_to_elem = build_id_index(tree)

    for _, color, elem in matched_items_ancestor_first(colors, id_to_elem):
        for target in paint_targets(elem):
            set_fill(target, color, **fill_kwargs)


def apply_categorical(
    tree: etree._ElementTree,
    data: dict[str, str | None],
    *,
    palette: dict[str, str] | str = "tab10",
    na_color: str = "#cccccc",
    opacity: float | None = None,
    preserve_stroke: bool = True,
    color_missing: bool = True,
    id_to_elem: dict[str, etree._Element] | None = None,
) -> CategoricalPalette:
    """Apply categorical coloring to SVG elements. Modifies tree in-place.

    Args:
        tree: The lxml ElementTree representation of the SVG.
        data: A dictionary mapping element IDs to categorical labels. ``None``
            and NaN values are treated as missing categories.
        palette: A dictionary mapping categories to hex colors, or the name of a matplotlib colormap.
        na_color: Color for missing category values and colorable elements not
            represented in *data*.
        opacity: Opacity in the range 0–1. ``None`` preserves existing opacity.
        preserve_stroke: Whether to preserve original stroke styling.
        color_missing: Whether to color paths that are not in the data with `na_color`.

    Returns:
        The CategoricalPalette object used for coloring.
    """
    opacity = validate_opacity(opacity)
    cat_palette = CategoricalPalette(palette)
    fill_kwargs: _FillKwargs = {"opacity": opacity, "preserve_stroke": preserve_stroke}
    if id_to_elem is None:
        id_to_elem = build_id_index(tree)

    protected_paths: set[str] = set()

    for _, category, elem in matched_items_ancestor_first(data, id_to_elem):
        _protect_explicit_match(elem, protected_paths)
        if category is None or _is_missing_category(category):
            color = na_color
        else:
            color = cat_palette(category)
        for target in paint_targets(elem):
            set_fill(target, color, **fill_kwargs)

    if color_missing and data:
        _color_missing_indexed(
            tree, data, id_to_elem, protected_paths, na_color, fill_kwargs
        )

    return cat_palette


def _is_missing_category(category: object) -> bool:
    """Return whether a categorical value should use ``na_color``."""
    if category is None:
        return True
    try:
        return bool(np.isscalar(category) and np.isnan(category))
    except (TypeError, ValueError):
        return False


def aggregate_by_group(
    tree: etree._ElementTree,
    data: dict[str, float],
    agg: str | Callable[[list[float]], float] = "mean",
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
    func: Callable[[list[float]], float]
    if isinstance(agg, str):
        if agg not in agg_funcs:
            raise ValidationError(
                f"Unknown aggregation: {agg!r}. Choose from {list(agg_funcs)}"
            )
        func = cast("Callable[[list[float]], float]", agg_funcs[agg])
    elif callable(agg):
        func = agg
    else:
        raise ValidationError(
            f"Unknown aggregation: {agg!r}. Choose from {list(agg_funcs)}"
        )

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
