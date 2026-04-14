"""Pattern fill logic — apply hatching, dots, and custom patterns to SVG elements."""

from __future__ import annotations

from dataclasses import dataclass

from lxml import etree

from pathy_svg._constants import (
    COLORABLE_TAGS,
    SVG_NS,
    build_id_index,
    get_secure_parser,
    local_tag,
    safe_svg_id,
    svg_sub,
)
from pathy_svg._css import set_style_property
from pathy_svg.gradient import _get_or_create_defs, _remove_existing_def


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
            raise ValueError(
                f"Invalid custom pattern markup for '{pat_id}': {exc}"
            ) from exc
    elif spec.kind not in _PATTERN_BUILDERS:
        raise ValueError(f"Unknown pattern kind: {spec.kind!r}")


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


def _set_pattern_ref(
    element: etree._Element,
    pat_id: str,
    *,
    opacity: float | None = None,
    preserve_stroke: bool = True,
) -> None:
    """Set an element's fill to reference a pattern."""
    ref = f"url(#{pat_id})"
    element.set("fill", ref)
    style = set_style_property(element.get("style"), "fill", ref)
    if opacity is not None and opacity < 1.0:
        element.set("fill-opacity", str(opacity))
        style = set_style_property(style, "fill-opacity", str(opacity))
    if not preserve_stroke:
        element.set("stroke", "none")
        style = set_style_property(style, "stroke", "none")
    element.set("style", style)


def apply_pattern_fill(
    tree: etree._ElementTree,
    patterns: dict[str, str | PatternSpec],
    *,
    opacity: float | None = None,
    preserve_stroke: bool = True,
    id_to_elem: dict[str, etree._Element] | None = None,
) -> None:
    """Apply pattern fills to SVG elements. Modifies tree in-place."""
    if id_to_elem is None:
        id_to_elem = build_id_index(tree)

    defs = None

    for eid, spec_or_str in patterns.items():
        elem = id_to_elem.get(eid)
        if elem is None:
            continue

        if isinstance(spec_or_str, str):
            spec = PatternSpec(kind=spec_or_str)
        else:
            spec = spec_or_str

        if defs is None:
            defs = _get_or_create_defs(tree)

        pat_id = f"pathy-pat-{safe_svg_id(eid)}"
        _validate_pattern_spec(pat_id, spec)
        _remove_existing_def(defs, pat_id)
        _build_pattern_element(defs, pat_id, spec)

        kwargs = {"opacity": opacity, "preserve_stroke": preserve_stroke}
        if local_tag(elem.tag) == "g":
            for child in elem.iter():
                if child is not elem and local_tag(child.tag) in COLORABLE_TAGS:
                    _set_pattern_ref(child, pat_id, **kwargs)
        else:
            _set_pattern_ref(elem, pat_id, **kwargs)
