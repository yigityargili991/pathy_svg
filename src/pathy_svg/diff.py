"""Compare two datasets on the same SVG — delta, ratio, side-by-side."""

from __future__ import annotations

import math

from lxml import etree

from pathy_svg.transform import ViewBox, parse_viewbox

SVG_NS = "http://www.w3.org/2000/svg"


def compute_diff(
    baseline: dict[str, float],
    treatment: dict[str, float],
    *,
    mode: str = "delta",
) -> dict[str, float]:
    """Compute per-key differences between two datasets.

    Modes: "delta" (t-b), "ratio" (t/b), "log2ratio" (log2(t/b)), "percent_change" ((t-b)/b * 100).
    """
    common = set(baseline) & set(treatment)
    result = {}

    for k in common:
        b, t = baseline[k], treatment[k]
        if mode == "delta":
            result[k] = t - b
        elif mode == "ratio":
            result[k] = t / b if b != 0 else float("inf")
        elif mode == "log2ratio":
            if b > 0 and t > 0:
                result[k] = math.log2(t / b)
            else:
                result[k] = float("nan")
        elif mode == "percent_change":
            result[k] = ((t - b) / b * 100) if b != 0 else float("inf")
        else:
            raise ValueError(f"Unknown diff mode: {mode!r}")

    return result


def compose_side_by_side(
    docs: list,
    titles: list[str] | None = None,
    *,
    layout: str = "horizontal",
    spacing: float = 20,
    title_size: float = 14,
) -> etree._ElementTree:
    """Combine multiple SVGDocuments into a single SVG, side by side.

    Returns a new lxml ElementTree.
    """
    if not docs:
        raise ValueError("No documents to compose")

    viewboxes = []
    trees = []
    for doc in docs:
        vb = doc.viewbox
        if vb is None:
            vb = ViewBox(0, 0, 500, 500)
        viewboxes.append(vb)
        trees.append(doc._tree)

    if layout == "horizontal":
        total_w = sum(vb.width for vb in viewboxes) + spacing * (len(docs) - 1)
        max_h = max(vb.height for vb in viewboxes)
        title_offset = title_size * 1.5 if titles else 0
        total_h = max_h + title_offset
    else:  # vertical
        max_w = max(vb.width for vb in viewboxes)
        total_h = sum(vb.height for vb in viewboxes) + spacing * (len(docs) - 1)
        title_offset = title_size * 1.5 if titles else 0
        total_h += title_offset * len(docs) if titles else 0
        total_w = max_w

    new_root = etree.Element(
        f"{{{SVG_NS}}}svg",
        nsmap={None: SVG_NS},
    )
    new_root.set("viewBox", f"0 0 {total_w} {total_h}")
    new_root.set("width", str(total_w))
    new_root.set("height", str(total_h))

    x_offset = 0.0
    y_offset = 0.0

    for i, (doc, vb) in enumerate(zip(docs, viewboxes)):
        if titles and i < len(titles):
            txt = etree.SubElement(new_root, f"{{{SVG_NS}}}text")
            if layout == "horizontal":
                txt.set("x", str(x_offset + vb.width / 2))
                txt.set("y", str(title_size))
            else:
                txt.set("x", str(vb.width / 2))
                txt.set("y", str(y_offset + title_size))
            txt.set("text-anchor", "middle")
            txt.set("style", f"font-size:{title_size}px;font-family:sans-serif;font-weight:bold")
            txt.text = titles[i]

        g = etree.SubElement(new_root, f"{{{SVG_NS}}}g")
        if layout == "horizontal":
            tx = x_offset - vb.x
            ty = title_offset - vb.y
            g.set("transform", f"translate({tx},{ty})")
        else:
            tx = -vb.x
            ty = y_offset + (title_offset if titles else 0) - vb.y
            g.set("transform", f"translate({tx},{ty})")

        # Copy all children of the source root
        source_root = doc._tree.getroot()
        for child in source_root:
            g.append(__import__("copy").deepcopy(child))

        if layout == "horizontal":
            x_offset += vb.width + spacing
        else:
            y_offset += vb.height + spacing + (title_offset if titles else 0)

    return etree.ElementTree(new_root)
