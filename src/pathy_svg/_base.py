"""SVGDocumentBase — core loading, querying, and cloning logic."""

from __future__ import annotations

import copy
import re
import urllib.request
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

from lxml import etree
from typing_extensions import Self

from pathy_svg._constants import (
    SVG_NS,
    build_attr_index,
    build_id_index,
    get_secure_parser,
)
from pathy_svg.exceptions import PathNotFoundError, SVGParseError, ValidationError
from pathy_svg.transform import (
    BBox,
    ViewBox,
    bbox_of_element,
    centroid_of_bbox,
    parse_viewbox,
)

if TYPE_CHECKING:
    from os import PathLike

    from pathy_svg.inspect import PathInfo, ValidationResult

_ValueT = TypeVar("_ValueT")


class SVGDocumentBase:
    """Core document functionality: loading, properties, querying, and cloning.

    Subclasses (via mixins) add coloring, overlay, export, and serialization.
    """

    __slots__ = (
        "_id_index",
        "_last_categorical_palette",
        "_last_scale",
        "_nsmap",
        "_tree",
    )

    def __init__(
        self, tree: etree._ElementTree, *, _nsmap: dict[str, str] | None = None
    ):
        """Initialize from a parsed lxml ElementTree.

        Use the ``from_file``, ``from_string``, or ``from_url`` classmethods
        instead of calling this directly. The input tree is copied so later
        changes made by its owner cannot mutate this document.

        Args:
            tree: A parsed lxml ElementTree containing the SVG document.
            _nsmap: Pre-detected namespace mapping (internal use).
        """
        self._initialize(copy.deepcopy(tree), _nsmap=_nsmap)

    def _initialize(
        self, tree: etree._ElementTree, *, _nsmap: dict[str, str] | None = None
    ) -> None:
        """Initialize from a tree whose ownership has been transferred."""
        self._tree = tree
        self._nsmap = dict(_nsmap) if _nsmap is not None else self._detect_namespaces()
        self._last_scale = None
        self._last_categorical_palette = None
        self._id_index = None

    @classmethod
    def _from_owned_tree(
        cls, tree: etree._ElementTree, *, _nsmap: dict[str, str] | None = None
    ) -> Self:
        """Build from a fresh internal tree, honoring custom subclass setup."""
        if cls.__init__ is SVGDocumentBase.__init__ and cls.__new__ is object.__new__:
            instance = cls.__new__(cls)
            instance._initialize(tree, _nsmap=_nsmap)
            return instance

        # Match the historical subclass contract: factory constructors call
        # the subclass initializer with the tree. Its call to super().__init__
        # defensively copies the tree, which is preferable to bypassing custom
        # initialization merely to save a copy on this uncommon path.
        return cls(tree)

    @classmethod
    def from_file(cls, path: str | PathLike) -> Self:
        """Load from a local SVG file.

        Args:
            path: Path to the local SVG file.

        Returns:
            A new SVGDocument instance parsed from the file.

        Raises:
            FileNotFoundError: If the file does not exist.
            SVGParseError: If the SVG markup is invalid.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"SVG file not found: {path}")
        try:
            tree = etree.parse(str(path), get_secure_parser())
        except etree.XMLSyntaxError as exc:
            raise SVGParseError(f"Failed to parse SVG: {exc}") from exc
        return cls._from_owned_tree(tree)

    @classmethod
    def from_string(cls, svg: str | bytes) -> Self:
        """Parse raw SVG markup.

        Args:
            svg: The SVG markup as a string or bytes.

        Returns:
            A new SVGDocument instance parsed from the string.

        Raises:
            SVGParseError: If the SVG markup is invalid.
        """
        if isinstance(svg, str):
            svg = svg.encode("utf-8")
        try:
            tree = etree.ElementTree(etree.fromstring(svg, get_secure_parser()))
        except etree.XMLSyntaxError as exc:
            raise SVGParseError(f"Failed to parse SVG: {exc}") from exc
        return cls._from_owned_tree(tree)

    @classmethod
    def from_url(cls, url: str, *, timeout: float = 10.0) -> Self:
        """Fetch and parse a remote SVG.

        Args:
            url: The URL pointing to the SVG file.
            timeout: Request timeout in seconds.

        Returns:
            A new SVGDocument instance parsed from the response.
        """
        if not url.startswith(("http://", "https://")):
            raise ValidationError("Only http and https URLs are supported")
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = resp.read()
        return cls.from_string(data)

    @classmethod
    def from_tree(cls, tree: etree._ElementTree, *, copy: bool = True) -> Self:
        """Build a document from an lxml element tree.

        Args:
            tree: Parsed SVG element tree.
            copy: Copy the input tree when true (the default). When false,
                ownership is transferred to the document and the caller must
                not mutate the tree afterward.

        Returns:
            A new immutable document.
        """
        if not isinstance(copy, bool):
            raise ValidationError("copy must be a boolean")
        return cls(tree) if copy else cls._from_owned_tree(tree)

    @property
    def root(self) -> etree._Element:
        """An independent snapshot of the root ``<svg>`` element.

        The returned element can be inspected with the normal lxml APIs, but
        mutating it does not change this immutable document. Use the document's
        transformation methods to create a modified copy.
        """
        return self.root_copy()

    def root_copy(self) -> etree._Element:
        """Return an independent copy of the root ``<svg>`` element.

        This is the explicit form of :attr:`root`. Mutating the returned lxml
        element never changes the document.
        """
        return copy.deepcopy(self._root)

    def xpath(
        self,
        expression: str,
        *,
        namespaces: Mapping[str, str] | None = None,
        **variables: object,
    ) -> Any:
        """Evaluate XPath without exposing mutable elements from the document.

        Element results are copied individually; scalar XPath results are
        returned unchanged. This is cheaper than copying the entire root when
        only a subset of the document is needed.
        """
        result = self._tree.xpath(
            expression,
            namespaces=dict(namespaces) if namespaces is not None else None,
            **variables,
        )
        return _snapshot_xpath_result(result)

    @property
    def _root(self) -> etree._Element:
        """The live root element for trusted internal operations."""
        return self._tree.getroot()

    @property
    def path_ids(self) -> list[str]:
        """All ``<path>`` element IDs in the document."""
        return self._ids_for_tag("path")

    @property
    def group_ids(self) -> list[str]:
        """All ``<g>`` element IDs in the document."""
        return self._ids_for_tag("g")

    @property
    def element_ids(self) -> list[str]:
        """All element IDs in the document."""
        return list(self._element_index.keys())

    @property
    def viewbox(self) -> ViewBox | None:
        """The parsed viewBox, or None if not set."""
        vb = self._root.get("viewBox")
        if vb:
            return parse_viewbox(vb)
        return None

    @property
    def dimensions(self) -> tuple[float | None, float | None]:
        """(width, height) in pixels, or (None, None) if not set."""
        w = _parse_dimension(self._root.get("width"))
        h = _parse_dimension(self._root.get("height"))
        return (w, h)

    @property
    def namespaces(self) -> dict[str, str]:
        """Dict of xmlns prefix -> URI found in the document."""
        return dict(self._nsmap)

    @property
    def metadata(self) -> dict[str, str | None]:
        """Title and description from the SVG, if present."""
        ns = self._svg_ns_prefix()
        title_elem = (
            self._root.find(f"{ns}title", self._nsmap)
            if ns
            else self._root.find("title")
        )
        desc_elem = (
            self._root.find(f"{ns}desc", self._nsmap) if ns else self._root.find("desc")
        )
        return {
            "title": title_elem.text if title_elem is not None else None,
            "desc": desc_elem.text if desc_elem is not None else None,
        }

    @property
    def _element_index(self) -> dict[str, etree._Element]:
        """Lazy-build index of id -> element for O(1) lookup.

        Note: this cache is NOT invalidated when the tree is mutated.
        All public mutation methods use _clone() which resets the cache.
        Do not call _find_by_id after directly mutating _tree.
        """
        if self._id_index is None:
            self._id_index = build_id_index(self._tree)
        return self._id_index

    def _find_by_id(self, eid: str) -> etree._Element | None:
        """Find an element by its id attribute using O(1) index lookup."""
        return self._element_index.get(eid)

    def _build_index(self, key_attr: str) -> dict[str, etree._Element]:
        """Return an element index for the given attribute.

        Uses the cached ID index when *key_attr* is ``"id"``.
        """
        if key_attr == "id":
            return self._element_index
        return build_attr_index(self._tree, key_attr)

    def _resolve_key_attr(
        self, data: Mapping[str, _ValueT], key_attr: str
    ) -> tuple[dict[str, _ValueT], dict[str, etree._Element]]:
        """Expand *data* and build an element index for the given attribute.

        For ``key_attr="id"`` this is a no-op: returns (*data*, id-index).

        For non-ID attributes the same value may appear on many elements.
        This method creates a synthetic unique key per matching element so
        that every element is addressed individually in the returned dicts.
        Unmatched elements are also included in the index (for color_missing).
        """
        if key_attr == "id":
            return dict(data), self._element_index

        multi: dict[str, list[etree._Element]] = {}
        for elem in self._tree.iter():
            val = elem.get(key_attr)
            if val:
                multi.setdefault(val, []).append(elem)

        expanded_data: dict[str, _ValueT] = {}
        expanded_index: dict[str, etree._Element] = {}
        matched_keys: set[str] = set()
        for attr_val, elems in multi.items():
            for i, elem in enumerate(elems):
                synth = f"{attr_val}__pathy_{i}"
                expanded_index[synth] = elem
                if attr_val in data:
                    expanded_data[synth] = data[attr_val]
                    matched_keys.add(attr_val)

        # Preserve unmatched data keys so callers still see non-empty data
        # (needed for scale fitting and color_missing pass).
        for key, value in data.items():
            if key not in matched_keys:
                expanded_data[f"{key}__pathy_unmatched"] = value

        return expanded_data, expanded_index

    def _find_all_by_tag(self, local_tag: str) -> list[etree._Element]:
        """Find all elements with a given local tag name (ignoring namespace)."""
        return self._tree.xpath(f"//*[local-name()='{local_tag}']")

    def _ids_for_tag(self, local_tag: str) -> list[str]:
        """Get all IDs for elements with a given tag name."""
        return [
            eid for elem in self._find_all_by_tag(local_tag) if (eid := elem.get("id"))
        ]

    def bbox(self, element_id: str) -> BBox:
        """Get the bounding box of an element by ID."""
        elem = self._find_by_id(element_id)
        if elem is None:
            raise PathNotFoundError(
                f"Element '{element_id}' not found",
                details={"id": element_id, "available": self.element_ids},
            )
        box = bbox_of_element(elem, self._nsmap)
        if box is None:
            raise PathNotFoundError(
                f"Cannot compute bounding box for '{element_id}'",
                details={"id": element_id},
            )
        return box

    def centroid(self, element_id: str) -> tuple[float, float]:
        """Get the centroid of an element by ID."""
        return centroid_of_bbox(self.bbox(element_id))

    def inspect_paths(self) -> list[PathInfo]:
        """Return detailed info about all colorable elements."""
        from pathy_svg.inspect import inspect_paths

        return inspect_paths(self._tree, self._nsmap)

    def validate_ids(self, ids: Iterable[str]) -> ValidationResult:
        """Check which data IDs match elements in the SVG."""
        from pathy_svg.inspect import validate_ids

        return validate_ids(self._tree, ids)

    def _clone(self) -> Self:
        """Return an independent copy of this document."""
        return self._with_owned_tree(
            copy.deepcopy(self._tree),
            _nsmap=self._nsmap,
        )

    def _with_owned_tree(
        self, tree: etree._ElementTree, *, _nsmap: dict[str, str] | None = None
    ) -> Self:
        """Deep-copy instance state while adopting a fresh internal tree.

        Custom subclass state must support Python's ``copy.deepcopy`` protocol.
        The SVG tree and ID cache are supplied through the copy memo so lxml is
        not copied a second time and cached elements cannot survive the clone.
        """
        new_nsmap = (
            dict(_nsmap)
            if _nsmap is not None
            else _detect_namespace_map(tree.getroot())
        )
        memo: dict[int, object] = {
            id(self._tree): tree,
            id(self._nsmap): new_nsmap,
        }
        if self._id_index is not None:
            memo[id(self._id_index)] = None

        new = copy.deepcopy(self, memo)
        new._tree = tree
        new._nsmap = new_nsmap
        new._id_index = None
        return new

    def _detect_namespaces(self) -> dict[str, str]:
        """Detect all XML namespaces from the root element."""
        return _detect_namespace_map(self._root)

    def _svg_ns_prefix(self) -> str:
        """Return the XPath prefix for the SVG namespace, e.g. 'svg:'."""
        for prefix, uri in self._nsmap.items():
            if uri == SVG_NS:
                return f"{prefix}:"
        return ""


def _parse_dimension(val: str | None) -> float | None:
    """Parse a dimension like '500', '500px', '50%' into a float (ignoring units)."""
    if val is None:
        return None
    match = re.match(r"([+-]?\d*\.?\d+(?:[eE][+-]?\d+)?)", val.strip())
    return float(match.group(1)) if match else None


def _detect_namespace_map(root: etree._Element) -> dict[str, str]:
    """Detect namespaces from an SVG root element."""
    if not root.nsmap:
        return {"svg": SVG_NS}
    nsmap = {
        ("svg" if prefix is None else prefix): uri for prefix, uri in root.nsmap.items()
    }
    if "svg" not in nsmap and SVG_NS not in nsmap.values():
        nsmap["svg"] = SVG_NS
    return nsmap


def _snapshot_xpath_result(result: Any) -> Any:
    """Copy element-valued XPath results while retaining scalar results."""
    if isinstance(result, etree._Element):
        return copy.deepcopy(result)
    if isinstance(result, etree._ElementUnicodeResult):
        return str(result)
    if isinstance(result, list):
        return [_snapshot_xpath_result(item) for item in result]
    if isinstance(result, tuple):
        return tuple(_snapshot_xpath_result(item) for item in result)
    return result
