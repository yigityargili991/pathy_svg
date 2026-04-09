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
        clip: bool = True,
    ):
        """Apply data-driven coloring to paths.

        Args:
            data: Data dict mapping path IDs to numeric values.
            palette: Name of a matplotlib colormap or a list of hex colors.
            vmin: Minimum value for the color scale.
            vmax: Maximum value for the color scale.
            vcenter: Center value for diverging color scales.
            na_color: Color to use for missing or NaN values.
            breaks: List of boundary values for discrete color scales.
            opacity: Opacity for the filled paths.
            preserve_stroke: Whether to preserve original stroke styling.
            color_missing: Whether to color paths that are not in the data with `na_color`.
            clip: Whether to clip values outside the `vmin` and `vmax` bounds.

        Returns:
            A new SVGDocument with the heatmap applied.
        """
        from pathy_svg.coloring import apply_heatmap

        clone = self._clone()
        scale = apply_heatmap(
            clone._tree,
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
            clip=clip,
        )
        clone._last_scale = scale
        clone._last_heatmap_config = {
            "palette": palette,
            "vmin": vmin,
            "vmax": vmax,
            "vcenter": vcenter,
            "breaks": breaks,
        }
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
        clip: bool = True,
    ):
        """Apply data-driven coloring from a Pandas DataFrame.

        Args:
            df: A Pandas DataFrame containing the data.
            id_col: Column name for element IDs.
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
            clip: Whether to clip values outside the `vmin` and `vmax` bounds.

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
            clip=clip,
        )

    def recolor(
        self,
        colors: dict[str, str],
        *,
        opacity: float | None = None,
        preserve_stroke: bool = True,
    ):
        """Apply manual color mapping to paths.

        Args:
            colors: A dictionary mapping path IDs to hex color strings.
            opacity: Opacity for the filled paths.
            preserve_stroke: Whether to preserve original stroke styling.

        Returns:
            A new SVGDocument with the updated colors applied.
        """
        from pathy_svg.coloring import apply_recolor

        clone = self._clone()
        apply_recolor(
            clone._tree, colors, opacity=opacity, preserve_stroke=preserve_stroke
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
    ):
        """Apply categorical coloring to paths.

        Args:
            data: A dictionary mapping path IDs to category labels.
            palette: A dictionary mapping categories to colors, or the name of a matplotlib colormap.
            na_color: Color to use for missing categories.
            opacity: Opacity for the filled paths.
            preserve_stroke: Whether to preserve original stroke styling.

        Returns:
            A new SVGDocument with the categorical coloring applied.
        """
        from pathy_svg.coloring import apply_categorical

        clone = self._clone()
        cat_palette = apply_categorical(
            clone._tree,
            data,
            palette=palette,
            na_color=na_color,
            opacity=opacity,
            preserve_stroke=preserve_stroke,
        )
        clone._last_categorical_palette = cat_palette
        return clone
