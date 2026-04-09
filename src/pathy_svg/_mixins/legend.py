"""Mixin for legend and coordinate guide methods."""

from __future__ import annotations

from lxml import etree

from pathy_svg._constants import SVG_NS
from pathy_svg.transform import ViewBox


class LegendMixin:
    """Legend and coordinate guide methods."""

    __slots__ = ()

    def legend(
        self,
        *,
        kind: str = "auto",
        position: tuple[float, float] = (0.85, 0.1),
        size: tuple[float, float] = (0.04, 0.4),
        direction: str = "vertical",
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

        Returns:
            A new SVGDocument containing the legend element.
        """
        from pathy_svg.legend import build_legend, resolve_legend_kind

        clone = self._clone()
        vb = clone.viewbox or ViewBox(0, 0, 500, 500)
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

    def xy_guide(self, *, color: str = "red", step: float = 50):
        """Return a copy with a coordinate grid overlay for orientation."""
        clone = self._clone()
        vb = clone.viewbox
        if vb is None:
            return clone

        root = clone.root
        ns = root.nsmap.get(None, SVG_NS)
        g = etree.SubElement(root, f"{{{ns}}}g" if ns else "g", id="pathy-guide")
        g.set("style", f"stroke:{color};stroke-width:0.5;fill:none;opacity:0.5")

        x = vb.x
        while x <= vb.x + vb.width:
            line = etree.SubElement(g, f"{{{ns}}}line" if ns else "line")
            line.set("x1", str(x))
            line.set("y1", str(vb.y))
            line.set("x2", str(x))
            line.set("y2", str(vb.y + vb.height))
            txt = etree.SubElement(g, f"{{{ns}}}text" if ns else "text")
            txt.set("x", str(x + 2))
            txt.set("y", str(vb.y + 12))
            txt.set("style", f"fill:{color};font-size:8px;stroke:none")
            txt.text = str(int(x))
            x += step

        y = vb.y
        while y <= vb.y + vb.height:
            line = etree.SubElement(g, f"{{{ns}}}line" if ns else "line")
            line.set("x1", str(vb.x))
            line.set("y1", str(y))
            line.set("x2", str(vb.x + vb.width))
            line.set("y2", str(y))
            txt = etree.SubElement(g, f"{{{ns}}}text" if ns else "text")
            txt.set("x", str(vb.x + 2))
            txt.set("y", str(y - 2))
            txt.set("style", f"fill:{color};font-size:8px;stroke:none")
            txt.text = str(int(y))
            y += step

        return clone
