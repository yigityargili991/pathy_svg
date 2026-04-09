"""Mixin classes for SVGDocument functionality."""

from pathy_svg._mixins.coloring import ColoringMixin
from pathy_svg._mixins.export import ExportMixin
from pathy_svg._mixins.overlay import OverlayMixin
from pathy_svg._mixins.serialization import SerializationMixin

__all__ = [
    "ColoringMixin",
    "ExportMixin",
    "OverlayMixin",
    "SerializationMixin",
]
