"""SVGDocument — composed from mixins for clean separation of concerns."""

from pathy_svg._base import SVGDocumentBase
from pathy_svg._mixins.coloring import ColoringMixin
from pathy_svg._mixins.export import ExportMixin
from pathy_svg._mixins.overlay import OverlayMixin
from pathy_svg._mixins.serialization import SerializationMixin


class SVGDocument(
    ColoringMixin,
    OverlayMixin,
    ExportMixin,
    SerializationMixin,
    SVGDocumentBase,
):
    """Immutable wrapper around a parsed SVG document.

    Every mutation method returns a new SVGDocument — the original is never modified.
    Supports method chaining: ``doc.heatmap(...).legend(...).save(...)``.
    """

    pass
