"""Geometric helpers — bounding boxes, centroids, viewBox math, SVG path parsing."""

from __future__ import annotations

import math
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
    """Parse an SVG viewBox attribute string into a ViewBox.

    Args:
        attr: The viewBox string (e.g., "0 0 500 500").

    Returns:
        A ViewBox instance.

    Raises:
        ValueError: If the attribute does not contain exactly 4 numbers.
    """
    parts = re.split(r"[\s,]+", attr.strip())
    if len(parts) != 4:
        raise ValueError(f"Invalid viewBox: {attr!r}")
    return ViewBox(*[float(p) for p in parts])


def centroid_of_bbox(bbox: BBox) -> tuple[float, float]:
    """Return the center point of a bounding box.

    Args:
        bbox: The bounding box to compute the centroid for.

    Returns:
        A tuple of (x, y) coordinates representing the center.
    """
    return (bbox.x + bbox.width / 2, bbox.y + bbox.height / 2)


def bbox_union(boxes: list[BBox]) -> BBox:
    """Return the bounding box that encloses all given bounding boxes.

    Args:
        boxes: A list of BBox instances.

    Returns:
        A single BBox enclosing all provided boxes.

    Raises:
        ValueError: If the boxes list is empty.
    """
    if not boxes:
        raise ValueError("Cannot compute union of zero bounding boxes")
    xs = [b.x for b in boxes]
    ys = [b.y for b in boxes]
    x_min = min(xs)
    y_min = min(ys)
    x_max = max(b.x + b.width for b in boxes)
    y_max = max(b.y + b.height for b in boxes)
    return BBox(x_min, y_min, x_max - x_min, y_max - y_min)


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

    Args:
        d: The SVG path 'd' attribute string.

    Returns:
        An approximate BBox for the path.
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


def bbox_of_element(
    element, nsmap: dict, _accumulated_transform: np.ndarray | None = None
) -> BBox | None:
    """Compute bounding box for an SVG element (path, rect, circle, etc.).

    Accounts for SVG transform attributes on the element and all ancestor elements.

    Args:
        element: The lxml Element to compute the bounding box for.
        nsmap: Namespace map to assist in local tag extraction.

    Returns:
        The computed BBox, or None if it cannot be computed.
    """
    # Build this element's full transform: parent's accumulated @ own local
    local_attr = element.get("transform")
    local_matrix = _parse_transform(local_attr) if local_attr else None

    if _accumulated_transform is None:
        # Top-level call: walk ancestors once to seed the accumulated transform
        _accumulated_transform = _get_ancestor_transform(element)

    if local_matrix is not None:
        current_transform = _accumulated_transform @ local_matrix
    else:
        current_transform = _accumulated_transform

    tag = _local_tag(element.tag)

    if tag == "path":
        d = element.get("d")
        if d:
            box = bbox_from_path_d(d)
        else:
            return None
    elif tag == "rect":
        x = float(element.get("x", 0))
        y = float(element.get("y", 0))
        w = float(element.get("width", 0))
        h = float(element.get("height", 0))
        box = BBox(x, y, w, h)
    elif tag in ("circle", "ellipse"):
        cx = float(element.get("cx", 0))
        cy = float(element.get("cy", 0))
        if tag == "circle":
            r = float(element.get("r", 0))
            box = BBox(cx - r, cy - r, 2 * r, 2 * r)
        else:
            rx = float(element.get("rx", 0))
            ry = float(element.get("ry", 0))
            box = BBox(cx - rx, cy - ry, 2 * rx, 2 * ry)
    elif tag == "g":
        child_boxes = []
        for child in element:
            child_box = bbox_of_element(
                child, nsmap, _accumulated_transform=current_transform
            )
            if child_box is not None:
                child_boxes.append(child_box)
        if child_boxes:
            return bbox_union(child_boxes)
        return None
    else:
        return None

    if not np.allclose(current_transform, np.eye(3)):
        box = _transform_bbox(box, current_transform)

    return box


def _local_tag(tag: str) -> str:
    """Strip namespace prefix from a tag, e.g. '{http://...}path' -> 'path'."""
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


_TRANSFORM_RE = re.compile(
    r"(?P<func>translate|rotate|scale|skewX|skewY|matrix)"
    r"\((?P<args>[^)]*)\)"
)


def _parse_transform_list(s: str) -> list[float]:
    """Parse comma- or whitespace-separated floats from a transform argument string."""
    return [float(x) for x in re.split(r"[,\s]+", s.strip()) if x.strip()]


