# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.3.0] - 2026-04-21

### Added
- `legend()` accepts explicit `scale` and `palette` kwargs, decoupling legend rendering from the `_last_scale` / `_last_categorical_palette` state set by `heatmap()` / `recolor_by_category()`. Lets users build a legend on a fresh document from a `ColorScale` they constructed manually.
- Top-level re-exports of `LegendKind`, `Direction`, `DiffMode`, `AnimationEffect`, `Placement`, `TooltipMethod`, `Layout` type aliases so users writing wrappers can type-hint against them without reaching into submodules.
- CLI parity: `heatmap` and `diff` commands now accept `--vmin`, `--vmax`, `--vcenter`, `--opacity`, `--key-attr`, matching `SVGDocument.heatmap()` / `SVGDocument.diff()`.

### Changed
- `xy_guide()` moved from `LegendMixin` to `AnnotationMixin`. The method is still available on `SVGDocument` — no user-facing change.

## [0.2.0] - 2026-04-21

### Removed
- **Breaking**: `SVGDocument.from_dataframe()` classmethod removed. Use `SVGDocument.from_file(path)` followed by `doc.heatmap_from_dataframe(df, ...)` or `dataframe_to_dict(df, id_col, value_col)` instead. This restores a consistent "one file → one document" constructor pattern.

## [0.1.3] - 2026-04-14

### Fixed
- **Security**: Extended XXE mitigation to custom pattern markup parsing — `CustomPatternSpec.markup` now uses the secure `XMLParser` in both validation and build paths

## [0.1.2] - 2026-04-13

### Fixed
- **Security**: Mitigated XML External Entity (XXE) vulnerability — `from_file` and `from_string` now use a secure `XMLParser` with `resolve_entities=False` and `no_network=True`
- Renamed ambiguous variable `l` to `layer` in `layers.py` (PEP 8 E741)

### Changed
- Expanded `bbox_from_path_d` docstring to explicitly document the Bézier control-point bounding box overestimation

## [0.1.1] - 2026-04-12

### Added
- `key_attr` parameter on all data-mapping methods — match elements by any attribute (`data-*`, `class`, etc.), not just `id`
- Callable aggregation in `heatmap_groups()` — pass a function like `agg=lambda vals: max(vals) - min(vals)`
- `expand_viewbox` parameter on `legend()` — opt out of automatic viewBox extension

### Fixed
- Group descendant protection now uses element identity, preventing `na_color` from overwriting children of colored `<g>` elements when using non-ID keys
- `heatmap_groups()` uses `id` for group lookup and `key_attr` for child matching — groups no longer need the custom attribute
- CSS tooltip selector changed from `[id]:hover` to `[data-tooltip]:hover` — works on elements without `id`
- Gradient/pattern def IDs sanitized via `safe_svg_id()` — handles spaces and punctuation in attribute values
- XPath injection in tooltip cleanup replaced with safe iteration
- `color_missing` pass runs correctly when no data keys match any elements

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

[0.2.0]: https://github.com/yigityargili991/pathy_svg/releases/tag/v0.2.0
[0.1.3]: https://github.com/yigityargili991/pathy_svg/releases/tag/v0.1.3
[0.1.2]: https://github.com/yigityargili991/pathy_svg/releases/tag/v0.1.2
[0.1.1]: https://github.com/yigityargili991/pathy_svg/releases/tag/v0.1.1
[0.1.0]: https://github.com/yigityargili991/pathy_svg/releases/tag/v0.1.0
