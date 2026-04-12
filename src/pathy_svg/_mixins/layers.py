"""Mixin for the layer system entry point."""

from __future__ import annotations


class LayerMixin:
    """Provides the layers() method for multi-layer composition."""

    __slots__ = ()

    def layers(self):
        """Create a LayerManager for composing named visualization layers.

        Returns:
            A new LayerManager initialized with this document as the base.
        """
        from pathy_svg.layers import LayerManager

        return LayerManager(self)
