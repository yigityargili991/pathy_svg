"""Backward-compatible re-exports — **deprecated**.

The canonical locations are now:
- Color utilities: ``pathy_svg.color``
- Data utilities: ``pathy_svg.data``
- SVG tools: ``pathy_svg.svg_tools``

This module re-exports everything so existing ``from pathy_svg.utils import …``
continues to work, but it will be removed in a future version.
"""

import warnings

warnings.warn(
    "pathy_svg.utils is deprecated. Import from pathy_svg.color, "
    "pathy_svg.data, or pathy_svg.svg_tools directly.",
    DeprecationWarning,
    stacklevel=2,
)

from pathy_svg.color import hex_to_rgb, interpolate_color, parse_svg_color, rgb_to_hex
from pathy_svg.data import bin_values, dataframe_to_dict, normalize_values
from pathy_svg.svg_tools import (
    extract_styles,
    merge_svgs,
    optimize_svg,
    strip_metadata,
    viewbox_to_pixel,
)

__all__ = [
    "hex_to_rgb",
    "rgb_to_hex",
    "interpolate_color",
    "parse_svg_color",
    "normalize_values",
    "bin_values",
    "dataframe_to_dict",
    "viewbox_to_pixel",
    "merge_svgs",
    "strip_metadata",
    "optimize_svg",
    "extract_styles",
]
