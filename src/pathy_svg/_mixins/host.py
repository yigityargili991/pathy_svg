"""TYPE_CHECKING host members mixins use on the composed document.

These stubs must not exist at runtime: mixins precede ``SVGDocumentBase``
in the document MRO, so a real ``_clone`` here would shadow the base
implementation.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Self, TypeVar

if TYPE_CHECKING:
    from lxml import etree

    from pathy_svg.themes import CategoricalPalette, ColorScale
    from pathy_svg.transform import ViewBox

_T = TypeVar("_T")


class _DocumentMixinHost:
    """Attributes and methods implemented by ``SVGDocumentBase`` and sibling mixins."""

    __slots__ = ()

    if TYPE_CHECKING:

        @property
        def _tree(self) -> etree._ElementTree: ...

        @property
        def _nsmap(self) -> dict[str, str]: ...

        @property
        def _last_scale(self) -> ColorScale | None: ...

        @_last_scale.setter
        def _last_scale(self, value: ColorScale | None) -> None: ...

        @property
        def _last_categorical_palette(self) -> CategoricalPalette | None: ...

        @_last_categorical_palette.setter
        def _last_categorical_palette(
            self, value: CategoricalPalette | None
        ) -> None: ...

        @property
        def _root(self) -> etree._Element: ...

        @property
        def viewbox(self) -> ViewBox | None: ...

        @property
        def dimensions(self) -> tuple[float | None, float | None]: ...

        def _clone(self) -> Self: ...

        def _with_owned_tree(
            self,
            tree: etree._ElementTree,
            *,
            _nsmap: dict[str, str] | None = None,
        ) -> Self: ...

        def _resolve_key_attr(
            self, data: Mapping[str, _T], key_attr: str
        ) -> tuple[dict[str, _T], dict[str, etree._Element]]: ...

        def heatmap(
            self,
            data: Mapping[str, float],
            *,
            palette: str | Sequence[str] = "RdYlBu_r",
            vmin: float | None = None,
            vmax: float | None = None,
            vcenter: float | None = None,
            na_color: str = "#cccccc",
            breaks: Sequence[float] | None = None,
            opacity: float | None = None,
            preserve_stroke: bool = True,
            color_missing: bool = True,
            key_attr: str = "id",
        ) -> Self: ...
