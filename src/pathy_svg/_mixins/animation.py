"""Mixin for CSS animation injection."""

from __future__ import annotations


class AnimationMixin:
    """CSS animation methods."""

    __slots__ = ()

    def animate(
        self,
        *,
        effect: str = "pulse",
        duration: float = 2.0,
        delay_by: str = "value",
        loop: bool = True,
    ):
        """Inject CSS animation into the SVG.

        Args:
            effect: The animation effect to apply (e.g. "pulse").
            duration: Animation duration in seconds.
            delay_by: Strategy for stagger delays ("value" or None).
            loop: Whether the animation should loop infinitely.

        Returns:
            A new SVGDocument with the CSS animation injected.
        """
        from pathy_svg.animation import inject_animation

        clone = self._clone()
        inject_animation(
            clone._tree,
            clone._nsmap,
            effect=effect,
            duration=duration,
            delay_by=delay_by,
            loop=loop,
            data_order=None,
        )
        return clone
