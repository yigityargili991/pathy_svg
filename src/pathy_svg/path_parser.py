"""SVG path ``d`` attribute tokenizer and bounding-box approximation."""

from __future__ import annotations

import re

import numpy as np

from pathy_svg.transform import BBox

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
    """Compute an approximate bounding box from an SVG path ``d`` attribute.

    Handles M, L, H, V, C, S, Q, T, A, Z commands (both absolute and relative).
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
    cx, cy = 0.0, 0.0
    sx, sy = 0.0, 0.0
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
