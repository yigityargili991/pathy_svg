"""Shared constants and helpers used across pathy_svg modules."""

from __future__ import annotations

import re
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


def get_secure_parser():
    return etree.XMLParser(
        resolve_entities=False,
        no_network=True,
    )