def _identity() -> np.ndarray:
    """Return a 3x3 identity matrix."""
    return np.eye(3, dtype=np.float64)


def _translate(tx: float, ty: float) -> np.ndarray:
    """Return a 3x3 translation matrix."""
    m = _identity()
    m[0, 2] = tx
    m[1, 2] = ty
    return m


def _rotate(angle_deg: float, cx: float = 0.0, cy: float = 0.0) -> np.ndarray:
    """Return a 3x3 rotation matrix (SVG uses degrees)."""
    angle_rad = math.radians(angle_deg)
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    if cx == 0.0 and cy == 0.0:
        return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=np.float64)
    # Rotate about (cx, cy): translate to origin, rotate, translate back
    return _translate(cx, cy) @ _rotate(angle_deg) @ _translate(-cx, -cy)


def _scale(sx: float, sy: float | None = None) -> np.ndarray:
    """Return a 3x3 scaling matrix."""
    if sy is None:
        sy = sx
    m = _identity()
    m[0, 0] = sx
    m[1, 1] = sy
    return m


def _skew_x(angle_deg: float) -> np.ndarray:
    """Return a 3x3 skewX matrix."""
    m = _identity()
    m[0, 1] = math.tan(math.radians(angle_deg))
    return m


def _skew_y(angle_deg: float) -> np.ndarray:
    """Return a 3x3 skewY matrix."""
    m = _identity()
    m[1, 0] = math.tan(math.radians(angle_deg))
    return m


def _matrix(a: float, b: float, c: float, d: float, e: float, f: float) -> np.ndarray:
    """Return a 3x3 matrix from SVG matrix(a,b,c,d,e,f) parameters."""
    return np.array([[a, c, e], [b, d, f], [0, 0, 1]], dtype=np.float64)


def _parse_transform(attr: str) -> np.ndarray:
    """Parse an SVG transform attribute into a single 3x3 transformation matrix.

    Multiple transforms are composed left-to-right (first transform is applied first).

    Args:
        attr: The transform attribute string, e.g. "translate(10,20) rotate(45)".

    Returns:
        A 3x3 numpy matrix representing the composed transformation.
    """
    result = _identity()
    for match in _TRANSFORM_RE.finditer(attr):
        func = match.group("func")
        args = _parse_transform_list(match.group("args"))
        if func == "translate":
            tx = args[0]
            ty = args[1] if len(args) > 1 else 0.0
            result = result @ _translate(tx, ty)
        elif func == "rotate":
            angle = args[0]
            cx = args[1] if len(args) > 2 else 0.0
            cy = args[2] if len(args) > 2 else 0.0
            result = result @ _rotate(angle, cx, cy)
        elif func == "scale":
            sx = args[0]
            sy = args[1] if len(args) > 1 else None
            result = result @ _scale(sx, sy)
        elif func == "skewX":
            result = result @ _skew_x(args[0])
        elif func == "skewY":
            result = result @ _skew_y(args[0])
        elif func == "matrix":
            result = result @ _matrix(*args[:6])
    return result


def _get_ancestor_transform(element) -> np.ndarray:
    """Walk from element's parent up to root, composing all ancestor transform attributes.

    Unlike the element's own transform (handled in bbox_of_element), this only
    collects transforms from parent elements upward.
    """
    result = _identity()
    current = element.getparent()
    while current is not None:
        transform_attr = current.get("transform")
        if transform_attr:
            local_matrix = _parse_transform(transform_attr)
            result = local_matrix @ result
        current = current.getparent()
    return result


def _transform_bbox(bbox: BBox, matrix: np.ndarray) -> BBox:
    """Apply a 3x3 transformation matrix to a bounding box.

    Transforms all four corners and returns the bounding box of the result.

    Args:
        bbox: The original BBox.
        matrix: A 3x3 transformation matrix.

    Returns:
        The transformed BBox.
    """
    corners = np.array(
        [
            [bbox.x, bbox.y, 1],
            [bbox.x + bbox.width, bbox.y, 1],
            [bbox.x, bbox.y + bbox.height, 1],
            [bbox.x + bbox.width, bbox.y + bbox.height, 1],
        ],
        dtype=np.float64,
    )
    transformed = (matrix @ corners.T).T
    x_min = float(transformed[:, 0].min())
    y_min = float(transformed[:, 1].min())
    x_max = float(transformed[:, 0].max())
    y_max = float(transformed[:, 1].max())
    return BBox(x_min, y_min, x_max - x_min, y_max - y_min)
