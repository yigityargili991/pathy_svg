# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.4.0] - 2026-08-13

### Added
- `compose_svgs()` and immutable `CompositionResult` / `PanelComposition` metadata, including per-panel source-to-output ID mappings
- Explicit immutable tree APIs: `SVGDocument.root_copy()`, snapshotting `SVGDocument.xpath()`, and `SVGDocument.from_tree(..., copy=...)`
- Public `CompositionError` and consistent `ValidationError` / `DataMappingError` boundaries that remain compatible with `ValueError`
- `dataframe` and `tabular` installation extras; `full` now includes all tabular, export, and notebook integrations
- Path-sensitive export overloads, `Self`-typed fluent transformations, generic `LayerManager`, and mapping/sequence-friendly inputs
- `color_missing` parameter on `recolor_by_category()`, mirroring `heatmap()`, to opt out of painting unmatched elements with `na_color`

### Changed
- Package maturity classifier is Beta while the pre-1.0 API is intentionally evolving
- `merge_svgs()` delegates to the structured composition API while retaining its document-only return contract
- The runtime now depends on `typing-extensions` to provide consistent `Self` typing on Python 3.10+
- **Breaking**: `recolor_by_category()` now paints data-addressable elements missing from `data` with `na_color` by default; pass `color_missing=False` to restore the previous touch-only-matched behavior. Missing-value sweeps in both `heatmap()` and `recolor_by_category()` only ever repaint indexed elements, never ID-less geometry or library-generated legends and annotations
- **Breaking**: composition (`merge_svgs()` / `compose_svgs()`) raises `CompositionError` for `<style>` at-rules that cannot be safely scoped per panel — `@import`, `@property`, `@counter-style`, and unrecognized at-rules. `@font-face` blocks pass through unscoped unless they reference local fragments via `url(#...)`, which is rejected; note that font-family names remain document-global, so identically named fonts from different panels collide (last one wins)

### Fixed
- `SVGDocument.root` now returns an independent snapshot and the constructor copies caller-owned element trees, so direct lxml mutations cannot alter an immutable document or make its cached ID index stale
- SVG composition isolates IDs, fragment references, selectors, keyframes, nested CSS, SMIL timing, and generated animation provenance across panels
- Composed nested viewports preserve nonzero viewBoxes, root presentation state, transforms, and accurate bounding boxes
- Path bounds now handle transformed arcs, compact arc flags, smooth `S`/`T` controls, nested SVG viewports, and `d="none"`
- Malformed `d` attributes degrade to their valid prefix (matching browser rendering) instead of failing whole-document APIs, and percentage or unit-bearing nested viewport dimensions parse leniently instead of raising
- Composed panels no longer clip content outside the source viewBox, fabricate clipping viewports from percentage or physical-unit dimensions, rewrite `url(#...)` fragments inside external URLs or `data-*` attributes, skip CSS placed after comments inside `<style>`, misclassify SMIL timing offsets, or reject minified `-.5s` animation shorthand
- `animate(effect='sequential')` falls back to animating all colorable elements when shapes lack IDs instead of silently animating nothing
- Repeated `legend()` calls no longer roll the viewBox back over edits the user made between calls (with the default `expand_viewbox=True`, `width`/`height` are still recomputed from the expanded viewBox), and gradient legends accept `labels=[]` to render a color bar without tick labels
- Repeated legends replace only library-owned legends, restore the source canvas, and compute stable bounds for every supported position and direction
- Missing-value coloring protects explicitly mapped group descendants and ignores non-rendering SVG resource geometry
- Generated animations use collision-safe names and private ownership metadata, including multi-digit generated class suffixes

## [0.3.1] - 2026-07-18

### Added
- Official Python 3.14 support (`requires-python` now `>=3.10,<3.15`)
- CI linting with ruff and type checking with pyrefly
- Dependabot weekly updates for GitHub Actions and pip dependencies

### Changed
- CI/publish workflows use `actions/checkout@v7` and `actions/setup-python@v6`
- Package classifier set to Production/Stable

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

[0.4.0]: https://github.com/yigityargili991/pathy_svg/releases/tag/v0.4.0
[0.3.1]: https://github.com/yigityargili991/pathy_svg/releases/tag/v0.3.1
[0.3.0]: https://github.com/yigityargili991/pathy_svg/releases/tag/v0.3.0
[0.2.0]: https://github.com/yigityargili991/pathy_svg/releases/tag/v0.2.0
[0.1.3]: https://github.com/yigityargili991/pathy_svg/releases/tag/v0.1.3
[0.1.2]: https://github.com/yigityargili991/pathy_svg/releases/tag/v0.1.2
[0.1.1]: https://github.com/yigityargili991/pathy_svg/releases/tag/v0.1.1
[0.1.0]: https://github.com/yigityargili991/pathy_svg/releases/tag/v0.1.0
