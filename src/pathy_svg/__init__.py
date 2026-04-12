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
