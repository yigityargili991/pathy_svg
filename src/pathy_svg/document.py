"""SVGDocument — the central object for loading, querying, and transforming SVGs."""

from __future__ import annotations

import copy
import re
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING

from lxml import etree

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

SVG_NS = "http://www.w3.org/2000/svg"


class SVGDocument:
    """Immutable wrapper around a parsed SVG document.

    Every mutation method returns a new SVGDocument — the original is never modified.
    Supports method chaining: ``doc.heatmap(...).legend(...).save(...)``.
    """

    __slots__ = (
        "_tree",
        "_nsmap",
        "_last_scale",
        "_last_heatmap_config",
        "_last_categorical_palette",
        "_id_index",
    )

    def __init__(
        self, tree: etree._ElementTree, *, _nsmap: dict[str, str] | None = None
    ):
        self._tree = tree
        self._nsmap = _nsmap if _nsmap is not None else self._detect_namespaces()
        self._id_index = None


    @classmethod
    def from_file(cls, path: str | PathLike) -> SVGDocument:
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
            tree = etree.parse(str(path))
        except etree.XMLSyntaxError as exc:
            raise SVGParseError(f"Failed to parse SVG: {exc}") from exc
        return cls(tree)

    @classmethod
    def from_string(cls, svg: str | bytes) -> SVGDocument:
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
            tree = etree.ElementTree(etree.fromstring(svg))
        except etree.XMLSyntaxError as exc:
            raise SVGParseError(f"Failed to parse SVG: {exc}") from exc
        return cls(tree)

    @classmethod
    def from_url(cls, url: str, *, timeout: float = 10.0) -> SVGDocument:
        """Fetch and parse a remote SVG.

        Args:
            url: The URL pointing to the SVG file.
            timeout: Request timeout in seconds.

        Returns:
            A new SVGDocument instance parsed from the response.
        """
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        return cls.from_string(data)

    @classmethod
    def from_dataframe(
        cls,
        path: str | PathLike,
        df,
        *,
        id_col: str,
        value_col: str,
    ) -> tuple[SVGDocument, dict[str, float]]:
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
        from pathy_svg.utils import dataframe_to_dict

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
        return self._tree.xpath(f"//*[local-name()='{local_tag}']")

    def _ids_for_tag(self, local_tag: str) -> list[str]:
        """Get all IDs for elements with a given tag name."""
        ids = []
        for elem in self._find_all_by_tag(local_tag):
            eid = elem.get("id")
            if eid:
                ids.append(eid)
        return ids


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
        """Apply data-driven coloring to paths.

        Args:
            data: Data dict mapping path IDs to numeric values.
            palette: Name of a matplotlib colormap or a list of hex colors.
            vmin: Minimum value for the color scale.
            vmax: Maximum value for the color scale.
            vcenter: Center value for diverging color scales.
            na_color: Color to use for missing or NaN values.
            breaks: List of boundary values for discrete color scales.
            opacity: Opacity for the filled paths.
            preserve_stroke: Whether to preserve original stroke styling.
            color_missing: Whether to color paths that are not in the data with `na_color`.
            clip: Whether to clip values outside the `vmin` and `vmax` bounds.

        Returns:
            A new SVGDocument with the heatmap applied.
        """
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
            "palette": palette,
            "vmin": vmin,
            "vmax": vmax,
            "vcenter": vcenter,
            "breaks": breaks,
        }
        return clone

    def heatmap_from_dataframe(
        self,
        df,
        *,
        id_col: str,
        value_col: str,
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
        """Apply data-driven coloring from a Pandas DataFrame.

        Args:
            df: A Pandas DataFrame containing the data.
            id_col: Column name for element IDs.
            value_col: Column name for numeric values.
            palette: Name of a matplotlib colormap or a list of hex colors.
            vmin: Minimum value for the color scale.
            vmax: Maximum value for the color scale.
            vcenter: Center value for diverging color scales.
            na_color: Color to use for missing or NaN values.
            breaks: List of boundary values for discrete color scales.
            opacity: Opacity for the filled paths.
            preserve_stroke: Whether to preserve original stroke styling.
            color_missing: Whether to color paths that are not in the data with `na_color`.
            clip: Whether to clip values outside the `vmin` and `vmax` bounds.

        Returns:
            A new SVGDocument with the heatmap applied.

        Raises:
            ValueError: If required columns are missing from the DataFrame.
        """
        from pathy_svg.utils import dataframe_to_dict

        data = dataframe_to_dict(df, id_col, value_col)
        return self.heatmap(
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

    def recolor(
        self,
        colors: dict[str, str],
        *,
        opacity: float | None = None,
        preserve_stroke: bool = True,
    ) -> SVGDocument:
        """Apply manual color mapping to paths.

        Args:
            colors: A dictionary mapping path IDs to hex color strings.
            opacity: Opacity for the filled paths.
            preserve_stroke: Whether to preserve original stroke styling.

        Returns:
            A new SVGDocument with the updated colors applied.
        """
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
        """Apply categorical coloring to paths.

        Args:
            data: A dictionary mapping path IDs to category labels.
            palette: A dictionary mapping categories to colors, or the name of a matplotlib colormap.
            na_color: Color to use for missing categories.
            opacity: Opacity for the filled paths.
            preserve_stroke: Whether to preserve original stroke styling.

        Returns:
            A new SVGDocument with the categorical coloring applied.
        """
        from pathy_svg.coloring import apply_categorical

        clone = self._clone()
        cat_palette = apply_categorical(
            clone._tree,
            data,
            palette=palette,
            na_color=na_color,
            opacity=opacity,
            preserve_stroke=preserve_stroke,
        )
        clone._last_categorical_palette = cat_palette
        return clone


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
        """Add a legend to the SVG.

        Args:
            kind: Type of legend to add ("auto", "gradient", "discrete", "categorical").
            position: Relative (x, y) coordinates for the legend origin (0-1 range).
            size: Relative (width, height) for the legend bounds (0-1 range).
            direction: Legend orientation ("vertical" or "horizontal").
            num_ticks: Number of ticks for continuous scales.
            tick_format: Formatting string for the tick labels.
            labels: Optional custom list of labels.
            font_size: Font size for labels.
            font_color: Font color for labels.
            font_family: CSS font family.
            title: Title for the legend.
            title_size: Font size for the title.
            border: Whether to draw a border around the legend.
            border_color: Color of the legend border.
            background: Background color of the legend area.
            padding: Padding inside the legend area.

        Returns:
            A new SVGDocument containing the legend element.
        """
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
                scale,
                vb,
                position=position,
                size=size,
                direction=direction,
                num_ticks=num_ticks,
                tick_format=tick_format,
                labels=labels,
                font_size=font_size,
                font_color=font_color,
                font_family=font_family,
                title=title,
                title_size=title_size,
                border=border,
                border_color=border_color,
                background=background,
                padding=padding,
            )
        elif kind in ("discrete", "categorical") and cat_pal is not None:
            colors = list(cat_pal.mapping.values())
            cat_labels = labels or list(cat_pal.mapping.keys())
            legend_elem = build_discrete_legend(
                colors,
                cat_labels,
                vb,
                position=position,
                size=size,
                direction=direction,
                font_size=font_size,
                font_color=font_color,
                font_family=font_family,
                title=title,
                title_size=title_size,
                border=border,
                border_color=border_color,
            )
        elif kind == "gradient":
            # Fallback: create a default scale
            from pathy_svg.themes import ColorScale

            fallback_scale = ColorScale("viridis", vmin=0, vmax=1)
            legend_elem = build_gradient_legend(
                fallback_scale,
                vb,
                position=position,
                size=size,
                direction=direction,
                num_ticks=num_ticks,
                tick_format=tick_format,
                labels=labels,
                font_size=font_size,
                font_color=font_color,
                font_family=font_family,
                title=title,
                title_size=title_size,
                border=border,
                border_color=border_color,
                background=background,
                padding=padding,
            )
        else:
            # Discrete with scale breaks
            if scale is not None and scale.breaks is not None:
                breaks = scale.breaks
                colors = [
                    scale((breaks[i] + breaks[i + 1]) / 2)
                    for i in range(len(breaks) - 1)
                ]
                bin_labels = labels or [
                    f"{tick_format.format(breaks[i])} – {tick_format.format(breaks[i + 1])}"
                    for i in range(len(breaks) - 1)
                ]
                legend_elem = build_discrete_legend(
                    colors,
                    bin_labels,
                    vb,
                    position=position,
                    size=size,
                    direction=direction,
                    font_size=font_size,
                    font_color=font_color,
                    font_family=font_family,
                    title=title,
                    title_size=title_size,
                    border=border,
                    border_color=border_color,
                )
            else:
                from pathy_svg.themes import ColorScale

                fallback_scale = ColorScale("viridis", vmin=0, vmax=1)
                legend_elem = build_gradient_legend(
                    fallback_scale,
                    vb,
                    position=position,
                    size=size,
                    direction=direction,
                    num_ticks=num_ticks,
                    tick_format=tick_format,
                    labels=labels,
                    font_size=font_size,
                    font_color=font_color,
                    font_family=font_family,
                    title=title,
                    title_size=title_size,
                    border=border,
                    border_color=border_color,
                    background=background,
                    padding=padding,
                )

        clone.root.append(legend_elem)
        return clone


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
        """Compute per-path differences and apply as a heatmap.

        Args:
            baseline: Data dict for the baseline state.
            treatment: Data dict for the treatment state.
            mode: The difference mode ("delta", "percent", or "ratio").
            palette: Name of a matplotlib diverging colormap or a list of hex colors.
            vcenter: Center value for the diverging color scale (typically 0).
            vmin: Minimum value for the color scale.
            vmax: Maximum value for the color scale.
            **heatmap_kwargs: Additional arguments passed to `heatmap`.

        Returns:
            A new SVGDocument with the diff heatmap applied.
        """
        from pathy_svg.diff import compute_diff

        diff_data = compute_diff(baseline, treatment, mode=mode)
        return self.heatmap(
            diff_data,
            palette=palette,
            vcenter=vcenter,
            vmin=vmin,
            vmax=vmax,
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
        """Create side-by-side comparison of multiple datasets.

        Args:
            datasets: A mapping of dataset names to data dicts.
            palette: Name of a matplotlib colormap or a list of hex colors.
            layout: Layout orientation ("horizontal" or "vertical").
            spacing: Spacing between SVGs in viewBox units.
            **heatmap_kwargs: Additional arguments passed to `heatmap`.

        Returns:
            A new merged SVGDocument containing the compared maps.
        """
        from pathy_svg.diff import compose_side_by_side

        colored_docs = []
        titles = []
        for name, data in datasets.items():
            titles.append(name)
            colored_docs.append(self.heatmap(data, palette=palette, **heatmap_kwargs))

        new_tree = compose_side_by_side(
            colored_docs,
            titles=titles,
            layout=layout,
            spacing=spacing,
        )
        return SVGDocument(new_tree)


    def animate(
        self,
        *,
        effect: str = "pulse",
        duration: float = 2.0,
        delay_by: str = "value",
        loop: bool = True,
    ) -> SVGDocument:
        """Inject CSS animation into the SVG.

        Args:
            effect: The animation effect to apply (e.g. "pulse").
            duration: Animation duration in seconds.
            delay_by: Strategy for stagger delays ("value" or None).
            loop: Whether the animation should loop infinitely.

        Returns:
            A new SVGDocument with the CSS animation injected.
        """
        from pathy_svg.animation import inject_animation

        clone = self._clone()
        data_order = None
        if delay_by == "value" and hasattr(self, "_last_scale"):
            # Try to get ordered IDs from last heatmap
            data_order = None  # Would need stored data; use default for now
        inject_animation(
            clone._tree,
            clone._nsmap,
            effect=effect,
            duration=duration,
            delay_by=delay_by,
            loop=loop,
            data_order=data_order,
        )
        return clone


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
        """Add text labels to paths.

        Args:
            labels: A dictionary mapping path IDs to text labels.
            placement: Placement strategy for the text ("centroid" or other supported strategies).
            font_size: Font size for the labels.
            font_color: Font color for the labels.
            font_family: CSS font-family string.
            background: Optional background color for the text (creates a bounding box).
            offset: An (x, y) tuple specifying offset for the text placement.

        Returns:
            A new SVGDocument with the text labels added.
        """
        from pathy_svg.annotations import add_text_labels

        clone = self._clone()
        add_text_labels(
            clone._tree,
            clone._nsmap,
            labels,
            placement=placement,
            font_size=font_size,
            font_color=font_color,
            font_family=font_family,
            background=background,
            offset=offset,
        )
        return clone

    def add_tooltips(
        self,
        tips: dict[str, str],
        *,
        method: str = "title",
    ) -> SVGDocument:
        """Add tooltips to paths.

        Args:
            tips: A dictionary mapping path IDs to tooltip text.
            method: The method to inject tooltips ("title" for `<title>` tags).

        Returns:
            A new SVGDocument with the tooltips injected.
        """
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
        """Replace text content in <text> elements.

        Args:
            replacements: A dictionary mapping existing text content to new text.
            text_color: Optional hex color string to apply to the modified text.

        Returns:
            A new SVGDocument with the text replaced.
        """
        from pathy_svg.annotations import replace_text

        clone = self._clone()
        replace_text(clone._tree, clone._nsmap, replacements, text_color=text_color)
        return clone


    def to_png(self, path=None, **kwargs) -> bytes | None:
        """Export to PNG. Requires pathy-svg[export].

        Args:
            path: File path to save the PNG to. If None, returns the PNG bytes.
            **kwargs: Additional parameters passed to `cairosvg.svg2png`.

        Returns:
            The exported PNG as bytes if `path` is None, otherwise `None`.
        """
        from pathy_svg.export import to_png

        return to_png(self, path, **kwargs)

    def to_pdf(self, path=None) -> bytes | None:
        """Export to PDF. Requires pathy-svg[export].

        Args:
            path: File path to save the PDF to. If None, returns the PDF bytes.

        Returns:
            The exported PDF as bytes if `path` is None, otherwise `None`.
        """
        from pathy_svg.export import to_pdf

        return to_pdf(self, path)

    def to_jpeg(self, path=None, **kwargs) -> bytes | None:
        """Export to JPEG. Requires pathy-svg[export].

        Args:
            path: File path to save the JPEG to. If None, returns the JPEG bytes.
            **kwargs: Additional parameters passed to `cairosvg.svg2png` and Pillow `Image.save`.

        Returns:
            The exported JPEG as bytes if `path` is None, otherwise `None`.
        """
        from pathy_svg.export import to_jpeg

        return to_jpeg(self, path, **kwargs)

    def thumbnail(self, **kwargs):
        """Return a PIL Image thumbnail. Requires pathy-svg[export].

        Args:
            **kwargs: Arguments passed to PIL Image.thumbnail (e.g. `size`).

        Returns:
            A PIL Image representing the SVG.
        """
        from pathy_svg.export import thumbnail

        return thumbnail(self, **kwargs)

    def show(self, **kwargs):
        """Display in Jupyter. Requires pathy-svg[full].

        Args:
            **kwargs: Additional arguments passed to IPython display.
        """
        from pathy_svg.export import show

        show(self, **kwargs)


    def _clone(self) -> SVGDocument:
        """Return a deep copy of this document."""
        return SVGDocument(
            copy.deepcopy(self._tree),
            _nsmap=dict(self._nsmap),
        )


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

    @staticmethod
    def _data_from_dataframe(
        df,
        id_col: str,
        value_col: str,
    ) -> dict[str, float]:
        """Extract a data dict from a Pandas DataFrame.

        Delegates to :func:`pathy_svg.utils.dataframe_to_dict`.
        """
        from pathy_svg.utils import dataframe_to_dict

        return dataframe_to_dict(df, id_col, value_col)
