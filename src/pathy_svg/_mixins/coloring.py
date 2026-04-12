"""Mixin for data-driven coloring methods."""

from __future__ import annotations


class ColoringMixin:
    """Heatmap, recolor, and categorical coloring methods."""

    __slots__ = ()

    def heatmap(
        self,
        data: dict[str, float],
        *,
        palette: str | list[str] = "RdYlBu_r",
        vmin: float | None = None,
        vmax: float | None = None,
        vcenter: float | None = None,
        na_color: str = "#cccccc",
        breaks: list[float] | None = None,
        opacity: float | None = None,
        preserve_stroke: bool = True,
        color_missing: bool = True,
        key_attr: str = "id",
    ):
        """Apply data-driven coloring to paths.

        Args:
            data: Data dict mapping element attribute values to numeric values.
            palette: Name of a matplotlib colormap or a list of hex colors.
            vmin: Minimum value for the color scale.
            vmax: Maximum value for the color scale.
            vcenter: Center value for diverging color scales.
            na_color: Color to use for missing or NaN values.
            breaks: List of boundary values for discrete color scales.
            opacity: Opacity for the filled paths.
            preserve_stroke: Whether to preserve original stroke styling.
            color_missing: Whether to color paths that are not in the data with `na_color`.
            key_attr: Element attribute used to match data keys (default ``"id"``).

        Returns:
            A new SVGDocument with the heatmap applied.
        """
        from pathy_svg.coloring import apply_heatmap

        clone = self._clone()
        resolved_data, resolved_index = clone._resolve_key_attr(data, key_attr)
        scale = apply_heatmap(
            clone._tree,
            resolved_data,
            palette=palette,
            vmin=vmin,
            vmax=vmax,
            vcenter=vcenter,
            na_color=na_color,
            breaks=breaks,
            opacity=opacity,
            preserve_stroke=preserve_stroke,
            color_missing=color_missing,
            id_to_elem=resolved_index,
        )
        clone._last_scale = scale
        return clone

    def heatmap_from_dataframe(
        self,
        df,
        *,
        id_col: str,
        value_col: str,
        palette: str | list[str] = "RdYlBu_r",
        vmin: float | None = None,
        vmax: float | None = None,
        vcenter: float | None = None,
        na_color: str = "#cccccc",
        breaks: list[float] | None = None,
        opacity: float | None = None,
        preserve_stroke: bool = True,
        color_missing: bool = True,
        key_attr: str = "id",
    ):
        """Apply data-driven coloring from a Pandas DataFrame.

        Args:
            df: A Pandas DataFrame containing the data.
            id_col: Column name for element attribute values.
            value_col: Column name for numeric values.
            palette: Name of a matplotlib colormap or a list of hex colors.
            vmin: Minimum value for the color scale.
            vmax: Maximum value for the color scale.
            vcenter: Center value for diverging color scales.
            na_color: Color to use for missing or NaN values.
            breaks: List of boundary values for discrete color scales.
            opacity: Opacity for the filled paths.
            preserve_stroke: Whether to preserve original stroke styling.
            color_missing: Whether to color paths that are not in the data with `na_color`.
            key_attr: Element attribute used to match data keys (default ``"id"``).

        Returns:
            A new SVGDocument with the heatmap applied.

        Raises:
            ValueError: If required columns are missing from the DataFrame.
        """
        from pathy_svg.data import dataframe_to_dict

        data = dataframe_to_dict(df, id_col, value_col)
        return self.heatmap(
            data,
            palette=palette,
            vmin=vmin,
            vmax=vmax,
            vcenter=vcenter,
            na_color=na_color,
            breaks=breaks,
            opacity=opacity,
            preserve_stroke=preserve_stroke,
            color_missing=color_missing,
            key_attr=key_attr,
        )

    def recolor(
        self,
        colors: dict[str, str],
        *,
        opacity: float | None = None,
        preserve_stroke: bool = True,
        key_attr: str = "id",
    ):
        """Apply manual color mapping to paths.

        Args:
            colors: A dictionary mapping element attribute values to hex color strings.
            opacity: Opacity for the filled paths.
            preserve_stroke: Whether to preserve original stroke styling.
            key_attr: Element attribute used to match data keys (default ``"id"``).

        Returns:
            A new SVGDocument with the updated colors applied.
        """
        from pathy_svg.coloring import apply_recolor

        clone = self._clone()
        resolved_colors, resolved_index = clone._resolve_key_attr(colors, key_attr)
        apply_recolor(
            clone._tree,
            resolved_colors,
            opacity=opacity,
            preserve_stroke=preserve_stroke,
            id_to_elem=resolved_index,
        )
        return clone

    def recolor_by_category(
        self,
        data: dict[str, str],
        *,
        palette: dict[str, str] | str = "tab10",
        na_color: str = "#cccccc",
        opacity: float | None = None,
        preserve_stroke: bool = True,
        key_attr: str = "id",
    ):
        """Apply categorical coloring to paths.

        Args:
            data: A dictionary mapping element attribute values to category labels.
            palette: A dictionary mapping categories to colors, or the name of a matplotlib colormap.
            na_color: Color to use for missing categories.
            opacity: Opacity for the filled paths.
            preserve_stroke: Whether to preserve original stroke styling.
            key_attr: Element attribute used to match data keys (default ``"id"``).

        Returns:
            A new SVGDocument with the categorical coloring applied.
        """
        from pathy_svg.coloring import apply_categorical

        clone = self._clone()
        resolved_data, resolved_index = clone._resolve_key_attr(data, key_attr)
        cat_palette = apply_categorical(
            clone._tree,
            resolved_data,
            palette=palette,
            na_color=na_color,
            opacity=opacity,
            preserve_stroke=preserve_stroke,
            id_to_elem=resolved_index,
        )
        clone._last_categorical_palette = cat_palette
        return clone
