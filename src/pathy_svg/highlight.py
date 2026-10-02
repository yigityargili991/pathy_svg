"""Highlight/dim logic — emphasize selected elements, desaturate the rest."""

from __future__ import annotations

from lxml import etree

from pathy_svg._constants import build_id_index, rendered_colorable_elements
from pathy_svg._css import set_style_property, style_property
from pathy_svg._paint import paint_targets
from pathy_svg.annotations import _ANNOTATIONS_ID
from pathy_svg.color import parse_svg_color, rgb_to_hex
from pathy_svg.legend import _GENERATED_LEGEND_ATTR


def _desaturate_color(color_str: str) -> str:
    """Convert a color to its greyscale equivalent using luminance weights."""
    try:
        r, g, b = parse_svg_color(color_str)
    except ValueError:
        return color_str
    grey = round(0.299 * r + 0.587 * g + 0.114 * b)
    return rgb_to_hex(grey, grey, grey)


def _get_fill_color(element: etree._Element) -> str | None:
    """Extract the current fill color from an element."""
    style_fill = style_property(element.get("style"), "fill")
    if style_fill is not None:
        return style_fill
    return element.get("fill")


def _dim_element(
    element: etree._Element,
    *,
    dim_opacity: float,
    desaturate: bool,
) -> None:
    """Apply dimming (opacity + optional desaturation) to an element."""
    element.set("fill-opacity", str(dim_opacity))
    style = set_style_property(element.get("style"), "fill-opacity", str(dim_opacity))
    element.set("style", style)

    if desaturate:
        fill = _get_fill_color(element)
        if fill and fill.lower() != "none":
            grey = _desaturate_color(fill)
            element.set("fill", grey)
            style = set_style_property(element.get("style"), "fill", grey)
            element.set("style", style)


def apply_highlight(
    tree: etree._ElementTree,
    ids: set[str],
    *,
    dim_opacity: float = 0.2,
    desaturate: bool = True,
    id_to_elem: dict[str, etree._Element] | None = None,
) -> None:
    """Highlight specified elements, dim all others. Modifies tree in-place.

    Shapes inside resource subtrees (``<defs>``, ``<pattern>``, ``<mask>``,
    ...) and inside generated legends, annotations, and tooltips are never
    dimmed.
    """
    if id_to_elem is None:
        id_to_elem = build_id_index(tree)

    # Expand group IDs: collect all children of highlighted groups
    highlighted_elems: set[etree._Element] = set()
    for eid in ids:
        elem = id_to_elem.get(eid)
        if elem is not None:
            highlighted_elems.update(paint_targets(elem))

    # Dim everything that's not highlighted
    for elem in rendered_colorable_elements(tree.getroot()):
        if elem in highlighted_elems:
            continue
        if any(_generated_overlay(parent) for parent in elem.iterancestors()):
            continue
        _dim_element(elem, dim_opacity=dim_opacity, desaturate=desaturate)


def _generated_overlay(element: etree._Element) -> bool:
    """Whether *element* is a legend, annotation, or tooltip group pathy_svg added.

    Matched by their markers, not the generic ``pathy-`` id prefix, which
    composition also gives to groups wrapping user geometry.
    """
    return (
        element.get(_GENERATED_LEGEND_ATTR) is not None
        or element.get("data-tooltip-for") is not None
        or element.get("id") == _ANNOTATIONS_ID
    )
