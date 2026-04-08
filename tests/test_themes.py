"""Tests for pathy_svg.themes module."""

import re

import pytest

from pathy_svg.themes import (
    CategoricalPalette,
    ColorScale,
    ThemePreset,
    heatmap_classic,
    medical,
    geographic,
)


class TestColorScale:
    def test_returns_hex(self):
        scale = ColorScale("viridis", vmin=0, vmax=1)
        color = scale(0.5)
        assert re.match(r"^#[0-9a-fA-F]{6}$", color)

    def test_min_max_different(self):
        scale = ColorScale("viridis", vmin=0, vmax=1)
        c0 = scale(0.0)
        c1 = scale(1.0)
        assert c0 != c1

    def test_fit_autosets_range(self):
        scale = ColorScale("viridis")
        scale.fit([10, 20, 30])
        # Should not raise
        color = scale(20)
        assert re.match(r"^#[0-9a-fA-F]{6}$", color)

    def test_custom_color_list(self):
        scale = ColorScale(["#ff0000", "#00ff00", "#0000ff"], vmin=0, vmax=1)
        color = scale(0.5)
        assert re.match(r"^#[0-9a-fA-F]{6}$", color)

    def test_nan_returns_gray(self):
        scale = ColorScale("viridis", vmin=0, vmax=1)
        assert scale(float("nan")) == "#cccccc"

    def test_map_values(self):
        scale = ColorScale("viridis", vmin=0, vmax=1)
        result = scale.map_values({"a": 0.0, "b": 1.0})
        assert "a" in result
        assert "b" in result
        assert result["a"] != result["b"]

    def test_diverging(self):
        scale = ColorScale("coolwarm", vmin=-1, vmax=1, vcenter=0)
        cn = scale(-1)
        c0 = scale(0)
        cp = scale(1)
        # All should be valid hex
        for c in [cn, c0, cp]:
            assert re.match(r"^#[0-9a-fA-F]{6}$", c)


class TestCategoricalPalette:
    def test_explicit_mapping(self):
        pal = CategoricalPalette({"cat": "#ff0000", "dog": "#00ff00"})
        assert pal("cat") == "#ff0000"
        assert pal("dog") == "#00ff00"

    def test_auto_assign(self):
        pal = CategoricalPalette("tab10")
        c1 = pal("alpha")
        c2 = pal("beta")
        assert c1 != c2
        # Same category returns same color
        assert pal("alpha") == c1

    def test_unknown_explicit_raises(self):
        pal = CategoricalPalette({"cat": "#ff0000"})
        with pytest.raises(KeyError):
            pal("unknown")

    def test_mapping_property(self):
        pal = CategoricalPalette("tab10")
        pal("x")
        pal("y")
        assert "x" in pal.mapping
        assert "y" in pal.mapping


class TestThemePreset:
    def test_to_dict(self):
        t = ThemePreset(palette="viridis", na_color="#eee")
        d = t.to_dict()
        assert d["palette"] == "viridis"
        assert d["na_color"] == "#eee"

    def test_builtin_presets(self):
        assert medical.sequential.palette == "YlOrRd"
        assert geographic.choropleth.palette == "YlGnBu"
        assert heatmap_classic.viridis.palette == "viridis"
