"""Shared constants and helpers used across pathy_svg modules."""

from __future__ import annotations

from typing import Literal

from lxml import etree

SVG_NS = "http://www.w3.org/2000/svg"

Layout = Literal["horizontal", "vertical"]

COLORABLE_TAGS = frozenset({"path", "rect", "circle", "ellipse", "polygon", "polyline"})


def local_tag(tag: str) -> str:
    """Strip namespace prefix from a tag, e.g. '{http://...}path' -> 'path'."""
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def svg_sub(parent, tag: str):
    """Create a namespaced SVG sub-element."""
    return etree.SubElement(parent, f"{{{SVG_NS}}}{tag}")


def build_id_index(tree) -> dict:
    """Build a dict mapping element id -> element for O(1) lookup.

    First element wins for duplicate IDs (consistent with XML spec).
    """
    index = {}
    for elem in tree.iter():
        eid = elem.get("id")
        if eid:
            index.setdefault(eid, elem)
    return index
