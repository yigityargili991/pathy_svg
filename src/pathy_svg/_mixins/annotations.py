"""Mixin for text annotation, tooltip, and text replacement methods."""

from __future__ import annotations

from pathy_svg.annotations import Placement, TooltipMethod


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
            clone._tree,
            clone._nsmap,
            resolved_tips,
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
