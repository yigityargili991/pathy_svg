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

doc = SVGDocument.from_file("map.svg")

data = {"region_a": 10.5, "region_b": 42.0, "region_c": 7.3}

doc.heatmap(data, palette="YlOrRd").legend(title="Values").save("output.svg")
```

## Features

- **Heatmaps** — data-driven coloring with any matplotlib colormap
- **Categorical coloring** — map categories to distinct colors
- **Manual recolor** — direct ID-to-color mapping
- **Diff visualization** — compare datasets with delta, ratio, log2ratio, or percent change modes
- **Side-by-side comparison** — multiple datasets in a single SVG
- **Legends** — gradient, discrete, and categorical legend types
- **Annotations** — text labels at element centroids or custom positions
- **Tooltips** — hover text via SVG `<title>` elements
- **Animations** — CSS keyframe effects (pulse, fade_in, blink, sequential)
- **Export** — PNG, PDF, JPEG via cairosvg and Pillow
- **Jupyter** — inline SVG display with `_repr_svg_` and `_repr_mimebundle_`
- **CLI** — heatmap, inspect, validate, guide, diff, and export commands
- **Immutable API** — method chaining with new instances returned on each call
- **DataFrame support** — load data directly from pandas
- **Theme presets** — medical, geographic, heatmap_classic

## CLI Usage

```bash
# Create a heatmap
pathy-svg heatmap map.svg data.csv --id-col region --value-col score --palette YlOrRd --legend -o out.svg

# Inspect SVG structure
pathy-svg inspect map.svg

# Validate data IDs against SVG
pathy-svg validate map.svg data.csv --id-col region

# Compare two datasets
pathy-svg diff map.svg baseline.csv treatment.csv --id-col region --value-col score --mode delta -o diff.svg

# Export to PNG
pathy-svg export map.svg -o map.png --width 1200
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
