"""Mixin for gradient, pattern, stroke, highlight, and group aggregation methods."""

from __future__ import annotations

from collections.abc import Callable, Collection
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathy_svg.gradient import GradientSpec
    from pathy_svg.pattern import PatternSpec


class StyleMixin:
    """Gradient fills, pattern fills, stroke mapping, highlight/dim, and group aggregation."""

    __slots__ = ()

    def gradient_fill(
        self,
        gradients: dict[str, GradientSpec],
        *,
        opacity: float | None = None,
        preserve_stroke: bool = True,
        key_attr: str = "id",
    ):
        """Apply gradient fills to elements.

        Args:
            gradients: Dict mapping element attribute values to GradientSpec objects.
            opacity: Opacity for the filled elements.
            preserve_stroke: Whether to preserve original stroke styling.
            key_attr: Element attribute used to match data keys (default ``"id"``).

        Returns:
            A new SVGDocument with gradient fills applied.
        """
        from pathy_svg.gradient import apply_gradient_fill

        clone = self._clone()
        resolved_grads, resolved_index = clone._resolve_key_attr(gradients, key_attr)
        apply_gradient_fill(
            clone._tree,
            resolved_grads,
            opacity=opacity,
            preserve_stroke=preserve_stroke,
            id_to_elem=resolved_index,
        )
        return clone

    def pattern_fill(
        self,
        patterns: dict[str, str | PatternSpec],
        *,
        opacity: float | None = None,
        preserve_stroke: bool = True,
        key_attr: str = "id",
    ):
        """Apply pattern fills to elements.

        Args:
            patterns: Dict mapping element attribute values to PatternSpec objects or pattern name strings.
            opacity: Opacity for the filled elements.
            preserve_stroke: Whether to preserve original stroke styling.
            key_attr: Element attribute used to match data keys (default ``"id"``).

        Returns:
            A new SVGDocument with pattern fills applied.
        """
        from pathy_svg.pattern import apply_pattern_fill

        clone = self._clone()
        resolved_pats, resolved_index = clone._resolve_key_attr(patterns, key_attr)
        apply_pattern_fill(
            clone._tree,
            resolved_pats,
            opacity=opacity,
            preserve_stroke=preserve_stroke,
            id_to_elem=resolved_index,
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
        key_attr: str = "id",
    ):
        """Map data to stroke width and/or color.

        Args:
            data: Dict mapping element attribute values to numeric values.
            width_range: Min/max stroke width. None to skip width mapping.
            palette: Colormap name for stroke color. None to skip color mapping.
            vmin: Minimum value for the scale.
            vmax: Maximum value for the scale.
            opacity: Stroke opacity.
            na_width: Stroke width for NaN values.
            na_color: Stroke color for NaN values.
            key_attr: Element attribute used to match data keys (default ``"id"``).

        Returns:
            A new SVGDocument with stroke mapping applied.
        """
        from pathy_svg.stroke import apply_stroke_map

        clone = self._clone()
        resolved_data, resolved_index = clone._resolve_key_attr(data, key_attr)
        scale = apply_stroke_map(
            clone._tree,
            resolved_data,
            width_range=width_range,
            palette=palette,
            vmin=vmin,
            vmax=vmax,
            opacity=opacity,
            na_width=na_width,
            na_color=na_color,
            id_to_elem=resolved_index,
        )
        if scale is not None:
            clone._last_scale = scale
        return clone

    def highlight(
        self,
        ids: Collection[str],
        *,
        dim_opacity: float = 0.2,
        desaturate: bool = True,
        key_attr: str = "id",
    ):
        """Highlight specified elements, dim all others.

        Args:
            ids: List or set of element attribute values to highlight.
            dim_opacity: Opacity for dimmed elements.
            desaturate: Whether to convert dimmed elements to greyscale.
            key_attr: Element attribute used to match data keys (default ``"id"``).

        Returns:
            A new SVGDocument with highlighting applied.
        """
        from pathy_svg.highlight import apply_highlight

        clone = self._clone()
        dummy = {k: True for k in ids}
        resolved_dummy, resolved_index = clone._resolve_key_attr(dummy, key_attr)
        apply_highlight(
            clone._tree,
            set(resolved_dummy.keys()),
            dim_opacity=dim_opacity,
            desaturate=desaturate,
            id_to_elem=resolved_index,
        )
        return clone

    def heatmap_groups(
        self,
        data: dict[str, float],
        *,
        agg: str | Callable[[list[float]], float] = "mean",
        palette: str | list[str] = "RdYlBu_r",
        vmin: float | None = None,
        vmax: float | None = None,
        vcenter: float | None = None,
        na_color: str = "#cccccc",
        breaks: list[float] | None = None,
        opacity: float | None = None,
        preserve_stroke: bool = True,
        key_attr: str = "id",
    ):
        """Color groups by aggregating their children's data values.

        Args:
            data: Dict mapping child element attribute values to numeric values.
            agg: Aggregation function name ("mean", "sum", "min", "max", "median")
                or a callable that takes a list of floats and returns a float.
            palette: Colormap name or list of hex colors.
            vmin: Minimum value for the color scale.
            vmax: Maximum value for the color scale.
            vcenter: Center value for diverging color scales.
            na_color: Color for NaN values within groups.
            breaks: Boundary values for discrete color scales.
            opacity: Opacity for colored groups.
            preserve_stroke: Whether to preserve original stroke styling.
            key_attr: Element attribute used to match data keys (default ``"id"``).

        Returns:
            A new SVGDocument with group-aggregated coloring applied.
        """
        from pathy_svg.coloring import aggregate_by_group, apply_heatmap

        clone = self._clone()
        group_data = aggregate_by_group(
            clone._tree, data, agg=agg, key_attr=key_attr,
        )
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
