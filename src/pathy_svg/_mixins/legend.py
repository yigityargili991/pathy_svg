"""Mixin for legend methods."""

from __future__ import annotations

from pathy_svg.legend import Direction, LegendKind

from lxml import etree

from pathy_svg._constants import SVG_NS
from pathy_svg.transform import ViewBox


class LegendMixin:
    """Legend methods."""

    __slots__ = ()

    def legend(
        self,
        *,
        kind: LegendKind = "auto",
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
            position: Relative (x, y) coordinates for the legend origin (0-1 range).
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
        from pathy_svg.legend import build_legend, resolve_legend_kind

        clone = self._clone()
        vb = clone.viewbox
        if vb is None:
            w, h = clone.dimensions
            vb = ViewBox(0, 0, w or 500, h or 500)

        if expand_viewbox:
            if direction == "vertical":
                legend_right = position[0] + size[0]
                if legend_right > 0.80:
                    extra = vb.width * (legend_right - 0.80 + 0.15)
                    new_width = vb.width + extra
                    vb = ViewBox(vb.x, vb.y, new_width, vb.height)
                    clone.root.set("viewBox", f"{vb.x} {vb.y} {vb.width} {vb.height}")
                    clone.root.set("width", str(vb.width))
            else:
                legend_bottom = position[1] + size[1]
                if legend_bottom > 0.80:
                    extra = vb.height * (legend_bottom - 0.80 + 0.15)
                    new_height = vb.height + extra
                    vb = ViewBox(vb.x, vb.y, vb.width, new_height)
                    clone.root.set("viewBox", f"{vb.x} {vb.y} {vb.width} {vb.height}")
                    clone.root.set("height", str(vb.height))

        resolved = resolve_legend_kind(
            kind, self._last_scale, self._last_categorical_palette
        )
        legend_elem = build_legend(
            resolved,
            self._last_scale,
            self._last_categorical_palette,
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
        clone.root.append(legend_elem)
        return clone
