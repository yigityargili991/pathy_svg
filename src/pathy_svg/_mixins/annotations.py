"""Mixin for text annotation, tooltip, and text replacement methods."""

from __future__ import annotations


class AnnotationMixin:
    """Annotate, tooltip, and text replacement methods."""

    __slots__ = ()

    def annotate(
        self,
        labels: dict[str, str],
        *,
        placement: str = "centroid",
        font_size: float = 12,
        font_color: str = "black",
        font_family: str = "sans-serif",
        background: str | None = None,
        offset: tuple[float, float] = (0, 0),
    ):
        """Add text labels to paths.

        Args:
            labels: A dictionary mapping path IDs to text labels.
            placement: Placement strategy for the text ("centroid" or other supported strategies).
            font_size: Font size for the labels.
            font_color: Font color for the labels.
            font_family: CSS font-family string.
            background: Optional background color for the text (creates a bounding box).
            offset: An (x, y) tuple specifying offset for the text placement.

        Returns:
            A new SVGDocument with the text labels added.
        """
        from pathy_svg.annotations import add_text_labels

        clone = self._clone()
        add_text_labels(
            clone._tree,
            clone._nsmap,
            labels,
            placement=placement,
            font_size=font_size,
            font_color=font_color,
            font_family=font_family,
            background=background,
            offset=offset,
        )
        return clone

    def add_tooltips(
        self,
        tips: dict[str, str],
        *,
        method: str = "title",
    ):
        """Add tooltips to paths.

        Args:
            tips: A dictionary mapping path IDs to tooltip text.
            method: The method to inject tooltips ("title" for `<title>` tags).

        Returns:
            A new SVGDocument with the tooltips injected.
        """
        from pathy_svg.annotations import add_tooltips

        clone = self._clone()
        add_tooltips(clone._tree, clone._nsmap, tips, method=method)
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
        replace_text(clone._tree, clone._nsmap, replacements, text_color=text_color)
        return clone
