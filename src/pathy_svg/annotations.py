"""Text labels, tooltips, and markers on SVG paths."""

from __future__ import annotations

from typing import Literal

from lxml import etree

from pathy_svg._constants import SVG_NS, build_id_index, svg_sub
from pathy_svg._css import set_style_property
from pathy_svg.transform import bbox_of_element, centroid_of_bbox

Placement = Literal["centroid", "above", "below", "bbox_corner"]
TooltipMethod = Literal["title", "css"]


def add_text_labels(
    tree: etree._ElementTree,
    nsmap: dict,
    labels: dict[str, str],
    *,
    placement: Placement = "centroid",
    font_size: float = 12,
    font_color: str = "black",
    font_family: str = "sans-serif",
    background: str | None = None,
    offset: tuple[float, float] = (0, 0),
    id_to_elem: dict[str, etree._Element] | None = None,
) -> None:
    """Add text labels to SVG elements. Modifies tree in-place."""
    root = tree.getroot()
    g = svg_sub(root, "g")
    g.set("id", "pathy-annotations")
    if id_to_elem is None:
        id_to_elem = build_id_index(tree)

    for eid, text in labels.items():
        elem = id_to_elem.get(eid)
        if elem is None:
            continue

        bbox = bbox_of_element(elem, nsmap)
        if bbox is None:
            continue

        cx, cy = centroid_of_bbox(bbox)

        if placement == "above":
            cy = bbox.y - font_size
        elif placement == "below":
            cy = bbox.y + bbox.height + font_size
        elif placement == "bbox_corner":
            cx, cy = bbox.x, bbox.y

        cx += offset[0]
        cy += offset[1]

        if background:
            # Estimate text width (rough: 0.6 * font_size * len)
            tw = 0.6 * font_size * len(text)
            th = font_size * 1.4
            bg_rect = svg_sub(g, "rect")
            bg_rect.set("x", str(cx - tw / 2 - 2))
            bg_rect.set("y", str(cy - th / 2 - 2))
            bg_rect.set("width", str(tw + 4))
            bg_rect.set("height", str(th + 4))
            bg_rect.set("fill", background)
            bg_rect.set("rx", "2")

        txt = svg_sub(g, "text")
        txt.set("x", str(cx))
        txt.set("y", str(cy + font_size / 3))  # vertical center adjustment
        txt.set("text-anchor", "middle")
        txt.set(
            "style",
            f"fill:{font_color};font-size:{font_size}px;font-family:{font_family}",
        )
        txt.text = text


def add_tooltips(
    tree: etree._ElementTree,
    nsmap: dict,
    tips: dict[str, str],
    *,
    method: TooltipMethod = "title",
    id_to_elem: dict[str, etree._Element] | None = None,
) -> None:
    """Add tooltips to SVG elements. Modifies tree in-place.

    Methods:
        - "title": Adds a <title> child element (native SVG tooltip).
        - "css": Injects a CSS hover popup using a <style> block.
    """
    if id_to_elem is None:
        id_to_elem = build_id_index(tree)
    id_index = id_to_elem

    if method == "title":
        for eid, tip_text in tips.items():
            elem = id_index.get(eid)
            if elem is None:
                continue
            # Remove existing <title> if any
            for existing in elem:
                if existing.tag == f"{{{SVG_NS}}}title" or existing.tag == "title":
                    elem.remove(existing)
                    break
            title = etree.SubElement(elem, f"{{{SVG_NS}}}title")
            title.text = tip_text

    elif method == "css":
        root = tree.getroot()
        # Find or create <defs>
        defs = root.find(f"{{{SVG_NS}}}defs")
        if defs is None:
            defs = etree.SubElement(root, f"{{{SVG_NS}}}defs")
            root.insert(0, defs)

        style = defs.find(f"{{{SVG_NS}}}style[@id='pathy-tooltip-style']")
        if style is None:
            style = etree.SubElement(
                defs, f"{{{SVG_NS}}}style", id="pathy-tooltip-style"
            )
        style.text = (
            ".pathy-tooltip { display: none; pointer-events: none; }\n"
            "[data-tooltip]:hover + .pathy-tooltip { display: inline; }"
        )

        for eid, tip_text in tips.items():
            elem = id_index.get(eid)
            if elem is None:
                continue

            elem.set("data-tooltip", tip_text)

            for existing in list(tree.iter()):
                if existing.get("data-tooltip-for") == eid:
                    parent = existing.getparent()
                    if parent is not None:
                        parent.remove(existing)

            parent = elem.getparent()
            if parent is None:
                continue

            bbox = bbox_of_element(elem, nsmap)
            if bbox is None:
                x, y = 0.0, 0.0
            else:
                x = bbox.x + bbox.width / 2
                y = bbox.y - 8

            tw = max(24.0, 0.6 * 12 * len(tip_text))
            th = 18.0

            tooltip = etree.Element(f"{{{SVG_NS}}}g")
            tooltip.set("class", "pathy-tooltip")
            tooltip.set("data-tooltip-for", eid)

            bg = svg_sub(tooltip, "rect")
            bg.set("x", str(x - tw / 2 - 4))
            bg.set("y", str(y - th))
            bg.set("width", str(tw + 8))
            bg.set("height", str(th))
            bg.set("rx", "3")
            bg.set("fill", "black")
            bg.set("fill-opacity", "0.75")

            txt = svg_sub(tooltip, "text")
            txt.set("x", str(x))
            txt.set("y", str(y - 5))
            txt.set("text-anchor", "middle")
            txt.set("style", "fill:white;font-size:12px;font-family:sans-serif")
            txt.text = tip_text

            parent.insert(parent.index(elem) + 1, tooltip)


def replace_text(
    tree: etree._ElementTree,
    replacements: dict[str, str],
    *,
    text_color: str | None = None,
) -> None:
    """Replace text content in <text> elements throughout the SVG."""
    for elem in tree.iter():
        tag = elem.tag
        if isinstance(tag, str) and (tag.endswith("}text") or tag == "text"):
            if elem.text and elem.text.strip() in replacements:
                elem.text = replacements[elem.text.strip()]
                if text_color:
                    elem.set("style", set_style_property(
                        elem.get("style"), "fill", text_color,
                    ))
