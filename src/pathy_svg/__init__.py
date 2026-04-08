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
]
