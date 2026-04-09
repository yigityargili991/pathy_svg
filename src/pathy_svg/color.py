"""Color conversion utilities for pathy_svg."""

from __future__ import annotations

import colorsys
import re

import matplotlib.colors as _mcolors


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    """Convert a CSS hex colour string to an (R, G, B) int tuple.

    Supports both 6-digit (#rrggbb) and 3-digit (#rgb) shorthand forms.
    The leading ``#`` is optional.

    Args:
        hex_str: The hex color string to convert.

    Returns:
        A tuple of (R, G, B) integers in the range [0, 255].

    Raises:
        ValueError: If the hex string is invalid.

    Examples:
        >>> hex_to_rgb("#ff0000")  # (255, 0, 0)
        >>> hex_to_rgb("#f00")     # (255, 0, 0)
        >>> hex_to_rgb("00ff00")   # (0, 255, 0)
    """
    h = hex_str.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"Invalid hex colour: {hex_str!r}")
    try:
        r, g, b = bytes.fromhex(h)
    except ValueError as exc:
        raise ValueError(f"Invalid hex colour: {hex_str!r}") from exc
    return (r, g, b)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert (R, G, B) integers (0-255) to a lowercase CSS hex string.

    Args:
        r: Red channel value (0-255).
        g: Green channel value (0-255).
        b: Blue channel value (0-255).

    Returns:
        A lowercase CSS hex string (e.g., "#ff0000").

    Raises:
        ValueError: If any channel is out of the range [0, 255].

    Examples:
        >>> rgb_to_hex(255, 0, 0)    # "#ff0000"
        >>> rgb_to_hex(0, 128, 255)  # "#0080ff"
    """
    for name, val in (("r", r), ("g", g), ("b", b)):
        if not (0 <= val <= 255):
            raise ValueError(f"Channel {name} out of range [0, 255]: {val}")
    return f"#{r:02x}{g:02x}{b:02x}"


def interpolate_color(color1: str, color2: str, t: float) -> str:
    """Linearly interpolate between two hex colours.

    Args:
        color1: Starting colour (hex string, e.g. ``"#ff0000"``).
        color2: Ending colour (hex string).
        t: Interpolation factor in [0, 1]. ``t=0`` returns *color1*, ``t=1`` returns *color2*.

    Returns:
        Interpolated colour as a lowercase hex string.

    Raises:
        ValueError: If t is not in [0, 1].
    """
    if not (0.0 <= t <= 1.0):
        raise ValueError(f"Interpolation factor t must be in [0, 1], got {t}")
    r1, g1, b1 = hex_to_rgb(color1)
    r2, g2, b2 = hex_to_rgb(color2)
    r = round(r1 + (r2 - r1) * t)
    g = round(g1 + (g2 - g1) * t)
    b = round(b1 + (b2 - b1) * t)
    return rgb_to_hex(r, g, b)


def parse_svg_color(color_str: str) -> tuple[int, int, int]:
    """Parse a CSS/SVG colour string into an (R, G, B) int tuple.

    Supported formats:
    * Hex: ``"#rrggbb"`` or ``"#rgb"``
    * RGB function: ``"rgb(255, 0, 0)"``
    * HSL function: ``"hsl(0, 100%, 50%)"``
    * Named colours: ``"red"``, ``"blue"``, ``"transparent"``, etc.
      (all 140 CSS named colours via `matplotlib.colors`).

    Args:
        color_str: The SVG color string to parse.

    Returns:
        A tuple of (R, G, B) integers in the range [0, 255].

    Raises:
        ValueError: If the SVG color string is unrecognized or invalid.

    Examples:
        >>> parse_svg_color("red")              # (255, 0, 0)
        >>> parse_svg_color("#00ff00")          # (0, 255, 0)
        >>> parse_svg_color("rgb(0, 0, 255)")   # (0, 0, 255)
        >>> parse_svg_color("hsl(120, 100%, 50%)")  # (0, 255, 0)
    """
    s = color_str.strip().lower()

    if s.startswith("#"):
        return hex_to_rgb(s)

    m = re.fullmatch(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", s)
    if m:
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        for ch in (r, g, b):
            if not (0 <= ch <= 255):
                raise ValueError(f"RGB channel out of range [0, 255]: {ch}")
        return (r, g, b)

    m = re.fullmatch(
        r"hsl\(\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)%\s*,\s*(\d+(?:\.\d+)?)%\s*\)",
        s,
    )
    if m:
        h = float(m.group(1)) / 360.0
        sl = float(m.group(2)) / 100.0
        l = float(m.group(3)) / 100.0  # noqa: E741
        r_f, g_f, b_f = colorsys.hls_to_rgb(h, l, sl)
        return (round(r_f * 255), round(g_f * 255), round(b_f * 255))

    try:
        rgba = _mcolors.to_rgba(s)
        r = round(rgba[0] * 255)
        g = round(rgba[1] * 255)
        b = round(rgba[2] * 255)
        return (r, g, b)
    except ValueError:
        pass

    raise ValueError(f"Unrecognised SVG colour: {color_str!r}")
