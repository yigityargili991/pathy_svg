"""Mixin for serialization and display methods."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from lxml import etree

if TYPE_CHECKING:
    from os import PathLike


class SerializationMixin:
    """SVG serialization and Jupyter repr methods."""

    __slots__ = ()

    def to_string(self) -> str:
        """Serialize to an SVG string."""
        return etree.tostring(
            self._tree,
            pretty_print=True,
            encoding="unicode",
        )

    def to_bytes(self) -> bytes:
        """Serialize to SVG bytes (UTF-8)."""
        return etree.tostring(
            self._tree,
            pretty_print=True,
            xml_declaration=True,
            encoding="utf-8",
        )

    def save(
        self,
        path: str | PathLike,
        *,
        pretty_print: bool = True,
        xml_declaration: bool = True,
    ) -> None:
        """Write the SVG to a file."""
        path = Path(path)
        path.write_bytes(
            etree.tostring(
                self._tree,
                pretty_print=pretty_print,
                xml_declaration=xml_declaration,
                encoding="utf-8",
            )
        )

    def _repr_svg_(self) -> str:
        """Render inline in Jupyter notebooks."""
        return self.to_string()

    def _repr_mimebundle_(self, include=None, exclude=None) -> dict[str, str]:
        """Prefer raw SVG output in rich frontends."""
        if include is not None and "image/svg+xml" not in include:
            return {}
        if exclude is not None and "image/svg+xml" in exclude:
            return {}
        return {"image/svg+xml": self.to_string()}

    def _repr_html_(self) -> str:
        """HTML fallback for Jupyter."""
        return self.to_string()

