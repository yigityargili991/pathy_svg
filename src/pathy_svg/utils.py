"""Standalone helper utilities for pathy_svg.

All functions in this module are self-contained — they do not depend on
SVGDocument at import time (SVGDocument-accepting functions import it locally
to avoid circular imports).
"""

from __future__ import annotations

import bisect
import colorsys
import copy
import re




def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    """Convert a CSS hex colour string to an (R, G, B) int tuple.

    Supports both 6-digit (#rrggbb) and 3-digit (#rgb) shorthand forms.
    The leading ``#`` is optional.

    Args:
        hex_str: The hex color string to convert.

    Returns:
        A tuple of (R, G, B) integers in the range [0, 255].

    Raises:
        ValueError: If the hex string is invalid.

    Examples:
        >>> hex_to_rgb("#ff0000")  # (255, 0, 0)
        >>> hex_to_rgb("#f00")     # (255, 0, 0)
        >>> hex_to_rgb("00ff00")   # (0, 255, 0)
    """
    h = hex_str.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"Invalid hex colour: {hex_str!r}")
    try:
        r = int(h[0:2], 16)
        g = int(h[2:4], 16)
        b = int(h[4:6], 16)
    except ValueError:
        raise ValueError(f"Invalid hex colour: {hex_str!r}")
    return (r, g, b)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert (R, G, B) integers (0-255) to a lowercase CSS hex string.

    Args:
        r: Red channel value (0-255).
        g: Green channel value (0-255).
        b: Blue channel value (0-255).

    Returns:
        A lowercase CSS hex string (e.g., "#ff0000").

    Raises:
        ValueError: If any channel is out of the range [0, 255].

    Examples:
        >>> rgb_to_hex(255, 0, 0)    # "#ff0000"
        >>> rgb_to_hex(0, 128, 255)  # "#0080ff"
    """
    for name, val in (("r", r), ("g", g), ("b", b)):
        if not (0 <= val <= 255):
            raise ValueError(f"Channel {name} out of range [0, 255]: {val}")
    return f"#{round(r):02x}{round(g):02x}{round(b):02x}"


def interpolate_color(color1: str, color2: str, t: float) -> str:
    """Linearly interpolate between two hex colours.

    Args:
        color1: Starting colour (hex string, e.g. ``"#ff0000"``).
        color2: Ending colour (hex string).
        t: Interpolation factor in [0, 1]. ``t=0`` returns *color1*, ``t=1`` returns *color2*.

    Returns:
        Interpolated colour as a lowercase hex string.

    Raises:
        ValueError: If t is not in [0, 1].
    """
    if not (0.0 <= t <= 1.0):
        raise ValueError(f"Interpolation factor t must be in [0, 1], got {t}")
    r1, g1, b1 = hex_to_rgb(color1)
    r2, g2, b2 = hex_to_rgb(color2)
    r = round(r1 + (r2 - r1) * t)
    g = round(g1 + (g2 - g1) * t)
    b = round(b1 + (b2 - b1) * t)
    return rgb_to_hex(r, g, b)


def parse_svg_color(color_str: str) -> tuple[int, int, int]:
    """Parse a CSS/SVG colour string into an (R, G, B) int tuple.

    Supported formats:
    * Hex: ``"#rrggbb"`` or ``"#rgb"``
    * RGB function: ``"rgb(255, 0, 0)"``
    * HSL function: ``"hsl(0, 100%, 50%)"``
    * Named colours: ``"red"``, ``"blue"``, ``"transparent"``, etc.
      (all 140 CSS named colours via `matplotlib.colors`).

    Args:
        color_str: The SVG color string to parse.

    Returns:
        A tuple of (R, G, B) integers in the range [0, 255].

    Raises:
        ValueError: If the SVG color string is unrecognized or invalid.

    Examples:
        >>> parse_svg_color("red")              # (255, 0, 0)
        >>> parse_svg_color("#00ff00")          # (0, 255, 0)
        >>> parse_svg_color("rgb(0, 0, 255)")   # (0, 0, 255)
        >>> parse_svg_color("hsl(120, 100%, 50%)")  # (0, 255, 0)
    """
    s = color_str.strip().lower()

    if s.startswith("#"):
        return hex_to_rgb(s)

    m = re.fullmatch(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", s)
    if m:
        channels = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        for ch in channels:
            if not (0 <= ch <= 255):
                raise ValueError(f"RGB channel out of range [0, 255]: {ch}")
        return channels

    m = re.fullmatch(
        r"hsl\(\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)%\s*,\s*(\d+(?:\.\d+)?)%\s*\)",
        s,
    )
    if m:
        h = float(m.group(1)) / 360.0
        sl = float(m.group(2)) / 100.0
        l = float(m.group(3)) / 100.0  # noqa: E741
        r_f, g_f, b_f = colorsys.hls_to_rgb(h, l, sl)
        return (round(r_f * 255), round(g_f * 255), round(b_f * 255))

    try:
        import matplotlib.colors as mcolors

        rgba = mcolors.to_rgba(s)
        r = round(rgba[0] * 255)
        g = round(rgba[1] * 255)
        b = round(rgba[2] * 255)
        return (r, g, b)
    except ValueError:
        pass

    raise ValueError(f"Unrecognised SVG colour: {color_str!r}")




def normalize_values(data: dict[str, float]) -> dict[str, float]:
    """Min-max normalise a dict of float values to the range [0, 1].

    If all values are identical the function returns all zeros to avoid division-by-zero.

    Args:
        data: A dictionary mapping identifiers to numeric values.

    Returns:
        A dictionary with the same keys, mapped to normalized values in [0, 1].

    Examples:
        >>> normalize_values({"a": 0, "b": 5, "c": 10})
        # {"a": 0.0, "b": 0.5, "c": 1.0}
    """
    if not data:
        return {}
    values = list(data.values())
    lo = min(values)
    hi = max(values)
    rng = hi - lo
    if rng == 0:
        return {k: 0.0 for k in data}
    return {k: (v - lo) / rng for k, v in data.items()}


def bin_values(data: dict[str, float], breaks: list[float]) -> dict[str, int]:
    """Assign each value in data to a bin index defined by breaks.

    Bin indices are 0-based. A value ``v`` falls into bin ``i`` when
    ``breaks[i] <= v < breaks[i+1]``. Values below the first break are
    placed in bin 0; values at or above the last break are placed in the last bin.

    Args:
        data: Mapping of key to numeric value.
        breaks: Ordered sequence of boundary values that define bins. Must contain at least two elements.

    Returns:
        A dictionary mapping the same keys to integer bin indices.

    Raises:
        ValueError: If breaks contains fewer than two values.

    Examples:
        >>> bin_values({"a": 1, "b": 5, "c": 9}, [0, 3, 6, 10])
        # {"a": 0, "b": 1, "c": 2}
    """
    if len(breaks) < 2:
        raise ValueError("breaks must contain at least two values")
    sorted_breaks = sorted(breaks)
    result: dict[str, int] = {}
    n_bins = len(sorted_breaks) - 1
    for key, val in data.items():
        idx = bisect.bisect_right(sorted_breaks, val) - 1
        idx = max(0, min(idx, n_bins - 1))
        result[key] = idx
    return result




def viewbox_to_pixel(
    vb_x: float,
    vb_y: float,
    viewbox,
    width_px: float,
    height_px: float,
) -> tuple[float, float]:
    """Convert viewBox-relative coordinates to pixel coordinates.

    Args:
        vb_x: X coordinate in viewBox space.
        vb_y: Y coordinate in viewBox space.
        viewbox: A ViewBox object or a 4-tuple (x, y, width, height) describing the viewBox.
        width_px: Pixel width of the rendered SVG.
        height_px: Pixel height of the rendered SVG.

    Returns:
        A tuple of (pixel_x, pixel_y) coordinates.

    Raises:
        ValueError: If viewBox width or height is zero.

    Examples:
        >>> from pathy_svg.transform import ViewBox
        >>> viewbox_to_pixel(250, 200, ViewBox(0, 0, 500, 400), 1000, 800)
        # (500.0, 400.0)
    """
    vb_ox, vb_oy, vb_w, vb_h = viewbox[0], viewbox[1], viewbox[2], viewbox[3]
    if vb_w == 0 or vb_h == 0:
        raise ValueError("viewBox width and height must be non-zero")
    px = (vb_x - vb_ox) / vb_w * width_px
    py = (vb_y - vb_oy) / vb_h * height_px
    return (px, py)




def merge_svgs(svgs, layout: str = "horizontal", spacing: float = 20):
    """Combine multiple SVGDocument instances into a single SVGDocument.

    Args:
        svgs: Iterable of SVGDocument instances.
        layout: "horizontal" (side-by-side) or "vertical" (stacked top-to-bottom).
        spacing: Gap in viewBox units between adjacent SVGs.

    Returns:
        A new SVGDocument containing all inputs arranged according to layout.

    Raises:
        ValueError: If the svgs iterable is empty.
    """
    from pathy_svg.document import SVGDocument
    from lxml import etree

    SVG_NS = "http://www.w3.org/2000/svg"
    docs = list(svgs)
    if not docs:
        raise ValueError("svgs must be non-empty")

    # Collect dimensions
    infos = []
    for doc in docs:
        vb = doc.viewbox
        w, h = doc.dimensions
        if vb is not None:
            infos.append({"w": vb.width, "h": vb.height, "vb": vb})
        elif w is not None and h is not None:
            infos.append({"w": w, "h": h, "vb": None})
        else:
            # Fallback: use 500×500
            infos.append({"w": 500.0, "h": 500.0, "vb": None})

    # Compute total canvas size
    if layout == "horizontal":
        total_w = sum(info["w"] for info in infos) + spacing * (len(infos) - 1)
        total_h = max(info["h"] for info in infos)
    else:  # vertical
        total_w = max(info["w"] for info in infos)
        total_h = sum(info["h"] for info in infos) + spacing * (len(infos) - 1)

    # Build root <svg>
    root = etree.Element(
        f"{{{SVG_NS}}}svg",
        nsmap={None: SVG_NS},
    )
    root.set("viewBox", f"0 0 {total_w} {total_h}")
    root.set("xmlns", SVG_NS)

    # Place each child SVG inside a <g transform="translate(...)">
    offset = 0.0
    for i, (doc, info) in enumerate(zip(docs, infos)):
        if layout == "horizontal":
            tx, ty = offset, 0.0
            offset += info["w"] + spacing
        else:
            tx, ty = 0.0, offset
            offset += info["h"] + spacing

        g = etree.SubElement(root, f"{{{SVG_NS}}}g")
        g.set("transform", f"translate({tx}, {ty})")

        # Copy all children of the source SVG's root into g
        src_root = doc.root
        for child in src_root:
            g.append(copy.deepcopy(child))

    tree = etree.ElementTree(root)
    return SVGDocument(tree)


def strip_metadata(doc):
    """Return a new SVGDocument with Inkscape/Illustrator namespace elements removed.

    Removes elements from these namespaces:
    * `sodipodi:*`
    * `inkscape:*`
    * `dc:*`
    * `cc:*`
    * `rdf:*`
    * `<metadata>` elements

    Also strips the corresponding `xmlns:` declarations from the root.

    Args:
        doc: The SVGDocument to process.

    Returns:
        A new SVGDocument without the metadata elements.
    """
    from pathy_svg.document import SVGDocument
    from lxml import etree

    CRUFT_NS = {
        "http://sodipodi.sourceforge.net/DTD/sodipodi-0.0.dtd",
        "http://www.inkscape.org/namespaces/inkscape",
        "http://purl.org/dc/elements/1.1/",
        "http://creativecommons.org/ns#",
        "http://web.resource.org/cc/",
        "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    }
    SVG_NS = "http://www.w3.org/2000/svg"
    METADATA_TAG = f"{{{SVG_NS}}}metadata"

    clone = doc._clone()
    root = clone.root

    def _is_cruft(elem: etree._Element) -> bool:
        tag = elem.tag
        if not isinstance(tag, str):
            return False  # processing instructions / comments
        if tag == METADATA_TAG:
            return True
        if tag.startswith("{"):
            ns = tag[1 : tag.index("}")]
            return ns in CRUFT_NS
        return False

    # Remove cruft elements (iterate in reverse to allow safe removal)
    def _strip_from(parent):
        to_remove = [child for child in parent if _is_cruft(child)]
        for elem in to_remove:
            parent.remove(elem)
        for child in parent:
            _strip_from(child)

    _strip_from(root)

    # Strip cruft namespace attributes from root nsmap (requires re-serialise trick)
    # lxml nsmap is read-only, so we rebuild the root element if necessary
    dirty_nsmap = {k: v for k, v in root.nsmap.items() if v not in CRUFT_NS}
    if dirty_nsmap != dict(root.nsmap):
        new_root = etree.Element(root.tag, attrib=dict(root.attrib), nsmap=dirty_nsmap)
        for child in root:
            new_root.append(copy.deepcopy(child))
        new_tree = etree.ElementTree(new_root)
        return SVGDocument(new_tree)

    return clone


def optimize_svg(doc):
    """Return a new SVGDocument with XML comments removed and whitespace collapsed.

    Specifically:
    * Removes all XML comment nodes (`<!-- ... -->`)
    * Strips leading/trailing whitespace from text content in elements
    * Removes elements that are completely empty and carry no attributes
      (excluding `<defs>`, `<g>`, `<svg>` which may be intentionally
      empty containers).

    Args:
        doc: The SVGDocument to optimize.

    Returns:
        A new optimized SVGDocument.
    """

    KEEP_EMPTY = {"defs", "g", "svg", "symbol", "marker", "clipPath", "mask", "pattern"}

    clone = doc._clone()

    def _local(tag):
        if isinstance(tag, str) and tag.startswith("{"):
            return tag.split("}", 1)[1]
        return tag if isinstance(tag, str) else ""

    def _optimize(parent):
        to_remove = []
        for child in parent:
            if not isinstance(child.tag, str):
                # Comment / PI node
                to_remove.append(child)
                continue
            # Recurse first
            _optimize(child)
            # Collapse whitespace in text/tail
            if child.text and child.text.strip() == "":
                child.text = None
            elif child.text:
                child.text = child.text.strip()
            if child.tail and child.tail.strip() == "":
                child.tail = None
            elif child.tail:
                child.tail = child.tail.strip()
            # Remove empty childless elements with no attrs
            local = _local(child.tag)
            if (
                local not in KEEP_EMPTY
                and len(child) == 0
                and not dict(child.attrib)
                and not (child.text or "").strip()
            ):
                to_remove.append(child)

        for elem in to_remove:
            parent.remove(elem)

    _optimize(clone.root)
    return clone


def extract_styles(doc):
    """Pull inline `style="..."` attributes into a single `<style>` block.

    Each unique inline style string is assigned a generated class name
    (`pathy-s0`, `pathy-s1`, ...). The element's `style` attribute is
    removed and replaced with a `class` attribute referencing the generated
    class. A `<style>` element is inserted into `<defs>` (created if absent).

    Args:
        doc: The SVGDocument to process.

    Returns:
        A new SVGDocument with a `<style>` block in `<defs>`.
    """
    from lxml import etree

    SVG_NS = "http://www.w3.org/2000/svg"

    clone = doc._clone()
    root = clone.root

    # Collect all unique inline styles
    style_to_class: dict[str, str] = {}
    elements_with_style: list[tuple] = []

    for elem in root.iter():
        style_val = elem.get("style")
        if style_val:
            normalized = style_val.strip().rstrip(";")
            if normalized not in style_to_class:
                cls_name = f"pathy-s{len(style_to_class)}"
                style_to_class[normalized] = cls_name
            elements_with_style.append((elem, normalized))

    if not elements_with_style:
        return clone

    # Find or create <defs>
    ns = root.nsmap.get(None, SVG_NS)
    defs_tag = f"{{{ns}}}defs" if ns else "defs"
    defs = root.find(defs_tag)
    if defs is None:
        defs = etree.Element(defs_tag)
        root.insert(0, defs)

    # Build CSS text
    css_lines = []
    for style_val, cls_name in style_to_class.items():
        css_lines.append(f".{cls_name} {{ {style_val}; }}")
    css_text = "\n".join(css_lines)

    style_tag = f"{{{ns}}}style" if ns else "style"
    style_elem = etree.SubElement(defs, style_tag)
    style_elem.text = f"\n{css_text}\n"

    # Replace style attrs with class attrs
    for elem, normalized in elements_with_style:
        cls_name = style_to_class[normalized]
        existing_cls = elem.get("class", "")
        new_cls = f"{existing_cls} {cls_name}".strip() if existing_cls else cls_name
        elem.set("class", new_cls)
        del elem.attrib["style"]

    return clone


def dataframe_to_dict(df, id_col: str, value_col: str) -> dict[str, float]:
    """Extract a data dict from a Pandas DataFrame.

    Args:
        df: A Pandas DataFrame.
        id_col: Column name for element IDs.
        value_col: Column name for numeric values.

    Returns:
        A dict mapping IDs to float values.

    Raises:
        ValueError: If required columns are missing from the DataFrame.

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"id": ["a", "b"], "value": [1.0, 2.0]})
        >>> dataframe_to_dict(df, "id", "value")
        {"a": 1.0, "b": 2.0}
    """
    import pandas as pd

    if id_col not in df.columns:
        raise ValueError(f"Column '{id_col}' not found in DataFrame")
    if value_col not in df.columns:
        raise ValueError(f"Column '{value_col}' not found in DataFrame")
    numeric = pd.to_numeric(df[value_col], errors="coerce")
    valid = numeric.dropna()
    return dict(zip(df.loc[valid.index, id_col].astype(str), valid))

