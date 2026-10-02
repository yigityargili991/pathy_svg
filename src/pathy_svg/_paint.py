"""Shared helpers for painting data-mapped SVG elements."""

from __future__ import annotations

from math import isfinite
from numbers import Real
from typing import TypeVar

import numpy as np
from lxml import etree

from pathy_svg._constants import SVG_NS, local_tag, rendered_colorable_elements
from pathy_svg._css import set_style_property
from pathy_svg.exceptions import ValidationError

_T = TypeVar("_T")


def validate_opacity(opacity: object) -> float | None:
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


def matched_items_ancestor_first(
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


def paint_targets(element: etree._Element) -> list[etree._Element]:
    """Return the elements a mapped element paints.

    A group paints its rendered colorable descendants, skipping shapes inside
    resource subtrees such as ``<defs>`` or ``<pattern>``; any other element
    paints itself.
    """
    if local_tag(element.tag) == "g":
        return rendered_colorable_elements(element)
    return [element]


def set_fill(
    element: etree._Element,
    color: str,
    *,
    opacity: float | None = None,
    preserve_stroke: bool = True,
) -> None:
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


def get_or_create_defs(root: etree._Element) -> etree._Element:
    """Find or create the ``<defs>`` element in the SVG root."""
    defs = root.find(f"{{{SVG_NS}}}defs")
    if defs is None:
        defs = etree.SubElement(root, f"{{{SVG_NS}}}defs")
        root.insert(0, defs)
    return defs


def remove_def(defs: etree._Element, def_id: str) -> None:
    """Remove all existing children of ``<defs>`` with the given id."""
    for child in list(defs):
        if child.get("id") == def_id:
            defs.remove(child)
