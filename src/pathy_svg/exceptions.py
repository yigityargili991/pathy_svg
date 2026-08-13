"""Custom exception hierarchy for pathy_svg."""

from __future__ import annotations

from collections.abc import Mapping


class PathySVGError(Exception):
    """Base exception for all pathy_svg errors.

    Args:
        message: The error message.
        details: Optional dictionary containing context or additional details.
    """

    def __init__(
        self, message: str, *, details: Mapping[str, object] | None = None
    ) -> None:
        super().__init__(message)
        self.details = dict(details) if details is not None else {}


class SVGParseError(PathySVGError):
    """Malformed SVG or XML parsing failure."""


class PathNotFoundError(PathySVGError):
    """Referenced path ID doesn't exist in the SVG."""


class ExportError(PathySVGError):
    """CairoSVG not installed, write failure, or other export issue."""


class ValidationError(PathySVGError, ValueError):
    """Generic validation error (viewBox missing, etc.)."""


class DataMappingError(ValidationError):
    """Column not found, type mismatch, or other data mapping issue."""


class ColorScaleError(ValidationError):
    """Invalid palette name, bad breaks configuration, etc."""


class CompositionError(ValidationError):
    """An SVG composition cannot be completed safely."""
