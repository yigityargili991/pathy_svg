"""Mixin for dataset comparison methods."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any, Literal, Self

from pathy_svg._constants import Layout
from pathy_svg._mixins.host import _DocumentMixinHost
from pathy_svg.diff import DiffMode


class DiffMixin(_DocumentMixinHost):
    """Diff and side-by-side comparison methods."""

    __slots__ = ()

    def diff(
        self,
        baseline: Mapping[str, float],
        treatment: Mapping[str, float],
        *,
        mode: DiffMode = "delta",
        palette: str | Sequence[str] = "coolwarm",
        vcenter: float | Literal["auto"] | None = "auto",
        vmin: float | None = None,
        vmax: float | None = None,
        **heatmap_kwargs: Any,
    ) -> Self:
        """Compute per-path differences and apply as a heatmap.

        Args:
            baseline: Data dict for the baseline state.
            treatment: Data dict for the treatment state.
            mode: The difference mode ("delta", "ratio", "log2ratio", or "percent_change").
            palette: Name of a matplotlib diverging colormap or a list of hex colors.
            vcenter: Center value for the diverging color scale. ``"auto"``
                (the default) centers ``"ratio"`` at 1 and the other modes at 0;
                ``None`` disables centering.
            vmin: Minimum value for the color scale.
            vmax: Maximum value for the color scale.
            **heatmap_kwargs: Additional arguments passed to `heatmap`.

        Returns:
            A new SVGDocument with the diff heatmap applied.
        """
        from pathy_svg.diff import compute_diff

        if vcenter == "auto":
            vcenter = 1.0 if mode == "ratio" else 0.0
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
        datasets: Mapping[str, Mapping[str, float]],
        *,
        palette: str | Sequence[str] = "YlOrRd",
        layout: Layout = "horizontal",
        spacing: float = 20,
        **heatmap_kwargs: Any,
    ) -> Self:
        """Create side-by-side comparison of multiple datasets.

        Unless ``vmin``/``vmax`` are given, all panels share one color range
        spanning every dataset, so equal values get equal colors and
        ``legend()`` describes every panel.

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

        values = [
            value
            for data in datasets.values()
            for value in data.values()
            if math.isfinite(value)
        ]
        if values:
            low, high = min(values), max(values)
            vcenter = heatmap_kwargs.get("vcenter")
            if vcenter is not None:
                # Mirror one-sided data about vcenter, as a diverging fit does.
                if low >= vcenter:
                    low = 2 * vcenter - high
                if high <= vcenter:
                    high = 2 * vcenter - low
            heatmap_kwargs.setdefault("vmin", low)
            heatmap_kwargs.setdefault("vmax", high)

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
        result = self._with_owned_tree(new_tree)
        result._last_scale = next(
            (doc._last_scale for doc in colored_docs if doc._last_scale is not None),
            None,
        )
        result._last_categorical_palette = None
        return result
