"""SVGDocumentBase — core loading, querying, and cloning logic."""

from __future__ import annotations

import copy
import re
import urllib.request
import urllib.parse
import socket
import ipaddress
from pathlib import Path
from typing import TYPE_CHECKING

from lxml import etree

from pathy_svg._constants import SVG_NS, build_attr_index, build_id_index, get_secure_parser
from pathy_svg.exceptions import PathNotFoundError, SVGParseError
from pathy_svg.transform import (
    BBox,
    ViewBox,
    bbox_of_element,
    centroid_of_bbox,
    parse_viewbox,
)

if TYPE_CHECKING:
    from os import PathLike


class SVGDocumentBase:
    """Core document functionality: loading, properties, querying, and cloning.

    Subclasses (via mixins) add coloring, overlay, export, and serialization.
    """

    __slots__ = (
        "_tree",
        "_nsmap",
        "_last_scale",
        "_last_categorical_palette",
        "_id_index",
    )

    def __init__(
        self, tree: etree._ElementTree, *, _nsmap: dict[str, str] | None = None
    ):
        """Initialize from a parsed lxml ElementTree.

        Use the ``from_file``, ``from_string``, or ``from_url`` classmethods
        instead of calling this directly.

        Args:
            tree: A parsed lxml ElementTree containing the SVG document.
            _nsmap: Pre-detected namespace mapping (internal use).
        """
        self._tree = tree
        self._nsmap = _nsmap if _nsmap is not None else self._detect_namespaces()
        self._last_scale = None
        self._last_categorical_palette = None
        self._id_index = None

    @classmethod
    def from_file(cls, path: str | PathLike):
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
        return cls(tree)

    @classmethod
    def from_string(cls, svg: str | bytes):
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
        return cls(tree)

    @classmethod
    def from_url(cls, url: str, *, timeout: float = 10.0):
        """Fetch and parse a remote SVG.

        Args:
            url: The URL pointing to the SVG file.
            timeout: Request timeout in seconds.

        Returns:
            A new SVGDocument instance parsed from the response.
        """
        if not url.startswith(("http://", "https://")):
            raise ValueError("Only http and https URLs are supported")

        # Custom HTTPAdapter/Opener to prevent SSRF and DNS rebinding
        # By resolving the IP first and forcing urllib to connect to the IP
        # while keeping the original Host header.
        parsed = urllib.parse.urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Invalid URL hostname")

        try:
            # getaddrinfo handles both IPv4 and IPv6
            addr_info = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == 'https' else 80), proto=socket.IPPROTO_TCP)
        except socket.gaierror:
            raise ValueError(f"Could not resolve hostname: {hostname}")

        if not addr_info:
            raise ValueError(f"Could not resolve hostname: {hostname}")

        ip = addr_info[0][4][0]

        ip_obj = ipaddress.ip_address(ip)
        if not ip_obj.is_global:
            raise ValueError(f"URL points to a non-global IP address ({ip}), which is not allowed.")

        # Reconstruct the URL using the verified IP to prevent DNS rebinding
        # But we need to keep the original host header for virtual hosting and TLS SNI
        req = urllib.request.Request(url)

        # A safer and simpler way to prevent SSRF in urllib without rewriting the opener (which breaks SNI for HTTPS)
        # is to check if the hostname is an IP literal. If not, the best way in urllib is tricky.
        # Alternatively, since DNS rebinding is an advanced attack and requires a short TTL,
        # a safer solution is to raise an error if they don't provide a direct safe IP, or rely on
        # requests library if we could use it.
        # Since urllib.request is hard to patch for DNS rebinding securely without breaking HTTPS SNI,
        # we will use the safest approach: validating the IP, and if the user wants to avoid DNS rebinding,
        # we create a custom opener that patches socket.create_connection.

        class SafeOpener(urllib.request.HTTPHandler, urllib.request.HTTPSHandler):
            pass # Creating a custom socket.create_connection patch is too complex here

        # We will use a context manager to temporarily monkey-patch socket.create_connection
        # to force it to use our pre-resolved IP, preventing DNS rebinding.
        original_create_connection = socket.create_connection

        def safe_create_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None, *args, **kwargs):
            host, port = address
            if host == hostname:
                address = (ip, port)
            return original_create_connection(address, timeout, source_address, *args, **kwargs)

        socket.create_connection = safe_create_connection
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
        finally:
            socket.create_connection = original_create_connection

        return cls.from_string(data)

    @classmethod
    def from_dataframe(
        cls,
        path: str | PathLike,
        df,
        *,
        id_col: str,
        value_col: str,
    ):
        """Load an SVG and extract data from a Pandas DataFrame.

        Args:
            path: Path to the local SVG file.
            df: A Pandas DataFrame containing the data.
            id_col: Column name for element IDs.
            value_col: Column name for numeric values.

        Returns:
            A tuple of (SVGDocument, data_dict) where data_dict maps IDs to values.

        Raises:
            FileNotFoundError: If the SVG file does not exist.
            SVGParseError: If the SVG markup is invalid.
            ValueError: If required columns are missing from the DataFrame.
        """
        from pathy_svg.data import dataframe_to_dict

        doc = cls.from_file(path)
        data = dataframe_to_dict(df, id_col, value_col)
        return doc, data

    @property
    def root(self) -> etree._Element:
        """The root <svg> element."""
        return self._tree.getroot()

    @property
    def path_ids(self) -> list[str]:
        """All <path> element IDs in the document."""
        return self._ids_for_tag("path")

    @property
    def group_ids(self) -> list[str]:
        """All <g> element IDs in the document."""
        return self._ids_for_tag("g")

    @property
    def element_ids(self) -> list[str]:
        """All element IDs in the document."""
        return list(self._element_index.keys())

    @property
    def viewbox(self) -> ViewBox | None:
        """The parsed viewBox, or None if not set."""
        vb = self.root.get("viewBox")
        if vb:
            return parse_viewbox(vb)
        return None

    @property
    def dimensions(self) -> tuple[float | None, float | None]:
        """(width, height) in pixels, or (None, None) if not set."""
        w = _parse_dimension(self.root.get("width"))
        h = _parse_dimension(self.root.get("height"))
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
            self.root.find(f"{ns}title", self._nsmap) if ns else self.root.find("title")
        )
        desc_elem = (
            self.root.find(f"{ns}desc", self._nsmap) if ns else self.root.find("desc")
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
        self, data: dict, key_attr: str
    ) -> tuple[dict, dict[str, etree._Element]]:
        """Expand *data* and build an element index for the given attribute.

        For ``key_attr="id"`` this is a no-op: returns (*data*, id-index).

        For non-ID attributes the same value may appear on many elements.
        This method creates a synthetic unique key per matching element so
        that every element is addressed individually in the returned dicts.
        Unmatched elements are also included in the index (for color_missing).
        """
        if key_attr == "id":
            return data, self._element_index

        multi: dict[str, list[etree._Element]] = {}
        for elem in self._tree.iter():
            val = elem.get(key_attr)
            if val:
                multi.setdefault(val, []).append(elem)

        expanded_data: dict = {}
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
        for key in data:
            if key not in matched_keys:
                expanded_data[f"{key}__pathy_unmatched"] = data[key]

        return expanded_data, expanded_index

    def _find_all_by_tag(self, local_tag: str) -> list[etree._Element]:
        """Find all elements with a given local tag name (ignoring namespace)."""
        return self._tree.xpath(f"//*[local-name()='{local_tag}']")

    def _ids_for_tag(self, local_tag: str) -> list[str]:
        """Get all IDs for elements with a given tag name."""
        return [eid for elem in self._find_all_by_tag(local_tag) if (eid := elem.get("id"))]

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

    def inspect_paths(self):
        """Return detailed info about all colorable elements."""
        from pathy_svg.inspect import inspect_paths

        return inspect_paths(self._tree, self._nsmap)

    def validate_ids(self, ids):
        """Check which data IDs match elements in the SVG."""
        from pathy_svg.inspect import validate_ids

        return validate_ids(self._tree, ids)

    def _clone(self):
        """Return a deep copy of this document."""
        new = type(self)(
            copy.deepcopy(self._tree),
            _nsmap=dict(self._nsmap),
        )
        new._last_scale = self._last_scale
        new._last_categorical_palette = self._last_categorical_palette
        return new

    def _detect_namespaces(self) -> dict[str, str]:
        """Detect all XML namespaces from the root element."""
        root = self._tree.getroot()
        if not root.nsmap:
            return {"svg": SVG_NS}
        nsmap = {
            ("svg" if prefix is None else prefix): uri
            for prefix, uri in root.nsmap.items()
        }
        if "svg" not in nsmap and SVG_NS not in nsmap.values():
            nsmap["svg"] = SVG_NS
        return nsmap

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
    match = re.match(r"([+-]?\d*\.?\d+)", val.strip())
    return float(match.group(1)) if match else None
