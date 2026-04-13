# pathy-svg

[![PyPI](https://img.shields.io/pypi/v/pathy-svg)](https://pypi.org/project/pathy-svg/)
[![Python](https://img.shields.io/pypi/pyversions/pathy-svg)](https://pypi.org/project/pathy-svg/)
[![License](https://img.shields.io/github/license/yigityargili991/pathy_svg)](LICENSE)

Color arbitrary SVG paths by data values — turn any SVG into a heatmap.

## Installation

```bash
pip install pathy-svg
```

Optional extras:

```bash
pip install pathy-svg[export]  # PNG, PDF, JPEG export (cairosvg + Pillow)
pip install pathy-svg[full]    # All features including Jupyter display
```

## Quick Start

```python
from pathy_svg import SVGDocument

doc = SVGDocument.from_file("examples/map.svg")

data = {
    "stomach": 0.5,
    "liver": 0.8,
    "heart": 0.3,
    "lung_l": 0.6,
    "lung_r": 0.7,
}

doc.heatmap(data, palette="YlOrRd").legend(title="Expression").save("output.svg")
```

![Heatmap example](docs/examples/01_population.svg)

### Gradient and Pattern Fills

```python
from pathy_svg import SVGDocument, GradientSpec

doc = SVGDocument.from_file("examples/map.svg")

# Gradient fill
doc.gradient_fill({
    "stomach": GradientSpec(start="#ff0000", end="#0000ff", direction="horizontal"),
}).save("gradient.svg")

# Pattern fill (string shorthand or PatternSpec)
doc.pattern_fill({
    "liver": "crosshatch",
    "heart": "dots",
}).save("patterned.svg")
```

![Gradient fills](docs/examples/05_gradient_fills.svg)

![Pattern fills](docs/examples/04_density_patterns.svg)

### Stroke Mapping and Highlighting

```python
# Map data to stroke width and color
doc.stroke_map(data, width_range=(1, 5), palette="Reds").save("strokes.svg")

# Highlight specific elements, dim the rest
doc.highlight(["stomach", "liver"]).save("highlighted.svg")
```

![Stroke mapping](docs/examples/06_stroke_by_population.svg)

![Highlighting](docs/examples/03_top10_highlighted.svg)

### Matching by Data Attributes

```python
# Match elements by data-region instead of id
doc.heatmap({"north": 0.8, "south": 0.3}, key_attr="data-region").save("regions.svg")

# Works with all methods: recolor, stroke_map, highlight, annotate, etc.
doc.recolor({"north": "#ff0000"}, key_attr="data-region").save("recolored.svg")
```

### Group Aggregation and Layers

```python
# Color groups by the mean of their children's values
doc.heatmap_groups(data, agg="mean", palette="YlOrRd").save("groups.svg")

# Or use a custom aggregation function
doc.heatmap_groups(data, agg=lambda vals: max(vals) - min(vals)).save("range.svg")

# Compose multiple visualization layers
result = (
    doc.layers()
    .add("heat", lambda d: d.heatmap(data, palette="YlOrRd"))
    .add("borders", lambda d: d.stroke_map(data, palette="Greys"))
    .add("labels", lambda d: d.annotate({"stomach": "S", "liver": "L"}))
    .flatten()
)
result.save("layered.svg")
```

![Layered visualization](docs/examples/07_layered.svg)

The source distribution includes a runnable `examples/` directory with:

- `examples/map.svg`
- `examples/data.csv`
- `examples/baseline.csv`
- `examples/treatment.csv`

## Features

- **Heatmaps** — data-driven coloring with any matplotlib colormap
- **Categorical coloring** — map categories to distinct colors
- **Manual recolor** — direct ID-to-color mapping
- **Gradient fills** — apply linear gradients (horizontal, vertical, diagonal) to elements
- **Pattern fills** — hatching, crosshatch, dots, and custom SVG patterns for accessibility
- **Stroke mapping** — map data to stroke width and/or color independently of fill
- **Highlight/dim** — emphasize specific elements while dimming others with desaturation
- **Group aggregation** — color `<g>` elements by aggregating children (mean, sum, min, max, median, or custom callable)
- **Multi-layer system** — compose named visualization layers with show/hide/reorder
- **Diff visualization** — compare datasets with delta, ratio, log2ratio, or percent change modes
- **Side-by-side comparison** — multiple datasets in a single SVG
- **Legends** — gradient, discrete, and categorical legend types
- **Annotations** — text labels at element centroids or custom positions
- **Tooltips** — hover text via SVG `<title>` or CSS popups
- **Animations** — CSS keyframe effects (pulse, fade_in, blink, sequential)
- **Export** — PNG, PDF, JPEG via cairosvg and Pillow
- **Jupyter** — inline SVG display with `_repr_svg_` and `_repr_mimebundle_`
- **CLI** — heatmap, inspect, validate, guide, diff, and export commands
- **Flexible element matching** — match elements by `id`, `data-*` attributes, or `class` via `key_attr`
- **Immutable API** — method chaining with new instances returned on each call
- **DataFrame support** — load data directly from pandas
- **Theme presets** — medical, geographic, heatmap_classic

## CLI Usage

```bash
# Create a heatmap
pathy-svg heatmap examples/map.svg examples/data.csv --id-col organ --value-col expression --palette YlOrRd --legend -o out.svg

# Inspect SVG structure
pathy-svg inspect examples/map.svg

# Validate data IDs against SVG
pathy-svg validate examples/map.svg examples/data.csv --id-col organ

# Compare two datasets
pathy-svg diff examples/map.svg examples/baseline.csv examples/treatment.csv --id-col organ --value-col expression --mode delta -o diff.svg

# Export to PNG
pathy-svg export examples/map.svg -o map.png --width 1200
```

## API Overview

### Loading

| Method | Description |
|--------|-------------|
| `SVGDocument.from_file(path)` | Load from file path |
| `SVGDocument.from_string(svg)` | Load from SVG string |
| `SVGDocument.from_url(url)` | Load from URL |
| `SVGDocument.from_dataframe(df, ...)` | Load SVG path from a DataFrame column |

### Coloring

| Method | Description |
|--------|-------------|
| `.heatmap(data, palette=...)` | Apply data-driven coloring |
| `.heatmap_from_dataframe(df, ...)` | Heatmap from pandas DataFrame |
| `.recolor(color_map)` | Manual ID-to-color mapping |
| `.recolor_by_category(category_map)` | Categorical coloring |
| `.gradient_fill(gradients)` | Apply linear gradients to elements |
| `.pattern_fill(patterns)` | Apply hatching, dots, or custom patterns |
| `.stroke_map(data, width_range=..., palette=...)` | Map data to stroke width/color |
| `.highlight(ids)` | Emphasize elements, dim the rest |
| `.heatmap_groups(data, agg=...)` | Color groups by aggregating children |

### Layers

| Method | Description |
|--------|-------------|
| `.layers()` | Create a `LayerManager` for composing layers |
| `LayerManager.add(name, fn)` | Add a named layer |
| `LayerManager.hide(name)` / `.show(name)` | Toggle layer visibility |
| `LayerManager.reorder(names)` | Change layer order |
| `LayerManager.flatten()` | Render all visible layers to an `SVGDocument` |

### Visualization

| Method | Description |
|--------|-------------|
| `.legend(title=..., position=...)` | Add a legend |
| `.diff(baseline, treatment, mode=...)` | Diff two datasets |
| `.compare(datasets, layout=...)` | Side-by-side comparison |
| `.annotate(labels)` | Add text labels |
| `.add_tooltips(texts)` | Add hover tooltips |
| `.animate(effect=..., duration=..., loop=...)` | CSS animations |

### Inspection

| Method | Description |
|--------|-------------|
| `.path_ids` | List of all path element IDs |
| `.group_ids` | List of all group element IDs |
| `.element_ids` | List of all element IDs |
| `.viewbox` | SVG viewBox as `ViewBox` namedtuple |
| `.dimensions` | `(width, height)` tuple |
| `.inspect_paths()` | Detailed metadata for all colorable elements |
| `.validate_ids(ids)` | Check which IDs match SVG elements |

### Export

| Method | Description |
|--------|-------------|
| `.save(path)` | Write SVG to file |
| `.to_string()` | SVG as string |
| `.to_bytes()` | SVG as bytes |
| `.to_png(path)` | Export to PNG |
| `.to_pdf(path)` | Export to PDF |
| `.to_jpeg(path)` | Export to JPEG |
| `.show()` | Display in Jupyter |

## License

This project is licensed under the GNU General Public License v3.0 — see the [LICENSE](LICENSE) file for details.
