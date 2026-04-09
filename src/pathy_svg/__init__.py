"""pathy_svg — Color arbitrary SVG paths by data values."""

__version__ = "0.1.0"

from pathy_svg.document import SVGDocument
from pathy_svg.exceptions import (
    ColorScaleError,
    DataMappingError,
    ExportError,
    PathNotFoundError,
    PathySVGError,
    SVGParseError,
    ValidationError,
)
from pathy_svg.inspect import PathInfo, ValidationResult
from pathy_svg.themes import ColorScale, CategoricalPalette, ThemePreset
from pathy_svg.themes import medical, geographic, heatmap_classic
from pathy_svg.transform import BBox, ViewBox
from pathy_svg.color import hex_to_rgb, rgb_to_hex, interpolate_color, parse_svg_color
from pathy_svg.data import normalize_values, bin_values, dataframe_to_dict
from pathy_svg.utils import (
    viewbox_to_pixel,
    merge_svgs,
    strip_metadata,
    optimize_svg,
    extract_styles,
)

__all__ = [
    "__version__",
    "SVGDocument",
    # Exceptions
    "ColorScaleError",
    "DataMappingError",
    "ExportError",
    "PathNotFoundError",
    "PathySVGError",
    "SVGParseError",
    "ValidationError",
    # Data classes
    "PathInfo",
    "ValidationResult",
    "BBox",
    "ViewBox",
    # Themes
    "ColorScale",
    "CategoricalPalette",
    "ThemePreset",
    "medical",
    "geographic",
    "heatmap_classic",
    # Utils
    "hex_to_rgb",
    "rgb_to_hex",
    "interpolate_color",
    "parse_svg_color",
    "normalize_values",
    "bin_values",
    "viewbox_to_pixel",
    "merge_svgs",
    "strip_metadata",
    "optimize_svg",
    "extract_styles",
    "dataframe_to_dict",
]
