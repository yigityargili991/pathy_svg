"""SVG path ``d`` attribute tokenizer and bounding-box approximation."""

from __future__ import annotations

import math
import re

from pathy_svg.transform import BBox

Affine = tuple[float, float, float, float, float, float]
_IDENTITY_AFFINE: Affine = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

_PATH_NUMBER_RE = re.compile(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")
_PATH_COMMAND_ARITY = {
    "M": 2,
    "L": 2,
    "H": 1,
    "V": 1,
    "C": 6,
    "S": 4,
    "Q": 4,
    "T": 2,
    "A": 7,
}


def _tokenize_path_d(d: str) -> list[str | float]:
    """Tokenize an SVG path ``d`` attribute using command-aware arc flags.

    Arc flags are single ``0``/``1`` characters in the SVG grammar and need
    not be separated from one another or from the following coordinate.  A
    generic number regex would incorrectly read ``0110`` as one value rather
    than flags ``0``, ``1`` and coordinate ``10``.
    """
    tokens: list[str | float] = []
    command: str | None = None
    parameter_count = 0
    index = 0

    def _validate_parameter_count() -> None:
        if command is None or command.upper() == "Z":
            return
        arity = _PATH_COMMAND_ARITY[command.upper()]
        if parameter_count == 0 or parameter_count % arity:
            raise ValueError(f"Incomplete parameters for SVG path command {command!r}")

    while index < len(d):
        char = d[index]
        if char.isspace() or char == ",":
            index += 1
            continue

        if char in "MmZzLlHhVvCcSsQqTtAa":
            _validate_parameter_count()
            command = char
            parameter_count = 0
            tokens.append(char)
            index += 1
            continue

        if command is None or command.upper() == "Z":
            raise ValueError(
                f"Unexpected character in SVG path at offset {index}: {char!r}"
            )

        parameter_index = parameter_count % _PATH_COMMAND_ARITY[command.upper()]
        if command.upper() == "A" and parameter_index in (3, 4):
            if char not in "01":
                raise ValueError(f"Invalid SVG arc flag at offset {index}: {char!r}")
            tokens.append(float(char))
            index += 1
        else:
            match = _PATH_NUMBER_RE.match(d, index)
            if match is None:
                raise ValueError(f"Invalid SVG path number at offset {index}: {char!r}")
            tokens.append(float(match.group()))
            index = match.end()
        parameter_count += 1

    _validate_parameter_count()
    return tokens


def _angle_on_arc(angle: float, start: float, delta: float) -> bool:
    """Return whether ``angle`` lies within the directed arc sweep."""
    tau = 2 * math.pi
    tolerance = 1e-12
    if delta >= 0:
        return (angle - start) % tau <= delta + tolerance
    return (start - angle) % tau <= -delta + tolerance


def _transform_point(
    point: tuple[float, float], transform: Affine
) -> tuple[float, float]:
    """Apply an SVG-style affine transform to a point."""
    x, y = point
    a, b, c, d, e, f = transform
    return a * x + c * y + e, b * x + d * y + f


def _arc_extrema(
    start: tuple[float, float],
    end: tuple[float, float],
    rx: float,
    ry: float,
    rotation: float,
    large_arc: float,
    sweep: float,
    transform: Affine = _IDENTITY_AFFINE,
) -> list[tuple[float, float]]:
    """Return a transformed SVG arc's endpoint and in-sweep axis extrema.

    The conversion from endpoint to center parameterization follows the SVG
    implementation notes.  The ellipse's parametric coefficients are then
    transformed before its output-space x/y extrema are solved.  Returning
    only extrema that lie on the directed sweep makes the resulting
    axis-aligned bounds exact for non-degenerate arcs under any affine
    transform.
    """
    x1, y1 = start
    x2, y2 = end
    rx, ry = abs(rx), abs(ry)

    # A zero radius is a straight line. Identical endpoints omit the segment.
    # In either case the endpoint is sufficient for bounding-box purposes.
    if rx == 0 or ry == 0 or (x1 == x2 and y1 == y2):
        return [_transform_point(end, transform)]

    phi = math.radians(rotation % 360)
    cos_phi = math.cos(phi)
    sin_phi = math.sin(phi)

    dx = (x1 - x2) / 2
    dy = (y1 - y2) / 2
    x1_prime = cos_phi * dx + sin_phi * dy
    y1_prime = -sin_phi * dx + cos_phi * dy

    # Scale radii up uniformly when the supplied ellipse cannot reach both
    # endpoints, as required by SVG's out-of-range radii correction.
    radii_scale = (x1_prime / rx) ** 2 + (y1_prime / ry) ** 2
    radii_were_scaled = radii_scale > 1
    if radii_were_scaled:
        scale = math.sqrt(radii_scale)
        rx *= scale
        ry *= scale

    rx2 = rx * rx
    ry2 = ry * ry
    # Corrected radii put the endpoints at opposite ends of the ellipse, so
    # the center coefficient is exactly zero.  Assigning it directly avoids
    # cancellation leaving a tiny, geometrically incorrect center offset.
    numerator = (
        0.0
        if radii_were_scaled
        else max(
            0.0,
            rx2 * ry2 - rx2 * y1_prime * y1_prime - ry2 * x1_prime * x1_prime,
        )
    )
    denominator = rx2 * y1_prime * y1_prime + ry2 * x1_prime * x1_prime
    if denominator == 0:
        return [_transform_point(end, transform)]

    sign = -1.0 if bool(large_arc) == bool(sweep) else 1.0
    coefficient = sign * math.sqrt(numerator / denominator)
    cx_prime = coefficient * rx * y1_prime / ry
    cy_prime = -coefficient * ry * x1_prime / rx

    center_x = cos_phi * cx_prime - sin_phi * cy_prime + (x1 + x2) / 2
    center_y = sin_phi * cx_prime + cos_phi * cy_prime + (y1 + y2) / 2

    ux = (x1_prime - cx_prime) / rx
    uy = (y1_prime - cy_prime) / ry
    vx = (-x1_prime - cx_prime) / rx
    vy = (-y1_prime - cy_prime) / ry
    start_angle = math.atan2(uy, ux)
    delta_angle = math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
    if not sweep and delta_angle > 0:
        delta_angle -= 2 * math.pi
    elif sweep and delta_angle < 0:
        delta_angle += 2 * math.pi

    # Before transformation, the ellipse is center + cosine*P + sine*Q.
    # Transforming P and Q gives the output-space derivative coefficients,
    # whose roots are the exact extrema of the transformed arc.
    a, b, c, d, e, f = transform
    local_x_cos = rx * cos_phi
    local_x_sin = -ry * sin_phi
    local_y_cos = rx * sin_phi
    local_y_sin = ry * cos_phi
    output_x_cos = a * local_x_cos + c * local_y_cos
    output_x_sin = a * local_x_sin + c * local_y_sin
    output_y_cos = b * local_x_cos + d * local_y_cos
    output_y_sin = b * local_x_sin + d * local_y_sin
    output_center_x = a * center_x + c * center_y + e
    output_center_y = b * center_x + d * center_y + f

    # dX/dtheta and dY/dtheta each have two roots per full ellipse.
    x_extremum = math.atan2(output_x_sin, output_x_cos)
    y_extremum = math.atan2(output_y_sin, output_y_cos)
    candidates = (
        x_extremum,
        x_extremum + math.pi,
        y_extremum,
        y_extremum + math.pi,
    )

    points = [_transform_point(end, transform)]
    for angle in candidates:
        if _angle_on_arc(angle, start_angle, delta_angle):
            cos_angle = math.cos(angle)
            sin_angle = math.sin(angle)
            points.append(
                (
                    output_center_x
                    + output_x_cos * cos_angle
                    + output_x_sin * sin_angle,
                    output_center_y
                    + output_y_cos * cos_angle
                    + output_y_sin * sin_angle,
                )
            )
    return points


def bbox_from_path_d(d: str, transform: Affine | None = None) -> BBox:
    """Compute an approximate bounding box from an SVG path ``d`` attribute.

    Handles M, L, H, V, C, S, Q, T, A, Z commands (both absolute and relative).
    Elliptical-arc extrema are computed exactly, including after an affine
    transform.  For Bézier curves, the bounding box is approximated using
    transformed control points rather than solving for the true geometric
    extrema.  This means the result may overestimate the actual bounds,
    especially for paths with highly curved Bézier segments whose control
    points lie far outside the drawn curve.  The approximation is sufficient
    for label placement and centroid calculation but should not be relied on
    for pixel-precise clipping or hit-testing.

    Args:
        d: The SVG path 'd' attribute string.
        transform: Optional SVG-style ``(a, b, c, d, e, f)`` affine transform
            applied before candidate extrema are evaluated.

    Returns:
        An approximate BBox for the path.
    """
    # SVG 2 exposes path data as the ``d`` property, whose ``none`` keyword is
    # ASCII case-insensitive and represents no rendered geometry.
    if d.strip().lower() == "none":
        return BBox(0, 0, 0, 0)

    tokens = _tokenize_path_d(d)
    if not tokens:
        return BBox(0, 0, 0, 0)

    affine = transform or _IDENTITY_AFFINE
    points: list[tuple[float, float]] = []
    cx, cy = 0.0, 0.0
    sx, sy = 0.0, 0.0
    previous_command: str | None = None
    cubic_control: tuple[float, float] | None = None
    quadratic_control: tuple[float, float] | None = None
    i = 0

    def _next_float() -> float:
        nonlocal i
        i += 1
        return float(tokens[i])

    def _add_point(x: float, y: float) -> None:
        points.append(_transform_point((x, y), affine))

    def _add_points(*new_points: tuple[float, float]) -> None:
        points.extend(_transform_point(point, affine) for point in new_points)

    def _finish_segment(
        command: str,
        *,
        cubic: tuple[float, float] | None = None,
        quadratic: tuple[float, float] | None = None,
    ) -> None:
        """Record command state used by a following smooth curve segment."""
        nonlocal previous_command, cubic_control, quadratic_control
        previous_command = command.upper()
        cubic_control = cubic if previous_command in ("C", "S") else None
        quadratic_control = quadratic if previous_command in ("Q", "T") else None

    while i < len(tokens):
        tok = tokens[i]

        if tok == "M":
            cx, cy = _next_float(), _next_float()
            sx, sy = cx, cy
            _add_point(cx, cy)
            _finish_segment("M")
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                cx, cy = _next_float(), _next_float()
                _add_point(cx, cy)
                _finish_segment("L")
        elif tok == "m":
            cx += _next_float()
            cy += _next_float()
            sx, sy = cx, cy
            _add_point(cx, cy)
            _finish_segment("M")
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                cx += _next_float()
                cy += _next_float()
                _add_point(cx, cy)
                _finish_segment("L")
        elif tok == "L":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                cx, cy = _next_float(), _next_float()
                _add_point(cx, cy)
                _finish_segment("L")
        elif tok == "l":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                cx += _next_float()
                cy += _next_float()
                _add_point(cx, cy)
                _finish_segment("L")
        elif tok == "H":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                cx = _next_float()
                _add_point(cx, cy)
                _finish_segment("H")
        elif tok == "h":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                cx += _next_float()
                _add_point(cx, cy)
                _finish_segment("H")
        elif tok == "V":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                cy = _next_float()
                _add_point(cx, cy)
                _finish_segment("V")
        elif tok == "v":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                cy += _next_float()
                _add_point(cx, cy)
                _finish_segment("V")
        elif tok == "C":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                x1, y1 = _next_float(), _next_float()
                x2, y2 = _next_float(), _next_float()
                cx, cy = _next_float(), _next_float()
                _add_points((x1, y1), (x2, y2), (cx, cy))
                _finish_segment("C", cubic=(x2, y2))
        elif tok == "c":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                x1 = cx + _next_float()
                y1 = cy + _next_float()
                x2 = cx + _next_float()
                y2 = cy + _next_float()
                cx += _next_float()
                cy += _next_float()
                _add_points((x1, y1), (x2, y2), (cx, cy))
                _finish_segment("C", cubic=(x2, y2))
        elif tok == "S":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                if previous_command in ("C", "S") and cubic_control is not None:
                    x1, y1 = 2 * cx - cubic_control[0], 2 * cy - cubic_control[1]
                else:
                    x1, y1 = cx, cy
                x2, y2 = _next_float(), _next_float()
                cx, cy = _next_float(), _next_float()
                _add_points((x1, y1), (x2, y2), (cx, cy))
                _finish_segment("S", cubic=(x2, y2))
        elif tok == "s":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                if previous_command in ("C", "S") and cubic_control is not None:
                    x1, y1 = 2 * cx - cubic_control[0], 2 * cy - cubic_control[1]
                else:
                    x1, y1 = cx, cy
                x2 = cx + _next_float()
                y2 = cy + _next_float()
                cx += _next_float()
                cy += _next_float()
                _add_points((x1, y1), (x2, y2), (cx, cy))
                _finish_segment("S", cubic=(x2, y2))
        elif tok == "Q":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                x1, y1 = _next_float(), _next_float()
                cx, cy = _next_float(), _next_float()
                _add_points((x1, y1), (cx, cy))
                _finish_segment("Q", quadratic=(x1, y1))
        elif tok == "q":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                x1 = cx + _next_float()
                y1 = cy + _next_float()
                cx += _next_float()
                cy += _next_float()
                _add_points((x1, y1), (cx, cy))
                _finish_segment("Q", quadratic=(x1, y1))
        elif tok == "T":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                if previous_command in ("Q", "T") and quadratic_control is not None:
                    x1 = 2 * cx - quadratic_control[0]
                    y1 = 2 * cy - quadratic_control[1]
                else:
                    x1, y1 = cx, cy
                cx, cy = _next_float(), _next_float()
                _add_points((x1, y1), (cx, cy))
                _finish_segment("T", quadratic=(x1, y1))
        elif tok == "t":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                if previous_command in ("Q", "T") and quadratic_control is not None:
                    x1 = 2 * cx - quadratic_control[0]
                    y1 = 2 * cy - quadratic_control[1]
                else:
                    x1, y1 = cx, cy
                cx += _next_float()
                cy += _next_float()
                _add_points((x1, y1), (cx, cy))
                _finish_segment("T", quadratic=(x1, y1))
        elif tok == "A":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                rx, ry = _next_float(), _next_float()
                rotation = _next_float()
                large_arc, sweep = _next_float(), _next_float()
                start = (cx, cy)
                cx, cy = _next_float(), _next_float()
                points.extend(
                    _arc_extrema(
                        start,
                        (cx, cy),
                        rx,
                        ry,
                        rotation,
                        large_arc,
                        sweep,
                        affine,
                    )
                )
                _finish_segment("A")
        elif tok == "a":
            while i + 1 < len(tokens) and isinstance(tokens[i + 1], float):
                rx, ry = _next_float(), _next_float()
                rotation = _next_float()
                large_arc, sweep = _next_float(), _next_float()
                start = (cx, cy)
                cx += _next_float()
                cy += _next_float()
                points.extend(
                    _arc_extrema(
                        start,
                        (cx, cy),
                        rx,
                        ry,
                        rotation,
                        large_arc,
                        sweep,
                        affine,
                    )
                )
                _finish_segment("A")
        elif tok in ("Z", "z"):
            cx, cy = sx, sy
            _finish_segment("Z")

        i += 1

    if not points:
        return BBox(0, 0, 0, 0)

    xs, ys = zip(*points)
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    return BBox(x_min, y_min, x_max - x_min, y_max - y_min)
