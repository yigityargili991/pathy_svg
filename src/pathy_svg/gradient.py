"""Gradient fill logic — apply linear gradients to individual SVG elements."""

from __future__ import annotations

from dataclasses import dataclass

from lxml import etree

from pathy_svg._constants import build_id_index, safe_svg_id, svg_sub
from pathy_svg._paint import (
    get_or_create_defs,
    matched_items_ancestor_first,
    paint_targets,
    remove_def,
    set_fill,
    validate_opacity,
)
from pathy_svg.exceptions import ValidationError

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

    def __post_init__(self) -> None:
        if self.direction not in DIRECTION_MAP:
            raise ValidationError(f"Unknown gradient direction: {self.direction!r}")


def _create_gradient_element(
    defs: etree._Element, grad_id: str, spec: GradientSpec
) -> None:
    """Create a <linearGradient> element with stops in <defs>."""
    x1, y1, x2, y2 = DIRECTION_MAP[spec.direction]
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


def apply_gradient_fill(
    tree: etree._ElementTree,
    gradients: dict[str, GradientSpec],
    *,
    opacity: float | None = None,
    preserve_stroke: bool = True,
    id_to_elem: dict[str, etree._Element] | None = None,
) -> None:
    """Apply gradient fills to SVG elements. Modifies tree in-place."""
    opacity = validate_opacity(opacity)
    if id_to_elem is None:
        id_to_elem = build_id_index(tree)

    defs = None  # lazily created

    for eid, spec, elem in matched_items_ancestor_first(gradients, id_to_elem):
        if defs is None:
            defs = get_or_create_defs(tree.getroot())

        grad_id = f"pathy-grad-{safe_svg_id(eid)}"
        remove_def(defs, grad_id)
        _create_gradient_element(defs, grad_id, spec)

        for target in paint_targets(elem):
            set_fill(
                target,
                f"url(#{grad_id})",
                opacity=opacity,
                preserve_stroke=preserve_stroke,
            )
