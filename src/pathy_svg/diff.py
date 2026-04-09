"""Compare two datasets on the same SVG — delta, ratio, side-by-side."""

from __future__ import annotations

import copy
import math
from typing import TYPE_CHECKING, Callable, Literal

from lxml import etree

from pathy_svg._constants import SVG_NS, Layout
from pathy_svg.transform import ViewBox

if TYPE_CHECKING:
    from pathy_svg.document import SVGDocument

DiffMode = Literal["delta", "ratio", "log2ratio", "percent_change"]

_DIFF_OPS: dict[str, Callable[[float, float], float]] = {
    "delta": lambda b, t: t - b,
    "ratio": lambda b, t: t / b if b != 0 else float("inf"),
    "log2ratio": lambda b, t: math.log2(t / b) if b > 0 and t > 0 else float("nan"),
    "percent_change": lambda b, t: ((t - b) / b * 100) if b != 0 else float("inf"),
}


def compute_diff(
    baseline: dict[str, float],
    treatment: dict[str, float],
    *,
    mode: DiffMode = "delta",
) -> dict[str, float]:
    """Compute per-key differences between two datasets.

    Modes: "delta" (t-b), "ratio" (t/b), "log2ratio" (log2(t/b)), "percent_change" ((t-b)/b * 100).
    """
    op = _DIFF_OPS.get(mode)
    if op is None:
        raise ValueError(f"Unknown diff mode: {mode!r}")
    common = baseline.keys() & treatment.keys()
    return {k: op(baseline[k], treatment[k]) for k in common}


def compose_side_by_side(
    docs: list[SVGDocument],
    titles: list[str] | None = None,
    *,
    layout: Layout = "horizontal",
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
            txt.set(
                "style",
                f"font-size:{title_size}px;font-family:sans-serif;font-weight:bold",
            )
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
            g.append(copy.deepcopy(child))

        if layout == "horizontal":
            x_offset += vb.width + spacing
        else:
            y_offset += vb.height + spacing + (title_offset if titles else 0)

    return etree.ElementTree(new_root)
