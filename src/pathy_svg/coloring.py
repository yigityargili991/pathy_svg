"""Heatmap and recolor logic — the heart of pathy_svg."""

from __future__ import annotations

from collections.abc import Callable
from math import isfinite
from numbers import Real
from typing import TypeVar

import numpy as np
from lxml import etree

from pathy_svg._constants import (
    COLORABLE_TAGS,
    build_id_index,
    local_tag,
    rendered_colorable_elements,
)
from pathy_svg._css import set_style_property
from pathy_svg._css import style_property as _style_property
from pathy_svg.exceptions import ColorScaleError, ValidationError
from pathy_svg.themes import CategoricalPalette, ColorScale

_T = TypeVar("_T")


def _validate_opacity(opacity: object) -> float | None:
    """Validate and normalize an optional SVG opacity value."""
    if opacity is None:
        return None
    if isinstance(opacity, (bool, np.bool_)) or not isinstance(opacity, Real):
        raise TypeError("opacity must be a real number between 0.0 and 1.0")
    try:
        normalized = float(opacity)
    except (OverflowError, TypeError, ValueError) as exc:
        raise ValidationError(
            "opacity must be a real number between 0.0 and 1.0"
        ) from exc
    if not isfinite(normalized) or not 0.0 <= normalized <= 1.0:
        raise ValidationError("opacity must be a real number between 0.0 and 1.0")
    return normalized


def _matched_items_ancestor_first(
    data: dict[str, _T], id_to_elem: dict[str, etree._Element]
) -> list[tuple[str, _T, etree._Element]]:
    """Return matched mapping items ordered from SVG ancestors to descendants."""
    matched = [
        (sum(1 for _ in elem.iterancestors()), position, key, value, elem)
        for position, (key, value) in enumerate(data.items())
        if (elem := id_to_elem.get(key)) is not None
    ]
    matched.sort(key=lambda item: (item[0], item[1]))
    return [(key, value, elem) for _, _, key, value, elem in matched]


def _protect_explicit_match(element: etree._Element, protected_paths: set[str]) -> None:
    """Protect a mapped element, including colorable descendants of groups."""
    if local_tag(element.tag) == "g":
        protected_paths.update(
            _stable_element_path(child) for child in _colorable_children(element)
        )
    elif local_tag(element.tag) in COLORABLE_TAGS:
        protected_paths.add(_stable_element_path(element))


def _stable_element_path(element: etree._Element) -> str:
    """Return a tree-stable identity unaffected by lxml Python wrapper reuse."""
    return element.getroottree().getpath(element)


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
    if opacity is not None:
        element.set("fill-opacity", str(opacity))

    style = set_style_property(element.get("style"), "fill", color)
    if opacity is not None:
        style = set_style_property(style, "fill-opacity", str(opacity))
    if not preserve_stroke:
        element.set("stroke", "none")
        style = set_style_property(style, "stroke", "none")

    element.set("style", style)


def _colorable_children(element: etree._Element):
    """Yield rendered colorable descendant elements of a group."""
    for child in rendered_colorable_elements(element):
        if child is not element:
            yield child


def _set_fill_on_group(element: etree._Element, color: str, **kwargs):
    """Set fill on all colorable children of a group."""
    for child in _colorable_children(element):
        _set_fill(child, color, **kwargs)


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
    data: dict[str, object],
    id_to_elem: dict[str, etree._Element],
    protected_paths: set[str],
    na_color: str,
    fill_kwargs: dict[str, object],
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
        _set_fill(elem, na_color, **fill_kwargs)

    for eid, elem in id_to_elem.items():
        if eid in data:
            continue
        if _library_generated(elem):
            continue
        if local_tag(elem.tag) == "g":
            for child in _colorable_children(elem):
                _sweep(child)
        else:
            _sweep(elem)


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
    opacity = _validate_opacity(opacity)

    if not data:
        return None

    fill_kwargs = {"opacity": opacity, "preserve_stroke": preserve_stroke}
    if id_to_elem is None:
        id_to_elem = build_id_index(tree)

    scale = None
    protected_paths: set[str] = set()

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
        # Color elements that have data
        for _, value, elem in _matched_items_ancestor_first(data, id_to_elem):
            _protect_explicit_match(elem, protected_paths)
            if np.isfinite(value):
                color = scale(value)
            else:
                color = na_color
            if local_tag(elem.tag) == "g":
                _set_fill_on_group(elem, color, **fill_kwargs)
            else:
                _set_fill(elem, color, **fill_kwargs)

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
    opacity = _validate_opacity(opacity)
    fill_kwargs = {"opacity": opacity, "preserve_stroke": preserve_stroke}
    if id_to_elem is None:
        id_to_elem = build_id_index(tree)

    for _, color, elem in _matched_items_ancestor_first(colors, id_to_elem):
        if local_tag(elem.tag) == "g":
            _set_fill_on_group(elem, color, **fill_kwargs)
        else:
            _set_fill(elem, color, **fill_kwargs)


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
    opacity = _validate_opacity(opacity)
    cat_palette = CategoricalPalette(palette)
    fill_kwargs = {"opacity": opacity, "preserve_stroke": preserve_stroke}
    if id_to_elem is None:
        id_to_elem = build_id_index(tree)

    protected_paths: set[str] = set()

    for _, category, elem in _matched_items_ancestor_first(data, id_to_elem):
        _protect_explicit_match(elem, protected_paths)
        color = na_color if _is_missing_category(category) else cat_palette(category)
        if local_tag(elem.tag) == "g":
            _set_fill_on_group(elem, color, **fill_kwargs)
        else:
            _set_fill(elem, color, **fill_kwargs)

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
