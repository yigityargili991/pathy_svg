"""Shared constants and helpers used across pathy_svg modules."""

from __future__ import annotations

import re
from typing import Literal

from lxml import etree

SVG_NS = "http://www.w3.org/2000/svg"

Layout = Literal["horizontal", "vertical"]

COLORABLE_TAGS = frozenset({"path", "rect", "circle", "ellipse", "polygon", "polyline"})
NON_RENDERING_CONTAINERS = frozenset(
    {
        "clipPath",
        "defs",
        "filter",
        "hatch",
        "linearGradient",
        "marker",
        "mask",
        "meshgradient",
        "pattern",
        "radialGradient",
        "solidcolor",
        "symbol",
    }
)


def local_tag(tag: object) -> str:
    """Return a tag's local name, or ``""`` for non-element nodes.

    lxml represents comment and processing-instruction tags with callable
    sentinel objects rather than strings.  Treating them as having no local
    element name lets callers safely skip them while walking a mixed XML tree.
    """
    if not isinstance(tag, str):
        return ""
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def rendered_colorable_elements(root: etree._Element) -> list[etree._Element]:
    """Return rendered geometry, pruning SVG definition/resource subtrees."""
    elements: list[etree._Element] = []

    def collect(element: etree._Element, *, in_resource: bool = False) -> None:
        tag = local_tag(element.tag)
        in_resource = in_resource or tag in NON_RENDERING_CONTAINERS
        if not in_resource and tag in COLORABLE_TAGS:
            elements.append(element)
        for child in element:
            if isinstance(child.tag, str):
                collect(child, in_resource=in_resource)

    collect(root)
    return elements


def svg_sub(parent, tag: str):
    """Create a namespaced SVG sub-element."""
    return etree.SubElement(parent, f"{{{SVG_NS}}}{tag}")


def get_secure_parser() -> etree.XMLParser:
    """Create an XML parser that disables entity resolution and network access."""
    return etree.XMLParser(resolve_entities=False, no_network=True)


_UNSAFE_ID_RE = re.compile(r"[^A-Za-z0-9_-]")


def safe_svg_id(raw: str) -> str:
    """Sanitise *raw* into a valid XML/SVG id value.

    The result is deterministic: the same *raw* always produces the same
    output.  A short hash suffix is appended so that distinct inputs
    which sanitise to the same base string (e.g. ``"a/b"`` and
    ``"a b"``) still produce distinct IDs.
    """
    import hashlib

    base = _UNSAFE_ID_RE.sub("_", raw)
    # 6 hex chars → 16M buckets; enough to prevent accidental collisions
    # among attribute values in a single SVG.
    suffix = hashlib.sha256(raw.encode()).hexdigest()[:6]
    return f"{base}_{suffix}"


def build_id_index(tree) -> dict:
    """Build a dict mapping element id -> element for O(1) lookup.

    First element wins for duplicate IDs (consistent with XML spec).
    """
    return build_attr_index(tree, "id")


def build_attr_index(tree, attr: str = "id") -> dict:
    """Build a dict mapping element attribute value -> element for O(1) lookup.

    First element wins for duplicate values.
    """
    index = {}
    for elem in tree.iter():
        val = elem.get(attr)
        if val:
            index.setdefault(val, elem)
    return index
