# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-04-09

### Added
- SVGDocument class with immutable, chainable API
- Data-driven heatmaps with matplotlib colormap support
- Categorical coloring and manual recolor
- Gradient fills on individual elements via `gradient_fill()` with `GradientSpec`
- Pattern fills (hatching, crosshatch, dots, custom SVG) via `pattern_fill()` with `PatternSpec`
- Stroke-based visualization via `stroke_map()` — map data to stroke width and/or color
- Highlight/dim via `highlight()` — emphasize elements while desaturating others
- Group aggregation via `heatmap_groups()` — color groups by mean/sum/min/max/median of children
- Multi-layer composition system via `layers()` returning `LayerManager`
- Diff visualization with delta, ratio, log2ratio, and percent change modes
- Side-by-side dataset comparison
- Gradient, discrete, and categorical legends with auto viewBox extension
- Text annotations, tooltips, and text replacement
- CSS animations (pulse, fade_in, blink, sequential)
- Export to PNG, PDF, JPEG via cairosvg and Pillow
- Jupyter notebook display (`_repr_svg_`, `_repr_html_`, `_repr_mimebundle_`)
- CLI with heatmap, inspect, validate, guide, diff, and export commands
- DataFrame integration via pandas
- Built-in theme presets (medical, geographic, heatmap_classic)
- Utility functions for color manipulation and SVG processing
- Coordinate grid overlay (xy_guide)
- US states example workflow with 2023 Census data

[0.1.0]: https://github.com/yigityargili991/pathy_svg/releases/tag/v0.1.0
