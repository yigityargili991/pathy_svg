"""Mixin for gradient, pattern, stroke, highlight, and group aggregation methods."""

from __future__ import annotations


class StyleMixin:
    """Gradient fills, pattern fills, stroke mapping, highlight/dim, and group aggregation."""

    __slots__ = ()

    def gradient_fill(
        self,
        gradients,
        *,
        opacity: float | None = None,
        preserve_stroke: bool = True,
    ):
        """Apply gradient fills to elements by ID.

        Args:
            gradients: Dict mapping element IDs to GradientSpec objects.
            opacity: Opacity for the filled elements.
            preserve_stroke: Whether to preserve original stroke styling.

        Returns:
            A new SVGDocument with gradient fills applied.
        """
        from pathy_svg.gradient import apply_gradient_fill

        clone = self._clone()
        apply_gradient_fill(
            clone._tree,
            gradients,
            opacity=opacity,
            preserve_stroke=preserve_stroke,
            id_to_elem=clone._element_index,
        )
        return clone

    def pattern_fill(
        self,
        patterns,
        *,
        opacity: float | None = None,
        preserve_stroke: bool = True,
    ):
        """Apply pattern fills to elements by ID.

        Args:
            patterns: Dict mapping element IDs to PatternSpec objects or pattern name strings.
            opacity: Opacity for the filled elements.
            preserve_stroke: Whether to preserve original stroke styling.

        Returns:
            A new SVGDocument with pattern fills applied.
        """
        from pathy_svg.pattern import apply_pattern_fill

        clone = self._clone()
        apply_pattern_fill(
            clone._tree,
            patterns,
            opacity=opacity,
            preserve_stroke=preserve_stroke,
            id_to_elem=clone._element_index,
        )
        return clone

    def stroke_map(
        self,
        data: dict[str, float],
        *,
        width_range: tuple[float, float] | None = (1.0, 5.0),
        palette: str | None = None,
        vmin: float | None = None,
        vmax: float | None = None,
        opacity: float | None = None,
        na_width: float = 1.0,
        na_color: str | None = None,
    ):
        """Map data to stroke width and/or color.

        Args:
            data: Dict mapping element IDs to numeric values.
            width_range: Min/max stroke width. None to skip width mapping.
            palette: Colormap name for stroke color. None to skip color mapping.
            vmin: Minimum value for the scale.
            vmax: Maximum value for the scale.
            opacity: Stroke opacity.
            na_width: Stroke width for NaN values.
            na_color: Stroke color for NaN values.

        Returns:
            A new SVGDocument with stroke mapping applied.
        """
        from pathy_svg.stroke import apply_stroke_map

        clone = self._clone()
        scale = apply_stroke_map(
            clone._tree,
            data,
            width_range=width_range,
            palette=palette,
            vmin=vmin,
            vmax=vmax,
            opacity=opacity,
            na_width=na_width,
            na_color=na_color,
            id_to_elem=clone._element_index,
        )
        if scale is not None:
            clone._last_scale = scale
        return clone

    def highlight(
        self,
        ids,
        *,
        dim_opacity: float = 0.2,
        desaturate: bool = True,
    ):
        """Highlight specified elements, dim all others.

        Args:
            ids: List or set of element IDs to highlight.
            dim_opacity: Opacity for dimmed elements.
            desaturate: Whether to convert dimmed elements to greyscale.

        Returns:
            A new SVGDocument with highlighting applied.
        """
        from pathy_svg.highlight import apply_highlight

        clone = self._clone()
        apply_highlight(
            clone._tree,
            set(ids),
            dim_opacity=dim_opacity,
            desaturate=desaturate,
            id_to_elem=clone._element_index,
        )
        return clone

    def heatmap_groups(
        self,
        data: dict[str, float],
        *,
        agg: str = "mean",
        palette: str | list[str] = "RdYlBu_r",
        vmin: float | None = None,
        vmax: float | None = None,
        vcenter: float | None = None,
        na_color: str = "#cccccc",
        breaks: list[float] | None = None,
        opacity: float | None = None,
        preserve_stroke: bool = True,
    ):
        """Color groups by aggregating their children's data values.

        Args:
            data: Dict mapping child element IDs to numeric values.
            agg: Aggregation function ("mean", "sum", "min", "max", "median").
            palette: Colormap name or list of hex colors.
            vmin: Minimum value for the color scale.
            vmax: Maximum value for the color scale.
            vcenter: Center value for diverging color scales.
            na_color: Color for groups with no data.
            breaks: Boundary values for discrete color scales.
            opacity: Opacity for colored groups.
            preserve_stroke: Whether to preserve original stroke styling.

        Returns:
            A new SVGDocument with group-aggregated coloring applied.
        """
        from pathy_svg.coloring import aggregate_by_group, apply_heatmap

        clone = self._clone()
        group_data = aggregate_by_group(clone._tree, data, agg=agg)
        scale = apply_heatmap(
            clone._tree,
            group_data,
            palette=palette,
            vmin=vmin,
            vmax=vmax,
            vcenter=vcenter,
            na_color=na_color,
            breaks=breaks,
            opacity=opacity,
            preserve_stroke=preserve_stroke,
            color_missing=False,
            id_to_elem=clone._element_index,
        )
        clone._last_scale = scale
        return clone
