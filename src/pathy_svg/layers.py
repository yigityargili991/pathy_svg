"""Layer system — compose named visualization layers on a single SVG."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Generic, TypeVar

from pathy_svg.exceptions import ValidationError

_DocumentT = TypeVar("_DocumentT")


class LayerManager(Generic[_DocumentT]):
    """Immutable layer composition manager.

    Each layer is a named function that transforms an SVGDocument.
    Layers are applied in order during flatten().
    """

    __slots__ = ("_base", "_layers")

    def __init__(
        self,
        base: _DocumentT,
        _layers: list[tuple[str, Callable[[_DocumentT], _DocumentT], bool]]
        | None = None,
    ) -> None:
        self._base = base
        self._layers = list(_layers) if _layers is not None else []

    def _copy(
        self,
        layers: list[tuple[str, Callable[[_DocumentT], _DocumentT], bool]]
        | None = None,
    ) -> LayerManager[_DocumentT]:
        return LayerManager(self._base, layers if layers is not None else self._layers)

    def _find(self, name: str) -> int:
        for i, (n, _, _) in enumerate(self._layers):
            if n == name:
                return i
        return -1

    @property
    def names(self) -> list[str]:
        return [n for n, _, _ in self._layers]

    @property
    def visible(self) -> dict[str, bool]:
        return {n: v for n, _, v in self._layers}

    def add(
        self, name: str, fn: Callable[[_DocumentT], _DocumentT]
    ) -> LayerManager[_DocumentT]:
        if self._find(name) >= 0:
            raise ValidationError(f"Layer '{name}' already exists")
        new_layers = self._layers + [(name, fn, True)]
        return self._copy(new_layers)

    def hide(self, name: str) -> LayerManager[_DocumentT]:
        idx = self._find(name)
        if idx < 0:
            raise KeyError(f"Layer '{name}' not found")
        new_layers = list(self._layers)
        n, fn, _ = new_layers[idx]
        new_layers[idx] = (n, fn, False)
        return self._copy(new_layers)

    def show(self, name: str) -> LayerManager[_DocumentT]:
        idx = self._find(name)
        if idx < 0:
            raise KeyError(f"Layer '{name}' not found")
        new_layers = list(self._layers)
        n, fn, _ = new_layers[idx]
        new_layers[idx] = (n, fn, True)
        return self._copy(new_layers)

    def remove(self, name: str) -> LayerManager[_DocumentT]:
        idx = self._find(name)
        if idx < 0:
            raise KeyError(f"Layer '{name}' not found")
        new_layers = [layer for layer in self._layers if layer[0] != name]
        return self._copy(new_layers)

    def reorder(self, names: Sequence[str]) -> LayerManager[_DocumentT]:
        current_names = set(self.names)
        if set(names) != current_names or len(names) != len(self._layers):
            raise ValidationError(
                f"reorder() must contain exactly the same layer names. "
                f"Expected {sorted(current_names)}, got {sorted(names)}"
            )
        lookup = {n: (n, fn, v) for n, fn, v in self._layers}
        new_layers = [lookup[n] for n in names]
        return self._copy(new_layers)

    def flatten(self) -> _DocumentT:
        """Apply all visible layers in order and return the result."""
        doc = self._base._clone()
        for name, fn, vis in self._layers:
            if vis:
                doc = fn(doc)
        return doc
