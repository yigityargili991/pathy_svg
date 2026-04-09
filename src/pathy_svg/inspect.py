"""Introspection — list paths, viewBox info, validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from lxml import etree

from pathy_svg._constants import COLORABLE_TAGS, local_tag
from pathy_svg.transform import BBox, bbox_of_element


@dataclass(frozen=True)
class PathInfo:
    """Detailed info about a single SVG element.

    Args:
        id: The element's ID.
        tag: The element's local tag name (e.g., 'path', 'g').
        bbox: The bounding box of the element, if it could be calculated.
        fill: The extracted fill color, if any.
        stroke: The extracted stroke color, if any.
        classes: List of CSS classes applied to the element.
        parent_group: The ID of the parent <g> element, if any.
        d_length: Length of the 'd' attribute string for paths.
    """

    id: str
    tag: str
    bbox: BBox | None = None
    fill: str | None = None
    stroke: str | None = None
    classes: list[str] = field(default_factory=list)
    parent_group: str | None = None
    d_length: int | None = None


@dataclass(frozen=True)
class ValidationResult:
    """Result of validating data IDs against SVG element IDs.

    Args:
        matched: List of IDs present in both data and SVG.
        unmatched: List of IDs present in data but not in SVG.
        unused: List of IDs present in SVG but not in data.
    """

    matched: list[str]
    unmatched: list[str]  # in data but not in SVG
    unused: list[str]  # in SVG but not in data

    @property
    def is_valid(self) -> bool:
        return len(self.unmatched) == 0


def _get_fill(elem: etree._Element) -> str | None:
    """Extract fill color from an element (style attr or fill attr)."""
    style = elem.get("style", "")
    if "fill:" in style:
        import re

        m = re.search(r"fill:\s*([^;]+)", style)
        if m:
            return m.group(1).strip()
    return elem.get("fill")


def _get_stroke(elem: etree._Element) -> str | None:
    """Extract stroke color from an element."""
    style = elem.get("style", "")
    if "stroke:" in style:
        import re

        m = re.search(r"stroke:\s*([^;]+)", style)
        if m:
            return m.group(1).strip()
    return elem.get("stroke")


def _get_classes(elem: etree._Element) -> list[str]:
    cls = elem.get("class", "")
    return cls.split() if cls else []


def _get_parent_group_id(elem: etree._Element) -> str | None:
    parent = elem.getparent()
    while parent is not None:
        if local_tag(parent.tag) == "g":
            pid = parent.get("id")
            if pid:
                return pid
        parent = parent.getparent()
    return None


def inspect_paths(tree: etree._ElementTree, nsmap: dict) -> list[PathInfo]:
    """Return detailed info about all elements with IDs in the SVG.

    Args:
        tree: The ElementTree of the SVG.
        nsmap: Namespace map of the document.

    Returns:
        A list of PathInfo objects describing each colorable element.
    """
    results = []

    for elem in tree.iter():
        local = local_tag(elem.tag)
        eid = elem.get("id")
        if not eid or local not in COLORABLE_TAGS:
            continue

        bbox = bbox_of_element(elem, nsmap)
        d = elem.get("d")

        results.append(
            PathInfo(
                id=eid,
                tag=local,
                bbox=bbox,
                fill=_get_fill(elem),
                stroke=_get_stroke(elem),
                classes=_get_classes(elem),
                parent_group=_get_parent_group_id(elem),
                d_length=len(d) if d else None,
            )
        )

    return results


def validate_ids(
    tree: etree._ElementTree, nsmap: dict, ids: Iterable[str]
) -> ValidationResult:
    """Check which data IDs match elements in the SVG.

    Args:
        tree: The ElementTree of the SVG.
        nsmap: Namespace map of the document.
        ids: An iterable of IDs from the dataset.

    Returns:
        A ValidationResult containing matched, unmatched, and unused IDs.
    """
    svg_ids = set()
    for elem in tree.iter():
        eid = elem.get("id")
        if eid:
            svg_ids.add(eid)

    data_ids = list(ids)
    data_set = set(data_ids)

    matched = [i for i in data_ids if i in svg_ids]
    unmatched = [i for i in data_ids if i not in svg_ids]
    unused = sorted(svg_ids - data_set)

    return ValidationResult(matched=matched, unmatched=unmatched, unused=unused)
