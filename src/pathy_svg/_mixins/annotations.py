"""Mixin for text annotation, tooltip, and text replacement methods."""

from __future__ import annotations

from lxml import etree

from pathy_svg._constants import SVG_NS
from pathy_svg.annotations import Placement, TooltipMethod
from pathy_svg.transform import ViewBox


def _frange(start: float, stop: float, step: float):
    """Yield floats from start to stop (inclusive) in fixed steps."""
    n = int((stop - start) / step) + 1
    for i in range(n):
        yield start + i * step


class AnnotationMixin:
    """Annotate, tooltip, and text replacement methods."""

    __slots__ = ()

    def annotate(
        self,
        labels: dict[str, str],
        *,
        placement: Placement = "centroid",
        font_size: float = 12,
        font_color: str = "black",
        font_family: str = "sans-serif",
        background: str | None = None,
        offset: tuple[float, float] = (0, 0),
        key_attr: str = "id",
    ):
        """Add text labels to paths.

        Args:
            labels: A dictionary mapping element attribute values to text labels.
            placement: Placement strategy for the text ("centroid" or other supported strategies).
            font_size: Font size for the labels.
            font_color: Font color for the labels.
            font_family: CSS font-family string.
            background: Optional background color for the text (creates a bounding box).
            offset: An (x, y) tuple specifying offset for the text placement.
            key_attr: Element attribute used to match data keys (default ``"id"``).

        Returns:
            A new SVGDocument with the text labels added.
        """
        from pathy_svg.annotations import add_text_labels

        clone = self._clone()
        resolved_labels, resolved_index = clone._resolve_key_attr(labels, key_attr)
        add_text_labels(
            clone._tree,
            clone._nsmap,
            resolved_labels,
            placement=placement,
            font_size=font_size,
            font_color=font_color,
            font_family=font_family,
            background=background,
            offset=offset,
            id_to_elem=resolved_index,
        )
        clone._id_index = None
        return clone

    def add_tooltips(
        self,
        tips: dict[str, str],
        *,
        method: TooltipMethod = "title",
        key_attr: str = "id",
    ):
        """Add tooltips to paths.

        Args:
            tips: A dictionary mapping element attribute values to tooltip text.
            method: The method to inject tooltips ("title" for `<title>` tags).
            key_attr: Element attribute used to match data keys (default ``"id"``).

        Returns:
            A new SVGDocument with the tooltips injected.
        """
        from pathy_svg.annotations import add_tooltips

        clone = self._clone()
        resolved_tips, resolved_index = clone._resolve_key_attr(tips, key_attr)
        add_tooltips(
            clone._tree, clone._nsmap, resolved_tips,
            method=method,
            id_to_elem=resolved_index,
        )
        clone._id_index = None
        return clone

    def replace_text(
        self,
        replacements: dict[str, str],
        *,
        text_color: str | None = None,
    ):
        """Replace text content in <text> elements.

        Args:
            replacements: A dictionary mapping existing text content to new text.
            text_color: Optional hex color string to apply to the modified text.

        Returns:
            A new SVGDocument with the text replaced.
        """
        from pathy_svg.annotations import replace_text

        clone = self._clone()
        replace_text(clone._tree, replacements, text_color=text_color)
        return clone

    def xy_guide(self, *, color: str = "red", step: float = 50):
        """Return a copy with a coordinate grid overlay for orientation."""
        clone = self._clone()
        vb = clone.viewbox
        if vb is None:
            return clone

        root = clone.root
        ns = root.nsmap.get(None, SVG_NS)
        g = etree.SubElement(root, f"{{{ns}}}g" if ns else "g", id="pathy-guide")
        g.set("style", f"stroke:{color};stroke-width:0.5;fill:none;opacity:0.5")

        for x in _frange(vb.x, vb.x + vb.width, step):
            line = etree.SubElement(g, f"{{{ns}}}line" if ns else "line")
            line.set("x1", str(x))
            line.set("y1", str(vb.y))
            line.set("x2", str(x))
            line.set("y2", str(vb.y + vb.height))
            txt = etree.SubElement(g, f"{{{ns}}}text" if ns else "text")
            txt.set("x", str(x + 2))
            txt.set("y", str(vb.y + 12))
            txt.set("style", f"fill:{color};font-size:8px;stroke:none")
            txt.text = str(int(x))

        for y in _frange(vb.y, vb.y + vb.height, step):
            line = etree.SubElement(g, f"{{{ns}}}line" if ns else "line")
            line.set("x1", str(vb.x))
            line.set("y1", str(y))
            line.set("x2", str(vb.x + vb.width))
            line.set("y2", str(y))
            txt = etree.SubElement(g, f"{{{ns}}}text" if ns else "text")
            txt.set("x", str(vb.x + 2))
            txt.set("y", str(y - 2))
            txt.set("style", f"fill:{color};font-size:8px;stroke:none")
            txt.text = str(int(y))

        return clone
