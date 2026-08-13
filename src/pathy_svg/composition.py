"""Public result types for collision-safe SVG composition."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from pathy_svg._constants import Layout
from pathy_svg.document import SVGDocument


@dataclass(frozen=True)
class PanelComposition:
    """ID metadata for one source panel in a composed SVG.

    ``id_map`` maps each source ID to its output ID. Malformed SVGs may contain
    duplicate source IDs; in that case the first occurrence is reported,
    matching SVG fragment lookup semantics.
    """

    index: int
    wrapper_id: str
    id_map: Mapping[str, str]

    @classmethod
    def _create(
        cls, index: int, wrapper_id: str, id_map: dict[str, str]
    ) -> PanelComposition:
        return cls(index, wrapper_id, MappingProxyType(dict(id_map)))

    def output_id(self, source_id: str) -> str:
        """Return the composed ID corresponding to ``source_id``.

        Raises:
            KeyError: If the source panel did not contain the requested ID.
        """
        return self.id_map[source_id]


@dataclass(frozen=True)
class CompositionResult:
    """A composed document together with per-panel ID mappings."""

    document: SVGDocument
    panels: tuple[PanelComposition, ...]

    def panel(self, index: int) -> PanelComposition:
        """Return metadata for a source panel by zero-based index."""
        return self.panels[index]


def compose_svgs(
    svgs: Iterable[SVGDocument],
    layout: Layout = "horizontal",
    spacing: float = 20,
) -> CompositionResult:
    """Compose documents and retain per-panel source-to-output ID mappings."""
    from pathy_svg.svg_tools import compose_svgs as _compose_svgs

    return _compose_svgs(svgs, layout=layout, spacing=spacing)
