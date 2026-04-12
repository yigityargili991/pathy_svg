"""Gradient fill logic — apply linear gradients to individual SVG elements."""

from __future__ import annotations

from dataclasses import dataclass

from lxml import etree

from pathy_svg._constants import COLORABLE_TAGS, SVG_NS, build_id_index, local_tag, safe_svg_id, svg_sub
from pathy_svg._css import set_style_property

DIRECTION_MAP = {
    "horizontal": ("0", "0", "1", "0"),
    "vertical": ("0", "0", "0", "1"),
    "diagonal": ("0", "0", "1", "1"),
}


@dataclass
class GradientSpec:
    """Specification for a linear gradient fill."""

    start: str
    end: str
    direction: str = "horizontal"
    mid: str | None = None


def _get_or_create_defs(tree: etree._ElementTree) -> etree._Element:
    """Find or create the <defs> element in the SVG root."""
    root = tree.getroot()
    ns = f"{{{SVG_NS}}}"
    defs = root.find(f"{ns}defs")
    if defs is None:
        defs = etree.SubElement(root, f"{ns}defs")
        root.insert(0, defs)
    return defs


def _remove_existing_def(defs: etree._Element, def_id: str) -> None:
    """Remove all existing children of <defs> with the given id."""
    for child in list(defs):
        if child.get("id") == def_id:
            defs.remove(child)


def _create_gradient_element(
    defs: etree._Element, grad_id: str, spec: GradientSpec
) -> None:
    """Create a <linearGradient> element with stops in <defs>."""
    x1, y1, x2, y2 = DIRECTION_MAP.get(spec.direction, DIRECTION_MAP["horizontal"])
    grad = svg_sub(defs, "linearGradient")
    grad.set("id", grad_id)
    grad.set("x1", x1)
    grad.set("y1", y1)
    grad.set("x2", x2)
    grad.set("y2", y2)

    stop0 = svg_sub(grad, "stop")
    stop0.set("offset", "0")
    stop0.set("style", f"stop-color:{spec.start}")

    if spec.mid is not None:
        stop_mid = svg_sub(grad, "stop")
        stop_mid.set("offset", "0.5")
        stop_mid.set("style", f"stop-color:{spec.mid}")

    stop1 = svg_sub(grad, "stop")
    stop1.set("offset", "1")
    stop1.set("style", f"stop-color:{spec.end}")


def _set_gradient_ref(
    element: etree._Element,
    grad_id: str,
    *,
    opacity: float | None = None,
    preserve_stroke: bool = True,
) -> None:
    """Set an element's fill to reference a gradient."""
    ref = f"url(#{grad_id})"
    element.set("fill", ref)
    style = set_style_property(element.get("style"), "fill", ref)
    if opacity is not None and opacity < 1.0:
        element.set("fill-opacity", str(opacity))
        style = set_style_property(style, "fill-opacity", str(opacity))
    if not preserve_stroke:
        element.set("stroke", "none")
        style = set_style_property(style, "stroke", "none")
    element.set("style", style)


def apply_gradient_fill(
    tree: etree._ElementTree,
    gradients: dict[str, GradientSpec],
    *,
    opacity: float | None = None,
    preserve_stroke: bool = True,
    id_to_elem: dict[str, etree._Element] | None = None,
) -> None:
    """Apply gradient fills to SVG elements. Modifies tree in-place."""
    if id_to_elem is None:
        id_to_elem = build_id_index(tree)

    defs = None  # lazily created

    for eid, spec in gradients.items():
        elem = id_to_elem.get(eid)
        if elem is None:
            continue

        if defs is None:
            defs = _get_or_create_defs(tree)

        grad_id = f"pathy-grad-{safe_svg_id(eid)}"
        _remove_existing_def(defs, grad_id)
        _create_gradient_element(defs, grad_id, spec)

        kwargs = {"opacity": opacity, "preserve_stroke": preserve_stroke}
        if local_tag(elem.tag) == "g":
            for child in elem.iter():
                if child is not elem and local_tag(child.tag) in COLORABLE_TAGS:
                    _set_gradient_ref(child, grad_id, **kwargs)
        else:
            _set_gradient_ref(elem, grad_id, **kwargs)
