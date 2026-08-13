"""Mixin for the layer system entry point."""

from __future__ import annotations

from typing import TYPE_CHECKING

from typing_extensions import Self

if TYPE_CHECKING:
    from pathy_svg.layers import LayerManager


class LayerMixin:
    """Provides the layers() method for multi-layer composition."""

    __slots__ = ()

    def layers(self) -> LayerManager[Self]:
        """Create a LayerManager for composing named visualization layers.

        Returns:
            A new LayerManager initialized with this document as the base.
        """
        from pathy_svg.layers import LayerManager

        return LayerManager(self)
