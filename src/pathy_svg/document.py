"""SVGDocument — composed from mixins for clean separation of concerns."""

from pathy_svg._base import SVGDocumentBase
from pathy_svg._mixins.animation import AnimationMixin
from pathy_svg._mixins.annotations import AnnotationMixin
from pathy_svg._mixins.coloring import ColoringMixin
from pathy_svg._mixins.diff import DiffMixin
from pathy_svg._mixins.export import ExportMixin
from pathy_svg._mixins.layers import LayerMixin
from pathy_svg._mixins.legend import LegendMixin
from pathy_svg._mixins.serialization import SerializationMixin
from pathy_svg._mixins.style import StyleMixin


class SVGDocument(
    ColoringMixin,
    StyleMixin,
    LegendMixin,
    DiffMixin,
    AnnotationMixin,
    AnimationMixin,
    ExportMixin,
    SerializationMixin,
    LayerMixin,
    SVGDocumentBase,
):
    """Immutable wrapper around a parsed SVG document.

    Every mutation method returns a new SVGDocument — the original is never modified.
    Supports method chaining: ``doc.heatmap(...).legend(...).save(...)``.
    """

    pass
