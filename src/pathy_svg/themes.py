"""Predefined color palettes and style presets for heatmaps."""

from __future__ import annotations

from dataclasses import dataclass, fields

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np


class ColorScale:
    """Maps numeric values to hex colors using matplotlib colormaps and normalization.

    Supports continuous, diverging (with vcenter), and discrete (with breaks) modes.
    """

    def __init__(
        self,
        palette: str | list[str] = "viridis",
        *,
        vmin: float | None = None,
        vmax: float | None = None,
        vcenter: float | None = None,
        breaks: list[float] | None = None,
    ):
        self.palette_name = palette if isinstance(palette, str) else "custom"
        self.vmin = vmin
        self.vmax = vmax
        self.vcenter = vcenter
        self.breaks = breaks

        # Build colormap
        if isinstance(palette, list):
            self._cmap = mcolors.LinearSegmentedColormap.from_list(
                "custom", palette, N=256
            )
        else:
            self._cmap = plt.get_cmap(palette)

        # Build normalizer
        if breaks is not None:
            # Discrete mode: BoundaryNorm
            self._norm = mcolors.BoundaryNorm(breaks, self._cmap.N)
        elif vcenter is not None:
            self._norm = mcolors.TwoSlopeNorm(
                vcenter=vcenter, vmin=vmin, vmax=vmax
            )
        else:
            self._norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

    def fit(self, values: list[float] | np.ndarray) -> ColorScale:
        """Auto-set vmin/vmax from data if not explicitly provided.

        Returns self for chaining.
        """
        arr = np.array(values, dtype=float)
        arr = arr[np.isfinite(arr)]
        if len(arr) == 0:
            return self

        if self.breaks is None:
            if self.vmin is None:
                self._norm.vmin = float(arr.min())
            if self.vmax is None:
                self._norm.vmax = float(arr.max())
        return self

    def __call__(self, value: float) -> str:
        """Map a single numeric value to a hex color string."""
        if not np.isfinite(value):
            return "#cccccc"
        rgba = self._cmap(self._norm(value))
        return mcolors.to_hex(rgba)

    def map_values(self, values: dict[str, float]) -> dict[str, str]:
        """Map a dict of {id: value} to {id: hex_color}."""
        return {k: self(v) for k, v in values.items()}


class CategoricalPalette:
    """Maps category labels to distinct colors."""

    def __init__(
        self,
        palette: dict[str, str] | str = "tab10",
    ):
        if isinstance(palette, dict):
            self._mapping = dict(palette)
            self._cmap = None
        else:
            self._mapping = {}
            self._cmap = plt.get_cmap(palette)
            self._next_idx = 0

    def __call__(self, category: str) -> str:
        """Get the hex color for a category. Auto-assigns colors if using a colormap."""
        if category in self._mapping:
            return self._mapping[category]
        if self._cmap is not None:
            rgba = self._cmap(self._next_idx % self._cmap.N)
            self._next_idx += 1
            color = mcolors.to_hex(rgba)
            self._mapping[category] = color
            return color
        raise KeyError(f"Unknown category: {category!r}")

    @property
    def mapping(self) -> dict[str, str]:
        """Current category-to-color mapping."""
        return dict(self._mapping)


# ---------------------------------------------------------------------------
# Theme presets
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ThemePreset:
    """A bundle of heatmap kwargs that can be unpacked with **."""

    palette: str | list[str]
    na_color: str = "#e0e0e0"
    preserve_stroke: bool = True

    def to_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}


class _MedicalThemes:
    sequential = ThemePreset(palette="YlOrRd")
    diverging = ThemePreset(palette="RdBu_r")
    categorical = ThemePreset(palette="Set2")


class _GeographicThemes:
    choropleth = ThemePreset(palette="YlGnBu")
    density = ThemePreset(palette="hot_r")
    categorical = ThemePreset(palette="tab20")


class _HeatmapClassicThemes:
    red_blue = ThemePreset(palette="RdYlBu_r")
    viridis = ThemePreset(palette="viridis")
    hot_cold = ThemePreset(palette="coolwarm")


medical = _MedicalThemes()
geographic = _GeographicThemes()
heatmap_classic = _HeatmapClassicThemes()
