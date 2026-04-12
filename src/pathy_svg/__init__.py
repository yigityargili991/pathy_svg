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

# Example Workflow

A step-by-step walkthrough showing how to explore, visualize, and compose
multiple data layers on a single SVG.

## 1. Load and Inspect

Start by loading an SVG and discovering what elements are available.

```python
from pathy_svg import SVGDocument

doc = SVGDocument.from_file("anatomy.svg")

# What elements can we color?
print(doc.element_ids)
# ['stomach', 'liver', 'heart', 'lung_l', 'lung_r', ...]

# Groups?
print(doc.group_ids)
# ['organs', 'outline']

# Detailed info
for info in doc.inspect_paths():
    print(f"{info.id:15s}  tag={info.tag:8s}  fill={info.fill}")
```

## 2. Validate Your Data

Check that your data IDs actually match elements in the SVG before coloring.

```python
data = {
    "stomach": 85.2,
    "liver": 42.1,
    "heart": 91.7,
    "lung_l": 63.4,
    "lung_r": 58.9,
    "typo_organ": 10.0,  # oops
}

result = doc.validate_ids(data.keys())
print(f"Matched: {result.matched}")
# ['stomach', 'liver', 'heart', 'lung_l', 'lung_r']
print(f"Unmatched: {result.unmatched}")
# ['typo_organ']
```

## 3. Apply a Heatmap

Color elements by their numeric values using a colormap.

```python
colored = doc.heatmap(
    data,
    palette="YlOrRd",   # any matplotlib colormap
    vmin=0,
    vmax=100,
)

# Add a legend
colored = colored.legend(
    title="Expression Level",
    position=(0.85, 0.1),
    direction="vertical",
)

colored.save("heatmap.svg")
```

## 4. Add Accessibility with Patterns

Overlay patterns so the visualization works without color.

```python
# Bin values into categories and assign patterns
high = [eid for eid, v in data.items() if v > 80]
mid  = [eid for eid, v in data.items() if 40 <= v <= 80]

from pathy_svg import PatternSpec

patterns = {}
for eid in high:
    patterns[eid] = PatternSpec(kind="dots", color="#333", spacing=4)
for eid in mid:
    patterns[eid] = PatternSpec(kind="diagonal_lines", color="#666", spacing=6)

patterned = colored.pattern_fill(patterns)
patterned.save("accessible.svg")
```

## 5. Highlight a Region of Interest

Dim everything except the elements you want to focus on.

```python
focused = colored.highlight(
    ["heart", "lung_l", "lung_r"],
    dim_opacity=0.15,
    desaturate=True,
)
focused.save("cardiopulmonary.svg")
```

## 6. Stroke-Based Visualization

Map a second variable to stroke width without touching fill colors.

```python
border_data = {"stomach": 2.0, "liver": 5.0, "heart": 8.0}

stroked = colored.stroke_map(
    border_data,
    width_range=(0.5, 4.0),
    palette="Greys",
)
stroked.save("with_borders.svg")
```

## 7. Compare Datasets

Visualize the difference between baseline and treatment measurements.

```python
baseline  = {"stomach": 40, "liver": 60, "heart": 50}
treatment = {"stomach": 80, "liver": 55, "heart": 90}

diff = doc.diff(
    baseline, treatment,
    mode="percent_change",
    palette="coolwarm",
)
diff.legend(title="% Change").save("diff.svg")
```

## 8. Compose with Layers

Build a complex visualization from independent layers that can be
toggled on and off.

```python
from pathy_svg import GradientSpec

result = (
    doc.layers()
    .add("heatmap", lambda d: d.heatmap(data, palette="YlOrRd"))
    .add("borders", lambda d: d.stroke_map(border_data, width_range=(1, 3)))
    .add("labels",  lambda d: d.annotate({
        "stomach": "85.2",
        "liver": "42.1",
        "heart": "91.7",
    }))
    .add("tooltips", lambda d: d.add_tooltips({
        "stomach": "Stomach: 85.2 (high)",
        "liver": "Liver: 42.1 (low)",
        "heart": "Heart: 91.7 (high)",
    }))
    .flatten()
)

result.save("complete.svg")
```

Toggle layers before rendering:

```python
# Same layers, but hide the labels
minimal = (
    doc.layers()
    .add("heatmap", lambda d: d.heatmap(data, palette="YlOrRd"))
    .add("borders", lambda d: d.stroke_map(border_data, width_range=(1, 3)))
    .add("labels",  lambda d: d.annotate({"stomach": "85.2"}))
    .hide("labels")
    .flatten()
)
```

## 9. Export

Save to different formats.

```python
result.save("output.svg")           # SVG
result.to_png("output.png", dpi=150) # PNG (requires cairosvg + Pillow)
result.to_pdf("output.pdf")          # PDF

# In Jupyter, just display inline:
result.show()
# Or just put it as the last expression in a cell — _repr_svg_ handles it.
```
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
