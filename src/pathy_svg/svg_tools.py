"""SVG manipulation utilities — metadata stripping, optimization, style extraction, merging."""

from __future__ import annotations

import copy
import re
from collections.abc import Iterable
from typing import TYPE_CHECKING, TypeVar

from pathy_svg._composition import (
    composition_size,
    composition_translation,
    copy_svg_panel,
    place_svg_panel,
    plan_svg_panels,
    validate_composition_layout,
)
from pathy_svg._constants import SVG_NS, Layout, local_tag
from pathy_svg.composition import CompositionResult, PanelComposition
from pathy_svg.exceptions import CompositionError, ValidationError

if TYPE_CHECKING:
    from pathy_svg.document import SVGDocument
    from pathy_svg.transform import ViewBox

_DocumentT = TypeVar("_DocumentT", bound="SVGDocument")

_CRUFT_NS = frozenset(
    {
        "http://sodipodi.sourceforge.net/DTD/sodipodi-0.0.dtd",
        "http://www.inkscape.org/namespaces/inkscape",
        "http://purl.org/dc/elements/1.1/",
        "http://creativecommons.org/ns#",
        "http://web.resource.org/cc/",
        "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    }
)

_METADATA_TAG = f"{{{SVG_NS}}}metadata"

_KEEP_EMPTY = frozenset(
    {
        "defs",
        "g",
        "svg",
        "symbol",
        "marker",
        "clipPath",
        "mask",
        "pattern",
    }
)

__all__ = [
    "compose_svgs",
    "extract_styles",
    "merge_svgs",
    "optimize_svg",
    "strip_metadata",
    "viewbox_to_pixel",
]


def viewbox_to_pixel(
    vb_x: float,
    vb_y: float,
    viewbox: ViewBox | tuple[float, float, float, float],
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
    vb_ox, vb_oy, vb_w, vb_h = viewbox
    if vb_w == 0 or vb_h == 0:
        raise ValidationError("viewBox width and height must be non-zero")
    px = (vb_x - vb_ox) / vb_w * width_px
    py = (vb_y - vb_oy) / vb_h * height_px
    return (px, py)


def compose_svgs(
    svgs: Iterable[SVGDocument],
    layout: Layout = "horizontal",
    spacing: float = 20,
) -> CompositionResult:
    """Compose SVG documents and return the document plus panel ID mappings.

    Unique valid IDs are preserved. When composition must rename an ID,
    ``result.panels[index].id_map`` exposes its output value.
    """
    from lxml import etree

    from pathy_svg.document import SVGDocument

    docs = list(svgs)
    if not docs:
        raise CompositionError("svgs must be non-empty")
    validate_composition_layout(layout)

    viewports: list[tuple[float, float] | None] = []
    for doc in docs:
        vb = doc.viewbox
        if vb is not None:
            viewports.append((vb.width, vb.height))
            continue
        w = _user_unit_length(doc._root.get("width"))
        h = _user_unit_length(doc._root.get("height"))
        if w is not None and h is not None:
            viewports.append((w, h))
        else:
            viewports.append(None)

    sizes = [
        viewport if viewport is not None else (500.0, 500.0) for viewport in viewports
    ]
    total_w, total_h = composition_size(sizes, layout, spacing)

    root = etree.Element(f"{{{SVG_NS}}}svg", nsmap={None: SVG_NS})
    root.set("viewBox", f"0 0 {total_w} {total_h}")

    plans = plan_svg_panels([doc._root for doc in docs])
    offset = 0.0
    for doc, (width, height), viewport, plan in zip(docs, sizes, viewports, plans):
        tx, ty = composition_translation(layout, main_offset=offset)
        offset += (width if layout == "horizontal" else height) + spacing

        panel_width, panel_height = viewport if viewport is not None else (None, None)
        panel = copy_svg_panel(doc._root, root, plan, panel_width, panel_height)
        place_svg_panel(panel, f"translate({tx}, {ty})")

    document = SVGDocument._from_owned_tree(etree.ElementTree(root))
    panels = tuple(
        PanelComposition._create(
            plan.index,
            plan.wrapper_id,
            plan.reference_map,
        )
        for plan in plans
    )
    return CompositionResult(document=document, panels=panels)


def merge_svgs(
    svgs: Iterable[SVGDocument],
    layout: Layout = "horizontal",
    spacing: float = 20,
) -> SVGDocument:
    """Combine multiple SVGDocument instances into a single SVGDocument.

    Args:
        svgs: Iterable of SVGDocument instances.
        layout: "horizontal" (side-by-side) or "vertical" (stacked top-to-bottom).
        spacing: Gap in viewBox units between adjacent SVGs.

    Returns:
        A new SVGDocument containing all inputs arranged according to layout.

    Raises:
        ValueError: If the svgs iterable is empty or layout is unsupported.
    """
    return compose_svgs(svgs, layout=layout, spacing=spacing).document


_USER_UNIT_LENGTH_RE = re.compile(
    r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?(?:[pP][xX])?"
)


def _user_unit_length(value: str | None) -> float | None:
    """Parse a root dimension only when it is a plain number or px length.

    Percentage and physical-unit dimensions carry no user-unit magnitude, so
    they must not be used as a nested panel viewport size.
    """
    if value is None:
        return None
    match = _USER_UNIT_LENGTH_RE.fullmatch(value.strip())
    if match is None:
        return None
    text = match.group(0)
    if text[-2:].lower() == "px":
        text = text[:-2]
    return float(text)


def strip_metadata(doc: _DocumentT) -> _DocumentT:
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
    from lxml import etree

    clone = doc._clone()
    root = clone._root

    def _is_cruft(elem: etree._Element) -> bool:
        tag = elem.tag
        if not isinstance(tag, str):
            return False
        if tag == _METADATA_TAG:
            return True
        if tag.startswith("{"):
            ns = tag[1 : tag.index("}")]
            return ns in _CRUFT_NS
        return False

    def _strip_from(parent):
        to_remove = [child for child in parent if _is_cruft(child)]
        for elem in to_remove:
            parent.remove(elem)
        for child in parent:
            _strip_from(child)

    _strip_from(root)

    dirty_nsmap = {k: v for k, v in root.nsmap.items() if v not in _CRUFT_NS}
    if len(dirty_nsmap) < len(root.nsmap):
        new_root = etree.Element(root.tag, attrib=dict(root.attrib), nsmap=dirty_nsmap)
        for child in root:
            new_root.append(copy.deepcopy(child))
        new_tree = etree.ElementTree(new_root)
        return clone._with_owned_tree(new_tree)

    return clone


def optimize_svg(doc: _DocumentT) -> _DocumentT:
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
    clone = doc._clone()

    def _optimize(parent):
        to_remove = []
        for child in parent:
            if not isinstance(child.tag, str):
                to_remove.append(child)
                continue
            _optimize(child)
            if child.text is not None and not child.text.strip():
                child.text = None
            elif child.text:
                child.text = child.text.strip()
            if child.tail is not None and not child.tail.strip():
                child.tail = None
            elif child.tail:
                child.tail = child.tail.strip()
            if (
                local_tag(child.tag) not in _KEEP_EMPTY
                and len(child) == 0
                and not child.attrib
                and not (child.text or "").strip()
            ):
                to_remove.append(child)

        for elem in to_remove:
            parent.remove(elem)

    _optimize(clone._root)
    return clone


def extract_styles(doc: _DocumentT) -> _DocumentT:
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

    clone = doc._clone()
    root = clone._root

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

    ns = root.nsmap.get(None, SVG_NS)
    defs_tag = f"{{{ns}}}defs" if ns else "defs"
    defs = root.find(defs_tag)
    if defs is None:
        defs = etree.Element(defs_tag)
        root.insert(0, defs)

    css_lines = []
    for style_val, cls_name in style_to_class.items():
        css_lines.append(f".{cls_name} {{ {style_val}; }}")
    css_text = "\n".join(css_lines)

    style_tag = f"{{{ns}}}style" if ns else "style"
    style_elem = etree.SubElement(defs, style_tag)
    style_elem.text = f"\n{css_text}\n"

    for elem, normalized in elements_with_style:
        cls_name = style_to_class[normalized]
        existing_cls = elem.get("class", "")
        new_cls = f"{existing_cls} {cls_name}".strip() if existing_cls else cls_name
        elem.set("class", new_cls)
        del elem.attrib["style"]

    return clone
