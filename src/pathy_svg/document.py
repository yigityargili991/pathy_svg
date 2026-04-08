"""SVGDocument — the central object for loading, querying, and transforming SVGs."""

from __future__ import annotations

import copy
import re
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING

from lxml import etree

from pathy_svg.exceptions import PathNotFoundError, SVGParseError
from pathy_svg.transform import BBox, ViewBox, bbox_of_element, centroid_of_bbox, parse_viewbox

if TYPE_CHECKING:
    from os import PathLike

SVG_NS = "http://www.w3.org/2000/svg"


class SVGDocument:
    """Immutable wrapper around a parsed SVG document.

    Every mutation method returns a new SVGDocument — the original is never modified.
    Supports method chaining: ``doc.heatmap(...).legend(...).save(...)``.
    """

    __slots__ = ("_tree", "_nsmap", "_last_scale", "_last_heatmap_config", "_last_categorical_palette", "_id_index")

    def __init__(self, tree: etree._ElementTree, *, _nsmap: dict[str, str] | None = None):
        self._tree = tree
        self._nsmap = _nsmap if _nsmap is not None else self._detect_namespaces()
        self._id_index = None

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_file(cls, path: str | PathLike) -> SVGDocument:
        """Load from a local SVG file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"SVG file not found: {path}")
        try:
            tree = etree.parse(str(path))
        except etree.XMLSyntaxError as exc:
            raise SVGParseError(f"Failed to parse SVG: {exc}") from exc
        return cls(tree)

    @classmethod
    def from_string(cls, svg: str | bytes) -> SVGDocument:
        """Parse raw SVG markup."""
        if isinstance(svg, str):
            svg = svg.encode("utf-8")
        try:
            tree = etree.ElementTree(etree.fromstring(svg))
        except etree.XMLSyntaxError as exc:
            raise SVGParseError(f"Failed to parse SVG: {exc}") from exc
        return cls(tree)

    @classmethod
    def from_url(cls, url: str, *, timeout: float = 10.0) -> SVGDocument:
        """Fetch and parse a remote SVG."""
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        return cls.from_string(data)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

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
        ids = []
        for elem in self._tree.iter():
            eid = elem.get("id")
            if eid:
                ids.append(eid)
        return ids

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
        w = self._parse_dimension(self.root.get("width"))
        h = self._parse_dimension(self.root.get("height"))
        return (w, h)

    @property
    def namespaces(self) -> dict[str, str]:
        """Dict of xmlns prefix -> URI found in the document."""
        return dict(self._nsmap)

    @property
    def metadata(self) -> dict[str, str | None]:
        """Title and description from the SVG, if present."""
        ns = self._svg_ns_prefix()
        title_elem = self.root.find(f"{ns}title", self._nsmap) if ns else self.root.find("title")
        desc_elem = self.root.find(f"{ns}desc", self._nsmap) if ns else self.root.find("desc")
        return {
            "title": title_elem.text if title_elem is not None else None,
            "desc": desc_elem.text if desc_elem is not None else None,
        }

    # ------------------------------------------------------------------
    # Element lookup
    # ------------------------------------------------------------------

    @property
    def _element_index(self) -> dict[str, etree._Element]:
        """Lazy-build index of id -> element for O(1) lookup.

        Note: this cache is NOT invalidated when the tree is mutated.
        All public mutation methods use _clone() which resets the cache.
        Do not call _find_by_id after directly mutating _tree.
        """
        if self._id_index is None:
            self._id_index = {}
            for elem in self._tree.iter():
                eid = elem.get("id")
                if eid:
                    self._id_index.setdefault(eid, elem)
        return self._id_index

    def _find_by_id(self, eid: str) -> etree._Element | None:
        """Find an element by its id attribute using O(1) index lookup."""
        return self._element_index.get(eid)

    def _find_all_by_tag(self, local_tag: str) -> list[etree._Element]:
        """Find all elements with a given local tag name (ignoring namespace)."""
        return self._tree.xpath(
            f"//*[local-name()='{local_tag}']"
        )

    def _ids_for_tag(self, local_tag: str) -> list[str]:
        """Get all IDs for elements with a given tag name."""
        ids = []
        for elem in self._find_all_by_tag(local_tag):
            eid = elem.get("id")
            if eid:
                ids.append(eid)
        return ids

    # ------------------------------------------------------------------
    # Geometric queries
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

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

    def save(self, path: str | PathLike, *, pretty_print: bool = True, xml_declaration: bool = True) -> None:
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

    # ------------------------------------------------------------------
    # Jupyter integration
    # ------------------------------------------------------------------

    def _repr_svg_(self) -> str:
        """Render inline in Jupyter notebooks."""
        return self.to_string()

    def _repr_html_(self) -> str:
        """HTML fallback for Jupyter."""
        return self.to_string()

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def inspect_paths(self):
        """Return detailed info about all colorable elements."""
        from pathy_svg.inspect import inspect_paths

        return inspect_paths(self._tree, self._nsmap)

    def validate_ids(self, ids):
        """Check which data IDs match elements in the SVG."""
        from pathy_svg.inspect import validate_ids

        return validate_ids(self._tree, self._nsmap, ids)

    def xy_guide(self, *, color: str = "red", step: float = 50) -> SVGDocument:
        """Return a copy with a coordinate grid overlay for orientation."""
        clone = self._clone()
        vb = clone.viewbox
        if vb is None:
            return clone

        root = clone.root
        ns = root.nsmap.get(None, SVG_NS)
        g = etree.SubElement(root, f"{{{ns}}}g" if ns else "g", id="pathy-guide")
        g.set("style", f"stroke:{color};stroke-width:0.5;fill:none;opacity:0.5")

        x = vb.x
        while x <= vb.x + vb.width:
            line = etree.SubElement(g, f"{{{ns}}}line" if ns else "line")
            line.set("x1", str(x))
            line.set("y1", str(vb.y))
            line.set("x2", str(x))
            line.set("y2", str(vb.y + vb.height))
            # Label
            txt = etree.SubElement(g, f"{{{ns}}}text" if ns else "text")
            txt.set("x", str(x + 2))
            txt.set("y", str(vb.y + 12))
            txt.set("style", f"fill:{color};font-size:8px;stroke:none")
            txt.text = str(int(x))
            x += step

        y = vb.y
        while y <= vb.y + vb.height:
            line = etree.SubElement(g, f"{{{ns}}}line" if ns else "line")
            line.set("x1", str(vb.x))
            line.set("y1", str(y))
            line.set("x2", str(vb.x + vb.width))
            line.set("y2", str(y))
            txt = etree.SubElement(g, f"{{{ns}}}text" if ns else "text")
            txt.set("x", str(vb.x + 2))
            txt.set("y", str(y - 2))
            txt.set("style", f"fill:{color};font-size:8px;stroke:none")
            txt.text = str(int(y))
            y += step

        return clone

    # ------------------------------------------------------------------
    # Coloring
    # ------------------------------------------------------------------

    def heatmap(
        self,
        data: dict[str, float],
        *,
        palette: str | list[str] = "RdYlBu_r",
        vmin: float | None = None,
        vmax: float | None = None,
        vcenter: float | None = None,
        na_color: str = "#cccccc",
        breaks: list[float] | None = None,
        opacity: float | None = None,
        preserve_stroke: bool = True,
        color_missing: bool = True,
        clip: bool = True,
    ) -> SVGDocument:
        """Apply data-driven coloring to paths. Returns a new SVGDocument."""
        from pathy_svg.coloring import apply_heatmap

        clone = self._clone()
        scale = apply_heatmap(
            clone._tree,
            data,
            palette=palette,
            vmin=vmin,
            vmax=vmax,
            vcenter=vcenter,
            na_color=na_color,
            breaks=breaks,
            opacity=opacity,
            preserve_stroke=preserve_stroke,
            color_missing=color_missing,
            clip=clip,
        )
        clone._last_scale = scale
        clone._last_heatmap_config = {
            "palette": palette, "vmin": vmin, "vmax": vmax,
            "vcenter": vcenter, "breaks": breaks,
        }
        return clone

    def recolor(
        self,
        colors: dict[str, str],
        *,
        opacity: float | None = None,
        preserve_stroke: bool = True,
    ) -> SVGDocument:
        """Apply manual color mapping to paths. Returns a new SVGDocument."""
        from pathy_svg.coloring import apply_recolor

        clone = self._clone()
        apply_recolor(
            clone._tree, colors, opacity=opacity, preserve_stroke=preserve_stroke
        )
        return clone

    def recolor_by_category(
        self,
        data: dict[str, str],
        *,
        palette: dict[str, str] | str = "tab10",
        na_color: str = "#cccccc",
        opacity: float | None = None,
        preserve_stroke: bool = True,
    ) -> SVGDocument:
        """Apply categorical coloring to paths. Returns a new SVGDocument."""
        from pathy_svg.coloring import apply_categorical

        clone = self._clone()
        cat_palette = apply_categorical(
            clone._tree, data, palette=palette, na_color=na_color,
            opacity=opacity, preserve_stroke=preserve_stroke,
        )
        clone._last_categorical_palette = cat_palette
        return clone

    # ------------------------------------------------------------------
    # Legend
    # ------------------------------------------------------------------

    def legend(
        self,
        *,
        kind: str = "auto",
        position: tuple[float, float] = (0.85, 0.1),
        size: tuple[float, float] = (0.04, 0.4),
        direction: str = "vertical",
        num_ticks: int = 5,
        tick_format: str = "{:.2f}",
        labels: list[str] | None = None,
        font_size: float | None = None,
        font_color: str = "black",
        font_family: str = "sans-serif",
        title: str | None = None,
        title_size: float | None = None,
        border: bool = False,
        border_color: str = "#333",
        background: str | None = None,
        padding: float = 5,
    ) -> SVGDocument:
        """Add a legend to the SVG. Returns a new SVGDocument."""
        from pathy_svg.legend import build_discrete_legend, build_gradient_legend

        clone = self._clone()
        vb = clone.viewbox
        if vb is None:
            from pathy_svg.transform import ViewBox
            vb = ViewBox(0, 0, 500, 500)

        scale = getattr(self, "_last_scale", None)
        cat_pal = getattr(self, "_last_categorical_palette", None)

        if kind == "auto":
            if cat_pal is not None:
                kind = "categorical"
            elif scale is not None and scale.breaks is not None:
                kind = "discrete"
            else:
                kind = "gradient"

        if kind == "gradient" and scale is not None:
            legend_elem = build_gradient_legend(
                scale, vb,
                position=position, size=size, direction=direction,
                num_ticks=num_ticks, tick_format=tick_format, labels=labels,
                font_size=font_size, font_color=font_color, font_family=font_family,
                title=title, title_size=title_size,
                border=border, border_color=border_color,
                background=background, padding=padding,
            )
        elif kind in ("discrete", "categorical") and cat_pal is not None:
            colors = list(cat_pal.mapping.values())
            cat_labels = labels or list(cat_pal.mapping.keys())
            legend_elem = build_discrete_legend(
                colors, cat_labels, vb,
                position=position, size=size, direction=direction,
                font_size=font_size, font_color=font_color, font_family=font_family,
                title=title, title_size=title_size,
                border=border, border_color=border_color,
            )
        elif kind == "gradient":
            # Fallback: create a default scale
            from pathy_svg.themes import ColorScale
            fallback_scale = ColorScale("viridis", vmin=0, vmax=1)
            legend_elem = build_gradient_legend(
                fallback_scale, vb,
                position=position, size=size, direction=direction,
                num_ticks=num_ticks, tick_format=tick_format, labels=labels,
                font_size=font_size, font_color=font_color, font_family=font_family,
                title=title, title_size=title_size,
                border=border, border_color=border_color,
                background=background, padding=padding,
            )
        else:
            # Discrete with scale breaks
            if scale is not None and scale.breaks is not None:
                breaks = scale.breaks
                colors = [scale((breaks[i] + breaks[i + 1]) / 2) for i in range(len(breaks) - 1)]
                bin_labels = labels or [
                    f"{tick_format.format(breaks[i])} – {tick_format.format(breaks[i+1])}"
                    for i in range(len(breaks) - 1)
                ]
                legend_elem = build_discrete_legend(
                    colors, bin_labels, vb,
                    position=position, size=size, direction=direction,
                    font_size=font_size, font_color=font_color, font_family=font_family,
                    title=title, title_size=title_size,
                    border=border, border_color=border_color,
                )
            else:
                from pathy_svg.themes import ColorScale
                fallback_scale = ColorScale("viridis", vmin=0, vmax=1)
                legend_elem = build_gradient_legend(
                    fallback_scale, vb,
                    position=position, size=size, direction=direction,
                    num_ticks=num_ticks, tick_format=tick_format, labels=labels,
                    font_size=font_size, font_color=font_color, font_family=font_family,
                    title=title, title_size=title_size,
                    border=border, border_color=border_color,
                    background=background, padding=padding,
                )

        clone.root.append(legend_elem)
        return clone

    # ------------------------------------------------------------------
    # Diff / Comparison
    # ------------------------------------------------------------------

    def diff(
        self,
        baseline: dict[str, float],
        treatment: dict[str, float],
        *,
        mode: str = "delta",
        palette: str | list[str] = "coolwarm",
        vcenter: float | None = 0,
        vmin: float | None = None,
        vmax: float | None = None,
        **heatmap_kwargs,
    ) -> SVGDocument:
        """Compute per-path differences and apply as a heatmap. Returns a new SVGDocument."""
        from pathy_svg.diff import compute_diff

        diff_data = compute_diff(baseline, treatment, mode=mode)
        return self.heatmap(
            diff_data, palette=palette, vcenter=vcenter, vmin=vmin, vmax=vmax,
            **heatmap_kwargs,
        )

    def compare(
        self,
        datasets: dict[str, dict[str, float]],
        *,
        palette: str | list[str] = "YlOrRd",
        layout: str = "horizontal",
        spacing: float = 20,
        **heatmap_kwargs,
    ) -> SVGDocument:
        """Create side-by-side comparison of multiple datasets. Returns a new SVGDocument."""
        from pathy_svg.diff import compose_side_by_side

        colored_docs = []
        titles = []
        for name, data in datasets.items():
            titles.append(name)
            colored_docs.append(self.heatmap(data, palette=palette, **heatmap_kwargs))

        new_tree = compose_side_by_side(
            colored_docs, titles=titles, layout=layout, spacing=spacing,
        )
        return SVGDocument(new_tree)

    # ------------------------------------------------------------------
    # Animation
    # ------------------------------------------------------------------

    def animate(
        self,
        *,
        effect: str = "pulse",
        duration: float = 2.0,
        delay_by: str = "value",
        loop: bool = True,
    ) -> SVGDocument:
        """Inject CSS animation into the SVG. Returns a new SVGDocument."""
        from pathy_svg.animation import inject_animation

        clone = self._clone()
        data_order = None
        if delay_by == "value" and hasattr(self, "_last_scale"):
            # Try to get ordered IDs from last heatmap
            data_order = None  # Would need stored data; use default for now
        inject_animation(
            clone._tree, clone._nsmap,
            effect=effect, duration=duration, delay_by=delay_by,
            loop=loop, data_order=data_order,
        )
        return clone

    # ------------------------------------------------------------------
    # Annotations
    # ------------------------------------------------------------------

    def annotate(
        self,
        labels: dict[str, str],
        *,
        placement: str = "centroid",
        font_size: float = 12,
        font_color: str = "black",
        font_family: str = "sans-serif",
        background: str | None = None,
        offset: tuple[float, float] = (0, 0),
    ) -> SVGDocument:
        """Add text labels to paths. Returns a new SVGDocument."""
        from pathy_svg.annotations import add_text_labels

        clone = self._clone()
        add_text_labels(
            clone._tree, clone._nsmap, labels,
            placement=placement, font_size=font_size, font_color=font_color,
            font_family=font_family, background=background, offset=offset,
        )
        return clone

    def add_tooltips(
        self,
        tips: dict[str, str],
        *,
        method: str = "title",
    ) -> SVGDocument:
        """Add tooltips to paths. Returns a new SVGDocument."""
        from pathy_svg.annotations import add_tooltips

        clone = self._clone()
        add_tooltips(clone._tree, clone._nsmap, tips, method=method)
        return clone

    def replace_text(
        self,
        replacements: dict[str, str],
        *,
        text_color: str | None = None,
    ) -> SVGDocument:
        """Replace text content in <text> elements. Returns a new SVGDocument."""
        from pathy_svg.annotations import replace_text

        clone = self._clone()
        replace_text(clone._tree, clone._nsmap, replacements, text_color=text_color)
        return clone

    # ------------------------------------------------------------------
    # Export (raster)
    # ------------------------------------------------------------------

    def to_png(self, path=None, **kwargs) -> bytes | None:
        """Export to PNG. Requires pathy-svg[export]."""
        from pathy_svg.export import to_png
        return to_png(self, path, **kwargs)

    def to_pdf(self, path=None) -> bytes | None:
        """Export to PDF. Requires pathy-svg[export]."""
        from pathy_svg.export import to_pdf
        return to_pdf(self, path)

    def to_jpeg(self, path=None, **kwargs) -> bytes | None:
        """Export to JPEG. Requires pathy-svg[export]."""
        from pathy_svg.export import to_jpeg
        return to_jpeg(self, path, **kwargs)

    def thumbnail(self, **kwargs):
        """Return a PIL Image thumbnail. Requires pathy-svg[export]."""
        from pathy_svg.export import thumbnail
        return thumbnail(self, **kwargs)

    def show(self, **kwargs):
        """Display in Jupyter. Requires pathy-svg[full]."""
        from pathy_svg.export import show
        show(self, **kwargs)

    # ------------------------------------------------------------------
    # Cloning (immutability)
    # ------------------------------------------------------------------

    def _clone(self) -> SVGDocument:
        """Return a deep copy of this document."""
        return SVGDocument(
            copy.deepcopy(self._tree),
            _nsmap=dict(self._nsmap),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _detect_namespaces(self) -> dict[str, str]:
        """Detect all XML namespaces from the root element."""
        root = self._tree.getroot()
        nsmap = {}
        if root.nsmap:
            for prefix, uri in root.nsmap.items():
                if prefix is None:
                    nsmap["svg"] = uri
                else:
                    nsmap[prefix] = uri
        # Ensure SVG namespace is always available
        if "svg" not in nsmap and SVG_NS not in nsmap.values():
            nsmap["svg"] = SVG_NS
        return nsmap

    def _svg_ns_prefix(self) -> str:
        """Return the XPath prefix for the SVG namespace, e.g. 'svg:'."""
        for prefix, uri in self._nsmap.items():
            if uri == SVG_NS:
                return f"{prefix}:"
        return ""

    @staticmethod
    def _parse_dimension(val: str | None) -> float | None:
        """Parse a dimension like '500', '500px', '50%' into a float (ignoring units)."""
        if val is None:
            return None
        match = re.match(r"([+-]?\d*\.?\d+)", val.strip())
        if match:
            return float(match.group(1))
        return None
