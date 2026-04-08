"""Geometric helpers — bounding boxes, centroids, viewBox math, SVG path parsing."""

from __future__ import annotations

import re
from typing import NamedTuple

import numpy as np


class ViewBox(NamedTuple):
    x: float
    y: float
    width: float
    height: float


class BBox(NamedTuple):
    x: float
    y: float
    width: float
    height: float


def parse_viewbox(attr: str) -> ViewBox:
    """Parse an SVG viewBox attribute string into a ViewBox."""
    parts = re.split(r"[\s,]+", attr.strip())
    if len(parts) != 4:
        raise ValueError(f"Invalid viewBox: {attr!r}")
    return ViewBox(*[float(p) for p in parts])


def centroid_of_bbox(bbox: BBox) -> tuple[float, float]:
    """Return the center point of a bounding box."""
    return (bbox.x + bbox.width / 2, bbox.y + bbox.height / 2)


def bbox_union(boxes: list[BBox]) -> BBox:
    """Return the bounding box that encloses all given bounding boxes."""
    if not boxes:
        raise ValueError("Cannot compute union of zero bounding boxes")
    xs = [b.x for b in boxes]
    ys = [b.y for b in boxes]
    x_min = min(xs)
    y_min = min(ys)
    x_max = max(b.x + b.width for b in boxes)
    y_max = max(b.y + b.height for b in boxes)
    return BBox(x_min, y_min, x_max - x_min, y_max - y_min)


# ---------------------------------------------------------------------------
# SVG path `d` attribute tokenizer & bbox calculator
# ---------------------------------------------------------------------------

_PATH_CMD_RE = re.compile(
    r"([MmZzLlHhVvCcSsQqTtAa])|([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)"
)


def _tokenize_path_d(d: str) -> list[str | float]:
    """Tokenize an SVG path `d` attribute into commands and numbers."""
    tokens: list[str | float] = []
    for match in _PATH_CMD_RE.finditer(d):
        cmd, num = match.groups()
        if cmd:
            tokens.append(cmd)
        else:
            tokens.append(float(num))
    return tokens


def bbox_from_path_d(d: str) -> BBox:
    """Compute an approximate bounding box from an SVG path `d` attribute.

    Handles M, L, H, V, C, S, Q, T, Z commands (both absolute and relative).
    For curves, uses control points — slightly overestimates but sufficient
    for label placement and centroid calculation.
    """
    tokens = _tokenize_path_d(d)
    if not tokens:
        return BBox(0, 0, 0, 0)

    points: list[tuple[float, float]] = []
    cx, cy = 0.0, 0.0  # current point
    sx, sy = 0.0, 0.0  # subpath start
    i = 0

    def _next_float() -> float:
        nonlocal i
        i += 1
        return float(tokens[i])

    while i < len(tokens):
        tok = tokens[i]

        if tok == "M":
            cx, cy = _next_float(), _next_float()
            sx, sy = cx, cy
            points.append((cx, cy))
            # Implicit L after M
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                cx, cy = _next_float(), _next_float()
                points.append((cx, cy))
        elif tok == "m":
            cx += _next_float()
            cy += _next_float()
            sx, sy = cx, cy
            points.append((cx, cy))
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                cx += _next_float()
                cy += _next_float()
                points.append((cx, cy))
        elif tok == "L":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                cx, cy = _next_float(), _next_float()
                points.append((cx, cy))
        elif tok == "l":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                cx += _next_float()
                cy += _next_float()
                points.append((cx, cy))
        elif tok == "H":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                cx = _next_float()
                points.append((cx, cy))
        elif tok == "h":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                cx += _next_float()
                points.append((cx, cy))
        elif tok == "V":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                cy = _next_float()
                points.append((cx, cy))
        elif tok == "v":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                cy += _next_float()
                points.append((cx, cy))
        elif tok == "C":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                x1, y1 = _next_float(), _next_float()
                x2, y2 = _next_float(), _next_float()
                cx, cy = _next_float(), _next_float()
                points.extend([(x1, y1), (x2, y2), (cx, cy)])
        elif tok == "c":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                x1 = cx + _next_float()
                y1 = cy + _next_float()
                x2 = cx + _next_float()
                y2 = cy + _next_float()
                cx += _next_float()
                cy += _next_float()
                points.extend([(x1, y1), (x2, y2), (cx, cy)])
        elif tok == "S":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                x2, y2 = _next_float(), _next_float()
                cx, cy = _next_float(), _next_float()
                points.extend([(x2, y2), (cx, cy)])
        elif tok == "s":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                x2 = cx + _next_float()
                y2 = cy + _next_float()
                cx += _next_float()
                cy += _next_float()
                points.extend([(x2, y2), (cx, cy)])
        elif tok == "Q":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                x1, y1 = _next_float(), _next_float()
                cx, cy = _next_float(), _next_float()
                points.extend([(x1, y1), (cx, cy)])
        elif tok == "q":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                x1 = cx + _next_float()
                y1 = cy + _next_float()
                cx += _next_float()
                cy += _next_float()
                points.extend([(x1, y1), (cx, cy)])
        elif tok == "T":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                cx, cy = _next_float(), _next_float()
                points.append((cx, cy))
        elif tok == "t":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                cx += _next_float()
                cy += _next_float()
                points.append((cx, cy))
        elif tok == "A":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                # rx, ry, x-rotation, large-arc, sweep, x, y
                _next_float()  # rx
                _next_float()  # ry
                _next_float()  # x-rotation
                _next_float()  # large-arc-flag
                _next_float()  # sweep-flag
                cx, cy = _next_float(), _next_float()
                points.append((cx, cy))
        elif tok == "a":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                _next_float()  # rx
                _next_float()  # ry
                _next_float()  # x-rotation
                _next_float()  # large-arc-flag
                _next_float()  # sweep-flag
                cx += _next_float()
                cy += _next_float()
                points.append((cx, cy))
        elif tok in ("Z", "z"):
            cx, cy = sx, sy

        i += 1

    if not points:
        return BBox(0, 0, 0, 0)

    arr = np.array(points)
    x_min, y_min = arr.min(axis=0)
    x_max, y_max = arr.max(axis=0)
    return BBox(float(x_min), float(y_min), float(x_max - x_min), float(y_max - y_min))


def bbox_of_element(element, nsmap: dict) -> BBox | None:
    """Compute bounding box for an SVG element (path, rect, circle, etc.)."""
    tag = _local_tag(element.tag)

    if tag == "path":
        d = element.get("d")
        if d:
            return bbox_from_path_d(d)
    elif tag == "rect":
        x = float(element.get("x", 0))
        y = float(element.get("y", 0))
        w = float(element.get("width", 0))
        h = float(element.get("height", 0))
        return BBox(x, y, w, h)
    elif tag in ("circle", "ellipse"):
        cx = float(element.get("cx", 0))
        cy = float(element.get("cy", 0))
        if tag == "circle":
            r = float(element.get("r", 0))
            return BBox(cx - r, cy - r, 2 * r, 2 * r)
        else:
            rx = float(element.get("rx", 0))
            ry = float(element.get("ry", 0))
            return BBox(cx - rx, cy - ry, 2 * rx, 2 * ry)
    elif tag == "g":
        # Union of children
        child_boxes = []
        for child in element:
            box = bbox_of_element(child, nsmap)
            if box is not None:
                child_boxes.append(box)
        if child_boxes:
            return bbox_union(child_boxes)

    return None


def _local_tag(tag: str) -> str:
    """Strip namespace prefix from a tag, e.g. '{http://...}path' -> 'path'."""
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag
