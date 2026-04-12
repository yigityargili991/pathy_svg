"""pathy_svg — Color arbitrary SVG paths by data values.

# Quick Start

## Heatmap

```python
from pathy_svg import SVGDocument

doc = SVGDocument.from_file("map.svg")
data = {"stomach": 0.5, "liver": 0.8, "heart": 0.3}

doc.heatmap(data, palette="YlOrRd").legend(title="Expression").save("output.svg")
```

## Gradient and Pattern Fills

```python
from pathy_svg import SVGDocument, GradientSpec

doc = SVGDocument.from_file("map.svg")

# Linear gradient
doc.gradient_fill({
    "stomach": GradientSpec(start="#ff0000", end="#0000ff"),
}).save("gradient.svg")

# Pattern fill
doc.pattern_fill({"liver": "crosshatch", "heart": "dots"}).save("patterned.svg")
```

## Stroke Mapping

```python
doc.stroke_map(data, width_range=(1, 5), palette="Reds").save("strokes.svg")
```

## Highlight / Dim

```python
doc.highlight(["stomach", "liver"]).save("highlighted.svg")
```

## Group Aggregation

```python
doc.heatmap_groups(data, agg="mean", palette="YlOrRd").save("groups.svg")
```

## Layers

```python
result = (
    doc.layers()
    .add("heat", lambda d: d.heatmap(data, palette="YlOrRd"))
    .add("labels", lambda d: d.annotate({"stomach": "S", "liver": "L"}))
    .flatten()
)
result.save("layered.svg")
```

---

# Example Workflow: US States

A walkthrough using real 2023 US Census data on a public-domain
US states map. Each step shows the code and the resulting SVG.

## 1. Population Heatmap

Color every state by its population using the YlOrRd colormap.

```python
from pathy_svg import SVGDocument

doc = SVGDocument.from_file("us_states.svg")

population = {"CA": 38_965_193, "TX": 30_503_301, "FL": 22_610_726, ...}

colored = (
    doc.heatmap(population, palette="YlOrRd")
    .legend(title="Population", position=(0.82, 0.05), size=(0.03, 0.35))
)
colored.save("population.svg")
```

![Population heatmap](examples/01_population.svg)

## 2. Population Density

Derived metric: people per square mile, using the viridis colormap.

```python
land_area = {"AK": 570641, "TX": 261232, "CA": 155779, ...}
density = {st: population[st] / land_area[st] for st in population}

density_map = (
    doc.heatmap(density, palette="viridis")
    .legend(title="People / sq mi", position=(0.82, 0.05), size=(0.03, 0.35))
)
density_map.save("density.svg")
```

![Density heatmap](examples/02_density.svg)

## 3. Highlight Top 10 States

Focus on the 10 most populous states; everything else is dimmed and desaturated.

```python
top10 = sorted(population, key=population.get, reverse=True)[:10]

highlighted = (
    doc.heatmap(population, palette="YlOrRd")
    .highlight(top10, dim_opacity=0.15, desaturate=True)
)
highlighted.save("top10.svg")
```

![Top 10 highlighted](examples/03_top10_highlighted.svg)

## 4. Pattern Fills for Accessibility

High-density states get dots, low-density get diagonal lines.
Works in grayscale and for colorblind readers.

```python
from pathy_svg import PatternSpec

median_density = sorted(density.values())[len(density) // 2]

patterns = {}
for st, d in density.items():
    if d > median_density * 2:
        patterns[st] = PatternSpec(kind="dots", color="#b30000", spacing=5, thickness=1.5)
    elif d < median_density / 2:
        patterns[st] = PatternSpec(kind="diagonal_lines", color="#084594", spacing=8)

doc.pattern_fill(patterns).save("patterns.svg")
```

![Pattern fills](examples/04_density_patterns.svg)

## 5. Gradient Fills

Apply custom linear gradients to individual states.

```python
from pathy_svg import GradientSpec

gradients = {
    "CA": GradientSpec(start="#fee08b", end="#d73027", direction="vertical"),
    "TX": GradientSpec(start="#d9ef8b", end="#1a9850", direction="horizontal"),
    "NY": GradientSpec(start="#e0f3f8", end="#4575b4", direction="diagonal"),
    "FL": GradientSpec(start="#fee08b", end="#f46d43", mid="#fdae61"),
}

doc.gradient_fill(gradients).save("gradients.svg")
```

![Gradient fills](examples/05_gradient_fills.svg)

## 6. Stroke Mapping

Density as fill color, population as stroke width. Two variables, one map.

```python
stroked = (
    doc.heatmap(density, palette="YlGnBu", vmax=1500)
    .stroke_map(population, width_range=(0.5, 5.0), palette="Greys")
)
stroked.save("stroked.svg")
```

![Stroke mapping](examples/06_stroke_by_population.svg)

## 7. Layer Composition

Build a complex visualization from independent, named layers.

```python
layered = (
    doc.layers()
    .add("density", lambda d: d.heatmap(density, palette="YlGnBu", vmax=1500))
    .add("borders", lambda d: d.stroke_map(population, width_range=(0.5, 3.0)))
    .add("labels",  lambda d: d.annotate(
        {st: st for st in top10}, font_size=7, font_color="#222",
    ))
    .flatten()
    .legend(title="Density", position=(0.82, 0.05), size=(0.03, 0.35))
)
layered.save("layered.svg")
```

![Layered composition](examples/07_layered.svg)

Full source: [`examples/us_states_workflow.py`](https://github.com/yigityargili991/pathy_svg/blob/main/examples/us_states_workflow.py)
"""

__version__ = "0.1.0"

from pathy_svg.document import SVGDocument
from pathy_svg.exceptions import (
    ColorScaleError,
    DataMappingError,
    ExportError,
    PathNotFoundError,
    PathySVGError,
    SVGParseError,
    ValidationError,
)
from pathy_svg.inspect import PathInfo, ValidationResult
from pathy_svg.themes import ColorScale, CategoricalPalette, ThemePreset
from pathy_svg.themes import medical, geographic, heatmap_classic
from pathy_svg.transform import BBox, ViewBox
from pathy_svg.color import hex_to_rgb, rgb_to_hex, interpolate_color, parse_svg_color
from pathy_svg.data import normalize_values, bin_values, dataframe_to_dict
from pathy_svg.svg_tools import (
    viewbox_to_pixel,
    merge_svgs,
    strip_metadata,
    optimize_svg,
    extract_styles,
)
from pathy_svg.gradient import GradientSpec
from pathy_svg.pattern import PatternSpec, CustomPatternSpec
from pathy_svg.layers import LayerManager

__all__ = [
    "__version__",
    "SVGDocument",
    # Exceptions
    "ColorScaleError",
    "DataMappingError",
    "ExportError",
    "PathNotFoundError",
    "PathySVGError",
    "SVGParseError",
    "ValidationError",
    # Data classes
    "PathInfo",
    "ValidationResult",
    "BBox",
    "ViewBox",
    # Themes
    "ColorScale",
    "CategoricalPalette",
    "ThemePreset",
    "medical",
    "geographic",
    "heatmap_classic",
    # Utils
    "hex_to_rgb",
    "rgb_to_hex",
    "interpolate_color",
    "parse_svg_color",
    "normalize_values",
    "bin_values",
    "viewbox_to_pixel",
    "merge_svgs",
    "strip_metadata",
    "optimize_svg",
    "extract_styles",
    "dataframe_to_dict",
    "GradientSpec",
    "PatternSpec",
    "CustomPatternSpec",
    "LayerManager",
]
