## 2024-04-14 - Keyboard accessible CSS tooltips
**Learning:** SVG tooltips built using CSS `:hover` states inherently exclude keyboard users who navigate via `Tab`.
**Action:** Always verify keyboard focusability (e.g., `tabindex="0"`) and visibility (CSS `:focus` outlines and visibility triggers) when introducing hover-based interactions in generated UI artifacts like SVGs. Provide descriptive `aria-label` attributes derived from tooltip content for screen readers.
