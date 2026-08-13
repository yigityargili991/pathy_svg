"""Geometric helpers — bounding boxes, centroids, viewBox math, SVG transforms."""

from __future__ import annotations

import math
import re
from typing import NamedTuple

import numpy as np

from pathy_svg._constants import local_tag


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
    x_min = min(b.x for b in boxes)
    y_min = min(b.y for b in boxes)
    x_max = max(b.x + b.width for b in boxes)
    y_max = max(b.y + b.height for b in boxes)
    return BBox(x_min, y_min, x_max - x_min, y_max - y_min)


# Re-export: placed here (not at top) to break a circular import
# (path_parser imports BBox from this module).
from pathy_svg.path_parser import bbox_from_path_d


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
    tag = local_tag(element.tag)

    # Build this element's full transform: parent's accumulated @ own local.
    # A nested <svg> additionally maps its child user space through its viewport.
    local_matrix = _element_coordinate_transform(element)

    if _accumulated_transform is None:
        # Top-level call: walk ancestors once to seed the accumulated transform
        _accumulated_transform = _get_ancestor_transform(element)

    current_transform = _accumulated_transform @ local_matrix

    if tag == "path":
        d = element.get("d")
        if d and d.strip().lower() != "none":
            # Path candidates must be evaluated after the affine transform.
            # Transforming a local AABB would include empty corner regions and
            # substantially overestimate rotated/skewed partial arcs.
            return bbox_from_path_d(d, _matrix_as_affine(current_transform))
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
            rx = ry = float(element.get("r", 0))
        else:
            rx = float(element.get("rx", 0))
            ry = float(element.get("ry", 0))
        return _transformed_ellipse_bbox(cx, cy, rx, ry, current_transform)
    elif tag in ("polygon", "polyline"):
        points_attr = element.get("points", "")
        coords = re.split(r"[\s,]+", points_attr.strip())
        if len(coords) >= 2:
            floats = [float(c) for c in coords if c]
            xs = floats[0::2]
            ys = floats[1::2]
            if xs and ys:
                box = BBox(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
            else:
                return None
        else:
            return None
    elif tag in ("g", "svg"):
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


def _matrix_as_affine(
    matrix: np.ndarray,
) -> tuple[float, float, float, float, float, float]:
    """Return an SVG-style affine tuple from a homogeneous matrix."""
    return (
        float(matrix[0, 0]),
        float(matrix[1, 0]),
        float(matrix[0, 1]),
        float(matrix[1, 1]),
        float(matrix[0, 2]),
        float(matrix[1, 2]),
    )


def _transformed_ellipse_bbox(
    cx: float, cy: float, rx: float, ry: float, matrix: np.ndarray
) -> BBox:
    """Return the exact AABB of an axis-aligned ellipse after an affine transform."""
    transformed_center = matrix @ np.array([cx, cy, 1.0])
    x_radius = math.hypot(matrix[0, 0] * rx, matrix[0, 1] * ry)
    y_radius = math.hypot(matrix[1, 0] * rx, matrix[1, 1] * ry)
    center_x = float(transformed_center[0])
    center_y = float(transformed_center[1])
    return BBox(
        center_x - x_radius,
        center_y - y_radius,
        2 * x_radius,
        2 * y_radius,
    )


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
    """Walk upward, composing ancestor transforms and nested SVG viewports.

    Unlike the element's own transform (handled in bbox_of_element), this only
    collects coordinate mappings from parent elements upward.
    """
    result = _identity()
    current = element.getparent()
    while current is not None:
        result = _element_coordinate_transform(current) @ result
        current = current.getparent()
    return result


def _element_coordinate_transform(element) -> np.ndarray:
    """Return the mapping from an element's child user space to its parent."""
    viewport = _identity()
    if local_tag(element.tag) == "svg" and element.getparent() is not None:
        viewport = _svg_viewport_transform(element)

    transform_attr = element.get("transform")
    if transform_attr:
        return _parse_transform(transform_attr) @ viewport
    return viewport


def _svg_viewport_transform(element) -> np.ndarray:
    """Map a nested ``svg`` viewBox into its viewport.

    Supports the default ``xMidYMid meet``, ``none``, and all standard
    xMin/xMid/xMax + YMin/YMid/YMax alignments with ``meet`` or ``slice``.
    """
    x = float(element.get("x", 0))
    y = float(element.get("y", 0))
    viewbox_attr = element.get("viewBox")
    if not viewbox_attr:
        return _translate(x, y)

    viewbox = parse_viewbox(viewbox_attr)
    if viewbox.width == 0 or viewbox.height == 0:
        return _translate(x, y)

    width = float(element.get("width", viewbox.width))
    height = float(element.get("height", viewbox.height))
    scale_x = width / viewbox.width
    scale_y = height / viewbox.height

    preserve = element.get("preserveAspectRatio", "xMidYMid meet").strip().split()
    if preserve and preserve[0] == "defer":
        preserve = preserve[1:]
    alignment = preserve[0] if preserve else "xMidYMid"
    if alignment == "none":
        return (
            _translate(x, y)
            @ _scale(scale_x, scale_y)
            @ _translate(-viewbox.x, -viewbox.y)
        )

    meet_or_slice = preserve[1] if len(preserve) > 1 else "meet"
    uniform_scale = (
        max(scale_x, scale_y) if meet_or_slice == "slice" else min(scale_x, scale_y)
    )
    remaining_x = width - viewbox.width * uniform_scale
    remaining_y = height - viewbox.height * uniform_scale
    x_alignment = 0.0 if alignment.startswith("xMin") else 1.0
    if alignment.startswith("xMid"):
        x_alignment = 0.5
    y_alignment = 0.0 if "YMin" in alignment else 1.0
    if "YMid" in alignment:
        y_alignment = 0.5

    return (
        _translate(
            x + remaining_x * x_alignment,
            y + remaining_y * y_alignment,
        )
        @ _scale(uniform_scale)
        @ _translate(-viewbox.x, -viewbox.y)
    )


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
