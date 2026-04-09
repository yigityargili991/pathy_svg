"""Predefined color palettes and style presets for heatmaps."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np


class ColorScale:
    """Maps numeric values to hex colors using matplotlib colormaps and normalization.

    Supports continuous, diverging (with vcenter), and discrete (with breaks) modes.

    Args:
        palette: Name of a matplotlib colormap or a list of hex colors.
        vmin: Minimum value for the color scale.
        vmax: Maximum value for the color scale.
        vcenter: Center value for diverging color scales.
        breaks: List of boundary values for discrete color scales.
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
            self._norm = mcolors.TwoSlopeNorm(vcenter=vcenter, vmin=vmin, vmax=vmax)
        else:
            self._norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

    @property
    def effective_vmin(self) -> float:
        """The resolved minimum value after fitting."""
        v = getattr(self._norm, "vmin", None)
        return float(v) if v is not None else 0.0

    @property
    def effective_vmax(self) -> float:
        """The resolved maximum value after fitting."""
        v = getattr(self._norm, "vmax", None)
        return float(v) if v is not None else 1.0

    def fit(self, values: list[float] | np.ndarray) -> ColorScale:
        """Auto-set vmin/vmax from data if not explicitly provided.

        Args:
            values: A list or numpy array of numeric values to fit the scale to.

        Returns:
            The current ColorScale instance for method chaining.
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
        """Map a single numeric value to a hex color string.

        Args:
            value: The numeric value to map.

        Returns:
            The corresponding hex color string from the scale, or "#cccccc" if the value is NaN or infinite.
        """
        if not np.isfinite(value):
            return "#cccccc"
        rgba = self._cmap(self._norm(value))
        return mcolors.to_hex(rgba)

    def map_values(self, values: dict[str, float]) -> dict[str, str]:
        """Map a dict of {id: value} to {id: hex_color}.

        Args:
            values: A dictionary mapping identifiers to numeric values.

        Returns:
            A dictionary mapping the same identifiers to their corresponding hex color strings.
        """
        return {k: self(v) for k, v in values.items()}


class CategoricalPalette:
    """Maps category labels to distinct colors.

    Args:
        palette: A dictionary mapping categories to hex colors, or the name of a matplotlib colormap.
    """

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
        """Get the hex color for a category. Auto-assigns colors if using a colormap.

        Args:
            category: The category label to map to a color.

        Returns:
            The hex color string associated with the category.

        Raises:
            KeyError: If the category is unknown and a predefined dictionary mapping was provided instead of a colormap.
        """
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


@dataclass(frozen=True)
class ThemePreset:
    """A bundle of heatmap kwargs that can be unpacked with **."""

    palette: str | list[str]
    na_color: str = "#e0e0e0"
    preserve_stroke: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class MedicalThemes:
    sequential: ThemePreset = ThemePreset(palette="YlOrRd")
    diverging: ThemePreset = ThemePreset(palette="RdBu_r")
    categorical: ThemePreset = ThemePreset(palette="Set2")


@dataclass(frozen=True)
class GeographicThemes:
    choropleth: ThemePreset = ThemePreset(palette="YlGnBu")
    density: ThemePreset = ThemePreset(palette="hot_r")
    categorical: ThemePreset = ThemePreset(palette="tab20")


@dataclass(frozen=True)
class HeatmapClassicThemes:
    red_blue: ThemePreset = ThemePreset(palette="RdYlBu_r")
    viridis: ThemePreset = ThemePreset(palette="viridis")
    hot_cold: ThemePreset = ThemePreset(palette="coolwarm")


medical = MedicalThemes()
geographic = GeographicThemes()
heatmap_classic = HeatmapClassicThemes()
