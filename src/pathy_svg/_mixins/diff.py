"""Mixin for dataset comparison methods."""

from __future__ import annotations


class DiffMixin:
    """Diff and side-by-side comparison methods."""

    __slots__ = ()

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
