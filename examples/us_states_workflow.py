"""Example workflow: US States population density visualization.

Uses real 2023 US Census population estimates and state land areas
to create multiple visualizations with pathy_svg.
"""

from pathlib import Path

from pathy_svg import SVGDocument, GradientSpec, PatternSpec

HERE = Path(__file__).parent
SVG_PATH = HERE / "us_states.svg"
OUT_DIR = HERE / "output"
OUT_DIR.mkdir(exist_ok=True)

# ── Real data: 2023 estimated population (US Census Bureau) ──────────

population = {
    "CA": 38_965_193, "TX": 30_503_301, "FL": 22_610_726, "NY": 19_571_216,
    "PA": 12_961_683, "IL": 12_549_689, "OH": 11_785_935, "GA": 11_029_227,
    "NC": 10_835_491, "MI": 10_037_261, "NJ": 9_290_841, "VA": 8_642_274,
    "WA": 7_812_880, "AZ": 7_431_344, "TN": 7_126_489, "MA": 7_001_399,
    "IN": 6_862_199, "MO": 6_196_156, "MD": 6_180_253, "WI": 5_910_955,
    "CO": 5_877_610, "MN": 5_737_915, "SC": 5_373_555, "AL": 5_108_468,
    "LA": 4_573_749, "KY": 4_526_154, "OR": 4_233_358, "OK": 4_053_824,
    "CT": 3_617_176, "UT": 3_417_734, "IA": 3_207_004, "NV": 3_194_176,
    "AR": 3_067_732, "MS": 2_939_690, "KS": 2_940_546, "NM": 2_114_371,
    "NE": 1_978_379, "ID": 1_964_726, "WV": 1_770_071, "HI": 1_435_138,
    "NH": 1_402_054, "ME": 1_395_722, "MT": 1_132_812, "RI": 1_095_962,
    "DE": 1_031_890, "SD": 919_318, "ND": 783_926, "AK": 733_391,
    "DC": 678_972, "VT": 647_464, "WY": 584_057,
}

# ── Real data: land area in sq miles (US Census) ────────────────────

land_area = {
    "AK": 570641, "TX": 261232, "CA": 155779, "MT": 145546, "NM": 121298,
    "AZ": 113594, "NV": 109781, "CO": 103642, "OR": 95988, "WY": 97093,
    "MI": 56539, "UT": 82170, "MN": 79627, "ID": 82643, "KS": 81759,
    "NE": 76824, "SD": 75811, "WA": 66456, "ND": 69001, "OK": 68595,
    "MO": 68742, "FL": 53625, "WI": 54158, "GA": 57513, "IL": 55519,
    "IA": 55857, "NY": 47126, "NC": 48618, "AR": 52035, "AL": 50645,
    "LA": 43204, "MS": 46923, "PA": 44743, "OH": 40861, "VA": 39490,
    "TN": 41235, "KY": 39486, "IN": 35826, "ME": 30843, "SC": 30061,
    "WV": 24038, "MD": 9707, "HI": 6423, "MA": 7800, "VT": 9217,
    "NH": 8953, "NJ": 7354, "CT": 4842, "DE": 1949, "RI": 1034,
    "DC": 61,
}

# Compute population density (people per sq mile)
density = {
    st: population[st] / land_area[st]
    for st in population
    if st in land_area
}

# ── 1. Population heatmap ────────────────────────────────────────────

doc = SVGDocument.from_file(SVG_PATH)

pop_map = (
    doc.heatmap(population, palette="YlOrRd")
    .legend(title="Population", position=(0.86, 0.15), size=(0.02, 0.5))
)
pop_map.save(OUT_DIR / "01_population.svg")
print("Saved 01_population.svg")

# ── 2. Population density with viridis ───────────────────────────────

density_map = (
    doc.heatmap(density, palette="viridis")
    .legend(title="People / sq mi", position=(0.86, 0.15), size=(0.02, 0.5))
)
density_map.save(OUT_DIR / "02_density.svg")
print("Saved 02_density.svg")

# ── 3. Highlight top 10 most populous states ─────────────────────────

top10 = sorted(population, key=population.get, reverse=True)[:10]

highlighted = (
    doc.heatmap(population, palette="YlOrRd")
    .highlight(top10, dim_opacity=0.15, desaturate=True)
)
highlighted.save(OUT_DIR / "03_top10_highlighted.svg")
print("Saved 03_top10_highlighted.svg")

# ── 4. Pattern fill: high vs low density ─────────────────────────────

median_density = sorted(density.values())[len(density) // 2]

patterns = {}
for st, d in density.items():
    if d > median_density * 2:
        patterns[st] = PatternSpec(kind="dots", color="#b30000", spacing=5, thickness=1.5)
    elif d < median_density / 2:
        patterns[st] = PatternSpec(kind="diagonal_lines", color="#084594", spacing=8)

patterned = doc.pattern_fill(patterns)
patterned.save(OUT_DIR / "04_density_patterns.svg")
print("Saved 04_density_patterns.svg")

# ── 5. Gradient fills on selected states ─────────────────────────────

gradients = {
    "CA": GradientSpec(start="#fee08b", end="#d73027", direction="vertical"),
    "TX": GradientSpec(start="#d9ef8b", end="#1a9850", direction="horizontal"),
    "NY": GradientSpec(start="#e0f3f8", end="#4575b4", direction="diagonal"),
    "FL": GradientSpec(start="#fee08b", end="#f46d43", mid="#fdae61"),
}

gradient_map = doc.gradient_fill(gradients)
gradient_map.save(OUT_DIR / "05_gradient_fills.svg")
print("Saved 05_gradient_fills.svg")

# ── 6. Stroke mapping: border width by population ────────────────────

stroked = (
    doc.heatmap(density, palette="YlGnBu")
    .stroke_map(population, width_range=(0.3, 4.0))
)
stroked.save(OUT_DIR / "06_stroke_by_population.svg")
print("Saved 06_stroke_by_population.svg")

# ── 7. Layer composition ─────────────────────────────────────────────

layered = (
    doc.layers()
    .add("density", lambda d: d.heatmap(density, palette="YlGnBu"))
    .add("borders", lambda d: d.stroke_map(population, width_range=(0.5, 3.0)))
    .add("labels", lambda d: d.annotate(
        {st: st for st in top10},
        font_size=7,
        font_color="#222",
    ))
    .flatten()
    .legend(title="Density (people/sq mi)", position=(0.86, 0.15), size=(0.02, 0.5))
)
layered.save(OUT_DIR / "07_layered.svg")
print("Saved 07_layered.svg")

print(f"\nAll outputs in {OUT_DIR.resolve()}")
