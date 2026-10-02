"""Pattern fill logic — apply hatching, dots, and custom patterns to SVG elements."""

from __future__ import annotations

from dataclasses import dataclass

from lxml import etree

from pathy_svg._constants import (
    SVG_NS,
    build_id_index,
    get_secure_parser,
    safe_svg_id,
    svg_sub,
)
from pathy_svg._paint import (
    get_or_create_defs,
    matched_items_ancestor_first,
    paint_targets,
    remove_def,
    set_fill,
    validate_opacity,
)
from pathy_svg.exceptions import ValidationError


@dataclass
class PatternSpec:
    """Specification for a built-in SVG pattern fill."""

    kind: str
    color: str = "#000000"
    background: str | None = None
    spacing: float = 6.0
    thickness: float = 1.0


@dataclass
class CustomPatternSpec(PatternSpec):
    """Specification for a custom SVG pattern with raw markup."""

    kind: str = "custom"
    markup: str = ""
    width: float = 10.0
    height: float = 10.0


def _validate_pattern_spec(pat_id: str, spec: PatternSpec) -> None:
    """Validate a pattern spec before modifying the tree. Raises on invalid input."""
    if isinstance(spec, CustomPatternSpec):
        try:
            etree.fromstring(
                f"<wrapper xmlns='{SVG_NS}'>{spec.markup}</wrapper>",
                parser=get_secure_parser(),
            )
        except etree.XMLSyntaxError as exc:
            raise ValidationError(
                f"Invalid custom pattern markup for '{pat_id}': {exc}"
            ) from exc
    elif spec.kind not in _PATTERN_BUILDERS:
        raise ValidationError(f"Unknown pattern kind: {spec.kind!r}")


def _build_pattern_element(
    defs: etree._Element, pat_id: str, spec: PatternSpec
) -> None:
    """Create a <pattern> element with the appropriate children."""
    if isinstance(spec, CustomPatternSpec):
        _build_custom_pattern(defs, pat_id, spec)
        return

    spacing = spec.spacing
    pat = svg_sub(defs, "pattern")
    pat.set("id", pat_id)
    pat.set("patternUnits", "userSpaceOnUse")
    pat.set("width", str(spacing))
    pat.set("height", str(spacing))

    if spec.background:
        bg = svg_sub(pat, "rect")
        bg.set("width", str(spacing))
        bg.set("height", str(spacing))
        bg.set("fill", spec.background)

    _PATTERN_BUILDERS[spec.kind](pat, spec)


def _build_custom_pattern(
    defs: etree._Element, pat_id: str, spec: CustomPatternSpec
) -> None:
    """Create a <pattern> element from raw SVG markup."""
    pat = svg_sub(defs, "pattern")
    pat.set("id", pat_id)
    pat.set("patternUnits", "userSpaceOnUse")
    pat.set("width", str(spec.width))
    pat.set("height", str(spec.height))

    if spec.background:
        bg = svg_sub(pat, "rect")
        bg.set("width", str(spec.width))
        bg.set("height", str(spec.height))
        bg.set("fill", spec.background)

    fragment = etree.fromstring(
        f"<wrapper xmlns='{SVG_NS}'>{spec.markup}</wrapper>",
        parser=get_secure_parser(),
    )
    for child in fragment:
        pat.append(child)


def _build_horizontal_lines(pat: etree._Element, spec: PatternSpec) -> None:
    line = svg_sub(pat, "line")
    line.set("x1", "0")
    line.set("y1", str(spec.spacing / 2))
    line.set("x2", str(spec.spacing))
    line.set("y2", str(spec.spacing / 2))
    line.set("stroke", spec.color)
    line.set("stroke-width", str(spec.thickness))


def _build_vertical_lines(pat: etree._Element, spec: PatternSpec) -> None:
    line = svg_sub(pat, "line")
    line.set("x1", str(spec.spacing / 2))
    line.set("y1", "0")
    line.set("x2", str(spec.spacing / 2))
    line.set("y2", str(spec.spacing))
    line.set("stroke", spec.color)
    line.set("stroke-width", str(spec.thickness))


def _build_diagonal_lines(pat: etree._Element, spec: PatternSpec) -> None:
    line = svg_sub(pat, "line")
    line.set("x1", "0")
    line.set("y1", str(spec.spacing))
    line.set("x2", str(spec.spacing))
    line.set("y2", "0")
    line.set("stroke", spec.color)
    line.set("stroke-width", str(spec.thickness))


def _build_crosshatch(pat: etree._Element, spec: PatternSpec) -> None:
    _build_horizontal_lines(pat, spec)
    _build_vertical_lines(pat, spec)


def _build_diagonal_crosshatch(pat: etree._Element, spec: PatternSpec) -> None:
    _build_diagonal_lines(pat, spec)
    line2 = svg_sub(pat, "line")
    line2.set("x1", "0")
    line2.set("y1", "0")
    line2.set("x2", str(spec.spacing))
    line2.set("y2", str(spec.spacing))
    line2.set("stroke", spec.color)
    line2.set("stroke-width", str(spec.thickness))


def _build_dots(pat: etree._Element, spec: PatternSpec) -> None:
    circle = svg_sub(pat, "circle")
    circle.set("cx", str(spec.spacing / 2))
    circle.set("cy", str(spec.spacing / 2))
    circle.set("r", str(spec.thickness))
    circle.set("fill", spec.color)


_PATTERN_BUILDERS = {
    "horizontal_lines": _build_horizontal_lines,
    "vertical_lines": _build_vertical_lines,
    "diagonal_lines": _build_diagonal_lines,
    "crosshatch": _build_crosshatch,
    "diagonal_crosshatch": _build_diagonal_crosshatch,
    "dots": _build_dots,
}


def apply_pattern_fill(
    tree: etree._ElementTree,
    patterns: dict[str, str | PatternSpec],
    *,
    opacity: float | None = None,
    preserve_stroke: bool = True,
    id_to_elem: dict[str, etree._Element] | None = None,
) -> None:
    """Apply pattern fills to SVG elements. Modifies tree in-place."""
    opacity = validate_opacity(opacity)
    if id_to_elem is None:
        id_to_elem = build_id_index(tree)

    defs = None

    for eid, spec_or_str, elem in matched_items_ancestor_first(patterns, id_to_elem):
        if isinstance(spec_or_str, str):
            spec = PatternSpec(kind=spec_or_str)
        else:
            spec = spec_or_str

        if defs is None:
            defs = get_or_create_defs(tree.getroot())

        pat_id = f"pathy-pat-{safe_svg_id(eid)}"
        _validate_pattern_spec(pat_id, spec)
        remove_def(defs, pat_id)
        _build_pattern_element(defs, pat_id, spec)

        for target in paint_targets(elem):
            set_fill(
                target,
                f"url(#{pat_id})",
                opacity=opacity,
                preserve_stroke=preserve_stroke,
            )
