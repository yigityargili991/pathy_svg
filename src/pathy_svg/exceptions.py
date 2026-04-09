"""Custom exception hierarchy for pathy_svg."""

from __future__ import annotations


class PathySVGError(Exception):
    """Base exception for all pathy_svg errors.

    Args:
        message: The error message.
        details: Optional dictionary containing context or additional details.
    """

    def __init__(self, message: str, *, details: dict | None = None):
        super().__init__(message)
        self.details = details or {}


class SVGParseError(PathySVGError):
    """Malformed SVG or XML parsing failure."""


class PathNotFoundError(PathySVGError):
    """Referenced path ID doesn't exist in the SVG."""


class DataMappingError(PathySVGError):
    """Column not found, type mismatch, or other data mapping issue."""


class ColorScaleError(PathySVGError):
    """Invalid palette name, bad breaks configuration, etc."""


class ExportError(PathySVGError):
    """CairoSVG not installed, write failure, or other export issue."""


class ValidationError(PathySVGError):
    """Generic validation error (viewBox missing, etc.)."""
