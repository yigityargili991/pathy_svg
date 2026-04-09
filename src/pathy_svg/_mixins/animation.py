"""Mixin for CSS animation injection."""

from __future__ import annotations

from pathy_svg.animation import AnimationEffect


class AnimationMixin:
    """CSS animation methods."""

    __slots__ = ()

    def animate(
        self,
        *,
        effect: AnimationEffect = "pulse",
        duration: float = 2.0,
        loop: bool = True,
    ):
        """Inject CSS animation into the SVG.

        Args:
            effect: The animation effect to apply (e.g. "pulse").
            duration: Animation duration in seconds.
            loop: Whether the animation should loop infinitely.

        Returns:
            A new SVGDocument with the CSS animation injected.
        """
        from pathy_svg.animation import inject_animation

        clone = self._clone()
        inject_animation(
            clone._tree,
            effect=effect,
            duration=duration,
            loop=loop,
        )
        return clone
