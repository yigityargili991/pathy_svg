## 2024-04-18 - Improved accessibility of CSS-based tooltips
**Learning:** Pure CSS tooltips generated via Python needed accessibility attributes (tabindex, aria-label) baked into the generated SVG elements, along with `:focus` and `:focus-visible` states added to the injected CSS block to support keyboard navigation.
**Action:** When adding tooltip features that modify SVG elements, always consider accessibility by adding tab navigation and screen reader support to the generated output.
