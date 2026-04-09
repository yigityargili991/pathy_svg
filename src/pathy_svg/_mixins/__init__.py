"""Mixin classes for SVGDocument functionality."""

from pathy_svg._mixins.animation import AnimationMixin
from pathy_svg._mixins.annotations import AnnotationMixin
from pathy_svg._mixins.coloring import ColoringMixin
from pathy_svg._mixins.diff import DiffMixin
from pathy_svg._mixins.export import ExportMixin
from pathy_svg._mixins.legend import LegendMixin
from pathy_svg._mixins.serialization import SerializationMixin

__all__ = [
    "AnimationMixin",
    "AnnotationMixin",
    "ColoringMixin",
    "DiffMixin",
    "ExportMixin",
    "LegendMixin",
    "SerializationMixin",
]
