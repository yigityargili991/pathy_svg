"""Mixin for legend methods."""

from __future__ import annotations

from lxml import etree

from pathy_svg._constants import SVG_NS
from pathy_svg.legend import (
    _GENERATED_LEGEND_ATTR,
    _GENERATED_LEGEND_VALUE,
    Direction,
    LegendKind,
    _build_legend_layout,
    resolve_legend_kind,
)
from pathy_svg.themes import CategoricalPalette, ColorScale
from pathy_svg.transform import ViewBox


class LegendMixin:
    """Legend methods."""

    __slots__ = ()

    def legend(
        self,
        *,
        kind: LegendKind = "auto",
        scale: ColorScale | None = None,
        palette: CategoricalPalette | None = None,
        position: tuple[float, float] = (0.85, 0.1),
        size: tuple[float, float] = (0.04, 0.4),
        direction: Direction = "vertical",
        num_ticks: int = 5,
        tick_format: str = "{:.2f}",
        labels: list[str] | None = None,
        font_size: float | None = None,
        font_color: str = "black",
        font_family: str = "sans-serif",
        title: str | None = None,
        title_size: float | None = None,
        border: bool = False,
        border_color: str = "#333",
        background: str | None = None,
        padding: float = 5,
        expand_viewbox: bool = True,
    ):
        """Add a legend to the SVG.

        Args:
            kind: Type of legend to add ("auto", "gradient", "discrete", "categorical").
            scale: Optional explicit ColorScale to use (overrides auto-detection).
            palette: Optional explicit CategoricalPalette to use (overrides auto-detection).
            position: Relative (x, y) coordinates for the legend origin. Values
                outside 0-1 place the legend beyond the source viewBox.
            size: Relative (width, height) for the legend bounds (0-1 range).
            direction: Legend orientation ("vertical" or "horizontal").
            num_ticks: Number of ticks for continuous scales.
            tick_format: Formatting string for the tick labels.
            labels: Optional custom list of labels.
            font_size: Font size for labels.
            font_color: Font color for labels.
            font_family: CSS font family.
            title: Title for the legend.
            title_size: Font size for the title.
            border: Whether to draw a border around the legend.
            border_color: Color of the legend border.
            background: Background color of the legend area.
            padding: Padding inside the legend area.
            expand_viewbox: Whether to auto-extend the viewBox to fit the legend (default ``True``).

        Returns:
            A new SVGDocument containing the legend element.
        """
        clone = self._clone()
        root = clone._root
        source_attrs = _restore_source_canvas(root)
        vb = clone.viewbox
        if vb is None:
            w, h = clone.dimensions
            vb = ViewBox(0, 0, w or 500, h or 500)

        chosen_scale = scale if scale is not None else clone._last_scale
        chosen_palette = (
            palette if palette is not None else clone._last_categorical_palette
        )
        resolved = resolve_legend_kind(kind, chosen_scale, chosen_palette)
        built = _build_legend_layout(
            resolved,
            chosen_scale,
            chosen_palette,
            vb,
            position=position,
            size=size,
            direction=direction,
            num_ticks=num_ticks,
            tick_format=tick_format,
            labels=labels,
            font_size=font_size,
            font_color=font_color,
            font_family=font_family,
            title=title,
            title_size=title_size,
            border=border,
            border_color=border_color,
            background=background,
            padding=padding,
        )

        if expand_viewbox:
            bounds = built.bounds
            x1 = min(vb.x, bounds.x)
            y1 = min(vb.y, bounds.y)
            x2 = max(vb.x + vb.width, bounds.x + bounds.width)
            y2 = max(vb.y + vb.height, bounds.y + bounds.height)
            expanded = ViewBox(x1, y1, x2 - x1, y2 - y1)
            root.set(
                "viewBox",
                f"{expanded.x} {expanded.y} {expanded.width} {expanded.height}",
            )
            if expanded.width != vb.width:
                root.set("width", str(expanded.width))
            if expanded.height != vb.height:
                root.set("height", str(expanded.height))

        built.element.set("id", _unique_legend_id(root))
        _store_source_canvas(built.element, source_attrs)
        root.append(built.element)
        return clone


_CANVAS_ATTRS = ("viewBox", "width", "height")
_PRIVATE_NS = "urn:pathy-svg:private:legend:v1"
_PROVENANCE_ATTR = f"{{{_PRIVATE_NS}}}provenance"
_PROVENANCE_VALUE = "pathy-generated-legend-v1"


def _private_attr(name: str) -> str:
    return f"{{{_PRIVATE_NS}}}{name}"


def _store_source_canvas(
    legend: etree._Element, source_attrs: dict[str, str | None]
) -> None:
    """Attach the complete private ownership and source-canvas schema."""
    legend.set(_PROVENANCE_ATTR, _PROVENANCE_VALUE)
    for attr in _CANVAS_ATTRS:
        value = source_attrs[attr]
        legend.set(
            _private_attr(f"source-{attr.lower()}-present"), str(value is not None)
        )
        if value is not None:
            legend.set(_private_attr(f"source-{attr.lower()}"), value)


def _generated_legend_id(element_id: str | None) -> bool:
    if element_id == "pathy-legend":
        return True
    prefix = "pathy-legend-"
    return bool(
        element_id
        and element_id.startswith(prefix)
        and element_id[len(prefix) :].isdigit()
    )


def _owned_generated_legend(element: etree._Element) -> bool:
    """Recognize only legends carrying our complete private metadata schema."""
    if element.tag != f"{{{SVG_NS}}}g":
        return False
    if not _generated_legend_id(element.get("id")):
        return False
    if element.get(_GENERATED_LEGEND_ATTR) != _GENERATED_LEGEND_VALUE:
        return False
    if element.get(_PROVENANCE_ATTR) != _PROVENANCE_VALUE:
        return False
    for attr in _CANVAS_ATTRS:
        present = element.get(_private_attr(f"source-{attr.lower()}-present"))
        value = element.get(_private_attr(f"source-{attr.lower()}"))
        if present not in ("True", "False"):
            return False
        if present == "True" and value is None:
            return False
        if present == "False" and value is not None:
            return False
    return True


def _restore_source_canvas(root: etree._Element) -> dict[str, str | None]:
    """Remove our prior direct-child legend and restore its source canvas."""
    generated = [child for child in root if _owned_generated_legend(child)]
    if not generated:
        return {attr: root.get(attr) for attr in _CANVAS_ATTRS}

    previous = generated[0]
    source_attrs = {
        attr: (
            previous.get(_private_attr(f"source-{attr.lower()}"))
            if previous.get(_private_attr(f"source-{attr.lower()}-present")) == "True"
            else None
        )
        for attr in _CANVAS_ATTRS
    }
    for attr, stored in source_attrs.items():
        if stored is not None:
            root.set(attr, stored)
        else:
            root.attrib.pop(attr, None)
    for child in generated:
        root.remove(child)
    return source_attrs


def _unique_legend_id(root: etree._Element) -> str:
    used = {element.get("id") for element in root.iter() if element.get("id")}
    base = "pathy-legend"
    if base not in used:
        return base
    suffix = 2
    while f"{base}-{suffix}" in used:
        suffix += 1
    return f"{base}-{suffix}"
