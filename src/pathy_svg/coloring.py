"""Heatmap and recolor logic — the heart of pathy_svg."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import numpy as np
from lxml import etree

from pathy_svg.exceptions import ColorScaleError, PathNotFoundError
from pathy_svg.themes import CategoricalPalette, ColorScale

if TYPE_CHECKING:
    pass


def _find_element_by_id(tree: etree._ElementTree, eid: str) -> etree._Element | None:
    """Find an element by its id attribute."""
    results = tree.xpath(f'//*[@id="{eid}"]')
    return results[0] if results else None


def _find_colorable_elements(tree: etree._ElementTree) -> list[etree._Element]:
    """Find all elements that can be colored (paths, rects, circles, etc.)."""
    colorable_tags = {"path", "rect", "circle", "ellipse", "polygon", "polyline"}
    elements = []
    for elem in tree.iter():
        local = _local_tag(elem.tag)
        if local in colorable_tags and elem.get("id"):
            elements.append(elem)
    return elements


def _local_tag(tag: str) -> str:
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def _set_fill(element: etree._Element, color: str, *, opacity: float | None = None, preserve_stroke: bool = True):
    """Set the fill color on an element, handling both style attr and fill attr."""
    style = element.get("style", "")

    if "fill:" in style or "fill :" in style:
        # Replace fill in existing style
        style = re.sub(r"fill\s*:\s*[^;]+", f"fill:{color}", style)
    elif style:
        style = f"fill:{color};{style}"
    else:
        style = f"fill:{color}"

    if opacity is not None and opacity < 1.0:
        if "fill-opacity:" in style:
            style = re.sub(r"fill-opacity\s*:\s*[^;]+", f"fill-opacity:{opacity}", style)
        else:
            style += f";fill-opacity:{opacity}"

    element.set("style", style)


def _set_fill_on_group(element: etree._Element, color: str, **kwargs):
    """Set fill on all colorable children of a group."""
    colorable_tags = {"path", "rect", "circle", "ellipse", "polygon", "polyline"}
    for child in element.iter():
        if child is element:
            continue
        if _local_tag(child.tag) in colorable_tags:
            _set_fill(child, color, **kwargs)


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
) -> None:
    """Apply data-driven coloring to SVG elements. Modifies tree in-place."""
    if not data:
        return

    try:
        scale = ColorScale(
            palette, vmin=vmin, vmax=vmax, vcenter=vcenter, breaks=breaks
        )
    except (ValueError, KeyError) as exc:
        raise ColorScaleError(f"Invalid palette or color scale config: {exc}") from exc

    scale.fit(list(data.values()))

    fill_kwargs = {"opacity": opacity, "preserve_stroke": preserve_stroke}
    protected_ids = set(data.keys())

    # Color elements that have data
    for eid, value in data.items():
        elem = _find_element_by_id(tree, eid)
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
                if _local_tag(child.tag) in {"path", "rect", "circle", "ellipse", "polygon", "polyline"}:
                    child_id = child.get("id")
                    if child_id:
                        protected_ids.add(child_id)
            _set_fill_on_group(elem, color, **fill_kwargs)
        else:
            _set_fill(elem, color, **fill_kwargs)

    # Color paths with no data
    if color_missing:
        for elem in _find_colorable_elements(tree):
            eid = elem.get("id")
            if eid and eid not in protected_ids:
                _set_fill(elem, na_color, **fill_kwargs)

    return scale


def apply_recolor(
    tree: etree._ElementTree,
    colors: dict[str, str],
    *,
    opacity: float | None = None,
    preserve_stroke: bool = True,
) -> None:
    """Apply manual color mapping to SVG elements. Modifies tree in-place."""
    fill_kwargs = {"opacity": opacity, "preserve_stroke": preserve_stroke}
    for eid, color in colors.items():
        elem = _find_element_by_id(tree, eid)
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
    """Apply categorical coloring to SVG elements. Modifies tree in-place."""
    cat_palette = CategoricalPalette(palette)
    fill_kwargs = {"opacity": opacity, "preserve_stroke": preserve_stroke}

    for eid, category in data.items():
        elem = _find_element_by_id(tree, eid)
        if elem is None:
            continue
        color = cat_palette(category)
        if _local_tag(elem.tag) == "g":
            _set_fill_on_group(elem, color, **fill_kwargs)
        else:
            _set_fill(elem, color, **fill_kwargs)

    return cat_palette
