"""Mixin for legend, annotation, animation, diff, and comparison methods."""

from __future__ import annotations

from lxml import etree

from pathy_svg._constants import SVG_NS
from pathy_svg.transform import ViewBox


class OverlayMixin:
    """Legend, annotation, tooltip, animation, diff, and comparison methods."""

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

    def diff(
        self,
        baseline: dict[str, float],
        treatment: dict[str, float],
        *,
        mode: str = "delta",
        palette: str | list[str] = "coolwarm",
        vcenter: float | None = 0,
        vmin: float | None = None,
        vmax: float | None = None,
        **heatmap_kwargs,
    ):
        """Compute per-path differences and apply as a heatmap.

        Args:
            baseline: Data dict for the baseline state.
            treatment: Data dict for the treatment state.
            mode: The difference mode ("delta", "percent", or "ratio").
            palette: Name of a matplotlib diverging colormap or a list of hex colors.
            vcenter: Center value for the diverging color scale (typically 0).
            vmin: Minimum value for the color scale.
            vmax: Maximum value for the color scale.
            **heatmap_kwargs: Additional arguments passed to `heatmap`.

        Returns:
            A new SVGDocument with the diff heatmap applied.
        """
        from pathy_svg.diff import compute_diff

        diff_data = compute_diff(baseline, treatment, mode=mode)
        return self.heatmap(
            diff_data,
            palette=palette,
            vcenter=vcenter,
            vmin=vmin,
            vmax=vmax,
            **heatmap_kwargs,
        )

    def compare(
        self,
        datasets: dict[str, dict[str, float]],
        *,
        palette: str | list[str] = "YlOrRd",
        layout: str = "horizontal",
        spacing: float = 20,
        **heatmap_kwargs,
    ):
        """Create side-by-side comparison of multiple datasets.

        Args:
            datasets: A mapping of dataset names to data dicts.
            palette: Name of a matplotlib colormap or a list of hex colors.
            layout: Layout orientation ("horizontal" or "vertical").
            spacing: Spacing between SVGs in viewBox units.
            **heatmap_kwargs: Additional arguments passed to `heatmap`.

        Returns:
            A new merged SVGDocument containing the compared maps.
        """
        from pathy_svg.diff import compose_side_by_side

        colored_docs = []
        titles = []
        for name, data in datasets.items():
            titles.append(name)
            colored_docs.append(self.heatmap(data, palette=palette, **heatmap_kwargs))

        new_tree = compose_side_by_side(
            colored_docs,
            titles=titles,
            layout=layout,
            spacing=spacing,
        )
        return type(self)(new_tree)

    def animate(
        self,
        *,
        effect: str = "pulse",
        duration: float = 2.0,
        delay_by: str = "value",
        loop: bool = True,
    ):
        """Inject CSS animation into the SVG.

        Args:
            effect: The animation effect to apply (e.g. "pulse").
            duration: Animation duration in seconds.
            delay_by: Strategy for stagger delays ("value" or None).
            loop: Whether the animation should loop infinitely.

        Returns:
            A new SVGDocument with the CSS animation injected.
        """
        from pathy_svg.animation import inject_animation

        clone = self._clone()
        inject_animation(
            clone._tree,
            clone._nsmap,
            effect=effect,
            duration=duration,
            delay_by=delay_by,
            loop=loop,
            data_order=None,
        )
        return clone

    def annotate(
        self,
        labels: dict[str, str],
        *,
        placement: str = "centroid",
        font_size: float = 12,
        font_color: str = "black",
        font_family: str = "sans-serif",
        background: str | None = None,
        offset: tuple[float, float] = (0, 0),
    ):
        """Add text labels to paths.

        Args:
            labels: A dictionary mapping path IDs to text labels.
            placement: Placement strategy for the text ("centroid" or other supported strategies).
            font_size: Font size for the labels.
            font_color: Font color for the labels.
            font_family: CSS font-family string.
            background: Optional background color for the text (creates a bounding box).
            offset: An (x, y) tuple specifying offset for the text placement.

        Returns:
            A new SVGDocument with the text labels added.
        """
        from pathy_svg.annotations import add_text_labels

        clone = self._clone()
        add_text_labels(
            clone._tree,
            clone._nsmap,
            labels,
            placement=placement,
            font_size=font_size,
            font_color=font_color,
            font_family=font_family,
            background=background,
            offset=offset,
        )
        return clone

    def add_tooltips(
        self,
        tips: dict[str, str],
        *,
        method: str = "title",
    ):
        """Add tooltips to paths.

        Args:
            tips: A dictionary mapping path IDs to tooltip text.
            method: The method to inject tooltips ("title" for `<title>` tags).

        Returns:
            A new SVGDocument with the tooltips injected.
        """
        from pathy_svg.annotations import add_tooltips

        clone = self._clone()
        add_tooltips(clone._tree, clone._nsmap, tips, method=method)
        return clone

    def replace_text(
        self,
        replacements: dict[str, str],
        *,
        text_color: str | None = None,
    ):
        """Replace text content in <text> elements.

        Args:
            replacements: A dictionary mapping existing text content to new text.
            text_color: Optional hex color string to apply to the modified text.

        Returns:
            A new SVGDocument with the text replaced.
        """
        from pathy_svg.annotations import replace_text

        clone = self._clone()
        replace_text(clone._tree, clone._nsmap, replacements, text_color=text_color)
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
