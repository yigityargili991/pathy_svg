"""Mixin for CSS animation injection."""

from __future__ import annotations

from collections.abc import Sequence

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
        data_order: Sequence[str] | None = None,
    ):
        """Inject CSS animation into the SVG.

        Args:
            effect: The animation effect to apply (e.g. "pulse").
            duration: Animation duration in seconds.
            loop: Whether the animation should loop infinitely.
            data_order: Element IDs to stagger in order for the ``"sequential"``
                effect. When omitted, colorable element IDs are discovered in
                document order. Elements without IDs are skipped.

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
            data_order=data_order,
        )
        return clone
