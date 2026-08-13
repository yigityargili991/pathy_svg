"""Private helpers for safely composing independent SVG documents."""

from __future__ import annotations

import copy
import re
from collections import ChainMap, Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from itertools import chain

from lxml import etree

from pathy_svg._constants import SVG_NS, Layout, local_tag
from pathy_svg._css import style_property
from pathy_svg.exceptions import CompositionError

_ARIA_IDREF_ATTRIBUTES = frozenset(
    {
        "aria-activedescendant",
        "aria-controls",
        "aria-describedby",
        "aria-details",
        "aria-errormessage",
        "aria-flowto",
        "aria-labelledby",
        "aria-owns",
    }
)

_URL_REFERENCE_ATTRIBUTES = frozenset(
    {
        "clip-path",
        "cursor",
        "fill",
        "filter",
        "marker",
        "marker-end",
        "marker-mid",
        "marker-start",
        "mask",
        "shape-inside",
        "shape-subtract",
        "stroke",
    }
)

_CSS_GAP = r"(?:\s|/\*.*?\*/)*"
_ATTRIBUTE_SELECTOR_RE = re.compile(
    rf"^\[(?P<head>{_CSS_GAP}(?:(?:[-\w*]+)?\|)?"
    rf"(?P<name>[-\w]+){_CSS_GAP})"
    rf"(?P<operator>~=|\^=|\$=|\*=|\|=|=)(?P<space>{_CSS_GAP})"
    r"(?P<value>\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|"
    rf"(?:\\.|[^\]\s])+)(?P<tail>{_CSS_GAP}(?:[iIsS])?{_CSS_GAP})\]$",
    re.DOTALL,
)

_ANIMATION_SHORTHAND_KEYWORDS = frozenset(
    {
        "alternate",
        "alternate-reverse",
        "auto",
        "backwards",
        "both",
        "ease",
        "ease-in",
        "ease-in-out",
        "ease-out",
        "forwards",
        "infinite",
        "inherit",
        "initial",
        "linear",
        "none",
        "normal",
        "paused",
        "reverse",
        "revert",
        "revert-layer",
        "running",
        "step-end",
        "step-start",
        "unset",
    }
)

_UNSAFE_CSS_AT_RULES = frozenset({"import", "property", "counter-style"})
_SUPPORTED_CSS_AT_RULES = frozenset(
    {
        "-webkit-keyframes",
        "container",
        "document",
        "font-face",
        "keyframes",
        "layer",
        "media",
        "namespace",
        "scope",
        "starting-style",
        "supports",
    }
)
_ANIMATION_NAME_KEYWORDS = frozenset(
    {"inherit", "initial", "none", "revert", "revert-layer", "unset"}
)
_ANIMATION_SHORTHAND_ROLES = {
    "alternate": "direction",
    "alternate-reverse": "direction",
    "auto": "auto",
    "backwards": "fill-mode",
    "both": "fill-mode",
    "ease": "timing-function",
    "ease-in": "timing-function",
    "ease-in-out": "timing-function",
    "ease-out": "timing-function",
    "forwards": "fill-mode",
    "infinite": "iteration-count",
    "linear": "timing-function",
    "normal": "direction",
    "paused": "play-state",
    "reverse": "direction",
    "running": "play-state",
    "step-end": "timing-function",
    "step-start": "timing-function",
}
_ANIMATION_FUNCTION_ROLES = {
    "cubic-bezier": "timing-function",
    "linear": "timing-function",
    "scroll": "timeline",
    "steps": "timing-function",
    "view": "timeline",
}

_MAX_SELECTOR_VARIANTS = 64
_PRIVATE_ANIMATION_NS = "urn:pathy-svg:private:animation:v1"
_PRIVATE_KEYFRAME_ATTR = f"{{{_PRIVATE_ANIMATION_NS}}}keyframe"
_CLOCK_VALUE_RE = re.compile(
    r"^[+-]?(?:(?:(?:\d+(?:\.\d*)?|\.\d+)(?:h|min|s|ms)?)|"
    r"(?:\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?))$",
    re.IGNORECASE,
)
_CSS_NUMBER_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$")
_CSS_TIME_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:ms|s)$", re.IGNORECASE)
_NON_SYNCBASE_TIMING_RE = re.compile(
    r"^(?:indefinite|media|"
    r"(?:wallclock|accesskey|repeat)\s*\([^()]*\)(?:\s*[+-][^;]*)?)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PanelCopyPlan:
    """Precomputed IDs for copying one panel without cross-panel collisions."""

    index: int
    wrapper_id: str
    root_id: tuple[str, str] | None
    descendant_ids: tuple[tuple[str, str], ...]
    reference_map: dict[str, str]
    blocked_ids: frozenset[str]


def validate_composition_layout(layout: str) -> None:
    """Validate the two layouts supported by all composition APIs."""
    if layout not in ("horizontal", "vertical"):
        raise CompositionError("layout must be 'horizontal' or 'vertical'")


def composition_size(
    sizes: list[tuple[float, float]], layout: Layout, spacing: float
) -> tuple[float, float]:
    """Return the common untitled extent calculation for composed panels."""
    validate_composition_layout(layout)
    if layout == "horizontal":
        return (
            sum(width for width, _ in sizes) + spacing * (len(sizes) - 1),
            max(height for _, height in sizes),
        )
    return (
        max(width for width, _ in sizes),
        sum(height for _, height in sizes) + spacing * (len(sizes) - 1),
    )


def composition_translation(
    layout: Layout,
    main_offset: float,
    cross_offset: float = 0.0,
) -> tuple[float, float]:
    """Place one nested panel viewport consistently for either layout."""
    validate_composition_layout(layout)
    if layout == "horizontal":
        return main_offset, cross_offset
    return cross_offset, main_offset


def plan_svg_panels(source_roots: list[etree._Element]) -> list[PanelCopyPlan]:
    """Plan globally unique output IDs while retaining every safe source ID."""
    reserved = {f"pathy-panel-{index}" for index in range(len(source_roots))}
    panel_entries: list[list[str]] = []
    for root in source_roots:
        panel_entries.append(
            [
                elem_id
                for elem in chain((root,), root.iterdescendants())
                if isinstance(elem.tag, str) and (elem_id := elem.get("id")) is not None
            ]
        )

    counts = Counter(elem_id for entries in panel_entries for elem_id in entries)
    preserved = {
        elem_id
        for elem_id, count in counts.items()
        if count == 1 and elem_id not in reserved and _valid_output_id(elem_id)
    }
    claimed = set(preserved) | reserved
    next_suffixes: dict[str, int] = {}
    plans: list[PanelCopyPlan] = []

    for index, (root, entries) in enumerate(zip(source_roots, panel_entries)):
        prefix = f"pathy-panel-{index}"
        root_id = root.get("id")
        reference_map: dict[str, str] = {}
        cursor = 0

        planned_root_id: tuple[str, str] | None = None
        if root_id is not None:
            new_root_id = _planned_id(
                root_id, prefix, preserved, claimed, next_suffixes
            )
            planned_root_id = (root_id, new_root_id)
            cursor = 1
            reference_map.setdefault(root_id, new_root_id)

        descendant_ids: list[tuple[str, str]] = []
        for old_id in entries[cursor:]:
            new_id = _planned_id(old_id, prefix, preserved, claimed, next_suffixes)
            descendant_ids.append((old_id, new_id))
            reference_map.setdefault(old_id, new_id)

        plans.append(
            PanelCopyPlan(
                index=index,
                wrapper_id=prefix,
                root_id=planned_root_id,
                descendant_ids=tuple(descendant_ids),
                reference_map=reference_map,
                blocked_ids=frozenset(),
            )
        )

    blocked_ids = frozenset(claimed)
    return [
        PanelCopyPlan(
            index=plan.index,
            wrapper_id=plan.wrapper_id,
            root_id=plan.root_id,
            descendant_ids=plan.descendant_ids,
            reference_map=plan.reference_map,
            blocked_ids=blocked_ids,
        )
        for plan in plans
    ]


def _planned_id(
    old_id: str,
    prefix: str,
    preserved: set[str],
    claimed: set[str],
    next_suffixes: dict[str, int],
) -> str:
    if old_id in preserved and _valid_output_id(old_id):
        return old_id

    base_id = f"{prefix}--{_sanitize_id_component(old_id)}"
    if base_id not in claimed:
        claimed.add(base_id)
        next_suffixes.setdefault(base_id, 1)
        return base_id

    duplicate = next_suffixes.get(base_id, 1)
    new_id = f"{base_id}--duplicate-{duplicate}"
    while new_id in claimed:
        duplicate += 1
        new_id = f"{base_id}--duplicate-{duplicate}"
    next_suffixes[base_id] = duplicate + 1
    claimed.add(new_id)
    return new_id


def _valid_output_id(elem_id: str) -> bool:
    return bool(elem_id) and not any(
        char.isspace() or ord(char) < 0x20 for char in elem_id
    )


def _sanitize_id_component(elem_id: str) -> str:
    if not elem_id:
        return "empty-id"
    sanitized = "".join(
        "-" if char.isspace() or ord(char) < 0x20 else char for char in elem_id
    ).strip("-")
    return sanitized or "empty-id"


def copy_svg_panel(
    source_root: etree._Element,
    target_root: etree._Element,
    plan: PanelCopyPlan,
    width: float | None,
    height: float | None,
) -> etree._Element:
    """Copy one source as a real nested SVG viewport within an isolated panel.

    Passing ``None`` for *width* and *height* keeps the source's own
    dimension attributes, embedding the panel without a fabricated viewport.
    """
    panel = etree.SubElement(target_root, f"{{{SVG_NS}}}g")
    panel.set("id", plan.wrapper_id)
    panel.set("data-panel-index", str(plan.index))

    nested = copy.deepcopy(source_root)
    panel.append(nested)
    nested.set("x", "0")
    nested.set("y", "0")
    if width is not None and height is not None:
        nested.set("width", str(width))
        nested.set("height", str(height))
    if (
        nested.get("overflow") is None
        and style_property(nested.get("style"), "overflow") is None
    ):
        nested.set("overflow", "visible")

    if plan.root_id is None:
        nested.attrib.pop("id", None)
    else:
        old_root_id, new_root_id = plan.root_id
        nested.set("id", new_root_id)
        if new_root_id != old_root_id:
            nested.set("data-original-id", old_root_id)

    copied_with_ids = (
        elem
        for elem in nested.iterdescendants()
        if isinstance(elem.tag, str) and elem.get("id") is not None
    )

    for elem, (old_id, new_id) in zip(
        copied_with_ids, plan.descendant_ids, strict=True
    ):
        elem.set("id", new_id)
        if new_id != old_id:
            elem.set("data-original-id", old_id)

    keyframe_names: list[str] = []
    for style in nested.iter():
        if not isinstance(style.tag, str) or local_tag(style.tag) != "style":
            continue
        css = _style_css_content(style)
        if css:
            _validate_css_for_composition(css)
            for name in _find_css_keyframes(css):
                if name not in keyframe_names:
                    keyframe_names.append(name)
    keyframe_map: dict[str, str] = {}
    claimed_keyframes: set[str] = set()
    for name in keyframe_names:
        base = f"{plan.wrapper_id}--keyframe--{_sanitize_id_component(name)}"
        alias = base
        suffix = 1
        while alias in claimed_keyframes:
            alias = f"{base}--duplicate-{suffix}"
            suffix += 1
        claimed_keyframes.add(alias)
        keyframe_map[name] = alias
    rewriter = _ReferenceRewriter(
        plan.reference_map,
        plan.blocked_ids,
        plan.wrapper_id,
        keyframe_map,
    )
    for elem in list(nested.iter()):
        if not isinstance(elem.tag, str):
            continue
        rewriter.rewrite_element(elem)

    return panel


def _style_css_content(style: etree._Element) -> str:
    """Collect a <style> element's full CSS text in document order.

    Comment and processing-instruction children contribute no CSS themselves,
    but the text in their tails does.
    """
    parts = [style.text or ""]
    parts.extend(child.tail or "" for child in style)
    return "".join(parts)


def place_svg_panel(panel: etree._Element, placement: str) -> None:
    """Apply layout placement before any transform inherited from the source root."""
    source_transform = panel.get("transform")
    transform = f"{placement} {source_transform}" if source_transform else placement
    panel.set("transform", transform)


class _ReferenceRewriter:
    def __init__(
        self,
        id_map: dict[str, str],
        blocked_ids: frozenset[str],
        scope_id: str,
        keyframe_map: dict[str, str],
    ) -> None:
        self.id_map = id_map
        self.blocked_ids = blocked_ids
        self.generated_ids: set[str] = set()
        self.unresolved_map: dict[str, str] = {}
        self.unresolved_suffixes: dict[str, int] = {}
        self.scope_id = scope_id
        self.keyframe_map = keyframe_map

    def map_fragment(self, fragment: str) -> str:
        mapped = self.id_map.get(fragment)
        if mapped is None:
            mapped = self.unresolved_map.get(fragment)
        if mapped is not None:
            return mapped
        base = f"{self.scope_id}--unresolved--{_sanitize_id_component(fragment)}"
        mapped = base
        duplicate = self.unresolved_suffixes.get(base, 1)
        while mapped in self.blocked_ids or mapped in self.generated_ids:
            mapped = f"{base}--duplicate-{duplicate}"
            duplicate += 1
        self.unresolved_suffixes[base] = duplicate
        self.unresolved_map[fragment] = mapped
        self.generated_ids.add(mapped)
        return mapped

    def rewrite_element(self, elem: etree._Element) -> None:
        private_keyframe = elem.get(_PRIVATE_KEYFRAME_ATTR)
        if private_keyframe in self.keyframe_map:
            elem.set(_PRIVATE_KEYFRAME_ATTR, self.keyframe_map[private_keyframe])
        for attr_name, value in list(elem.attrib.items()):
            attr_local_name = local_tag(attr_name)
            rewritten = value
            if attr_local_name == "style":
                rewritten = _rewrite_css_urls(value, self.map_fragment)
                rewritten = _rewrite_animation_declarations(
                    rewritten, self.keyframe_map
                )
            elif attr_local_name in _URL_REFERENCE_ATTRIBUTES:
                rewritten = _rewrite_css_urls(value, self.map_fragment)

            if attr_local_name == "href":
                rewritten = _rewrite_href(rewritten, self.map_fragment)
            elif attr_local_name in _ARIA_IDREF_ATTRIBUTES:
                rewritten = _rewrite_idref_list(rewritten, self.map_fragment)
            elif attr_local_name in {"begin", "end"}:
                rewritten = _rewrite_smil_timing(
                    rewritten,
                    ChainMap(self.id_map, self.unresolved_map),
                    self.map_fragment,
                )
            if rewritten != value:
                elem.set(attr_name, rewritten)

        if local_tag(elem.tag) == "style":
            css = _style_css_content(elem)
            if css:
                elem.text = _rewrite_css(
                    css,
                    self.id_map,
                    self.map_fragment,
                    self.scope_id,
                    self.keyframe_map,
                )
                for child in list(elem):
                    elem.remove(child)


def _rewrite_href(value: str, map_fragment: Callable[[str], str]) -> str:
    left_trimmed = value.lstrip()
    if not left_trimmed.startswith("#"):
        return value
    fragment = left_trimmed[1:]
    return f"#{map_fragment(fragment)}"


def _rewrite_idref_list(value: str, map_fragment: Callable[[str], str]) -> str:
    return " ".join(map_fragment(token) for token in value.split())


def _rewrite_smil_timing(
    value: str,
    id_map: Mapping[str, str],
    map_fragment: Callable[[str], str],
) -> str:
    output: list[str] = []
    for entry in value.split(";"):
        match = re.match(r"(?P<leading>\s*)(?P<body>\S.*?)(?P<trailing>\s*)$", entry)
        if match is None:
            output.append(entry)
            continue
        body = match.group("body")
        if _CLOCK_VALUE_RE.fullmatch(body) or _NON_SYNCBASE_TIMING_RE.match(body):
            output.append(entry)
            continue
        separators = [index for index, char in enumerate(body) if char == "."]
        split_at = next(
            (index for index in reversed(separators) if body[:index] in id_map),
            -1,
        )
        if split_at < 0:
            split_at = next(
                (
                    index
                    for index in reversed(separators)
                    if re.match(r"[A-Za-z_]", body[index + 1 :])
                ),
                -1,
            )
        if split_at < 0:
            output.append(entry)
            continue
        output.append(
            f"{match.group('leading')}{map_fragment(body[:split_at])}"
            f"{body[split_at:]}{match.group('trailing')}"
        )
    return ";".join(output)


def _find_css_keyframes(css: str) -> list[str]:
    names: list[str] = []
    index = 0
    while index < len(css):
        if css.startswith("/*", index):
            index = _consume_css_comment(css, index)
            continue
        if css[index] in "\"'":
            index = _consume_css_string(css, index)
            continue
        keyframe_end = _keyframes_keyword_end(css, index)
        if keyframe_end is not None:
            name_start = _skip_css_gap(css, keyframe_end)
            name_end = _consume_css_identifier(css, name_start)
            if name_end > name_start:
                name = _css_unescape(css[name_start:name_end])
                if name not in names:
                    names.append(name)
                index = name_end
                continue
        function_open = _css_function_open_paren(css, index)
        if function_open is not None:
            index = _consume_balanced_function(css, function_open)
            continue
        index += 1
    return names


def _validate_css_for_composition(css: str) -> None:
    """Reject document-global CSS that cannot be safely panel-isolated."""
    index = 0
    while index < len(css):
        if css.startswith("/*", index):
            index = _consume_css_comment(css, index)
            continue
        if css[index] in "\"'":
            index = _consume_css_string(css, index)
            continue
        function_open = _css_function_open_paren(css, index)
        if function_open is not None:
            index = _consume_balanced_function(css, function_open)
            continue
        if css[index] != "@":
            index += 1
            continue
        end = _consume_css_identifier(css, index + 1)
        rule_name = _css_unescape(css[index + 1 : end]).lower()
        if rule_name in _UNSAFE_CSS_AT_RULES:
            raise CompositionError(
                f"Cannot safely compose SVG CSS containing @{rule_name}"
            )
        if rule_name not in _SUPPORTED_CSS_AT_RULES:
            raise CompositionError(
                f"Cannot safely compose unsupported SVG CSS @{rule_name}"
            )
        if rule_name == "layer" and (
            (prelude := _skip_css_gap(css, end)) >= len(css) or css[prelude] != "{"
        ):
            raise CompositionError("Cannot safely compose named CSS @layer rules")
        if rule_name == "font-face":
            _reject_font_face_local_references(css, end)
        index = max(end, index + 1)


def _reject_font_face_local_references(css: str, prelude_start: int) -> None:
    """Reject @font-face blocks whose src references local url(#...) fragments."""
    block_start = _skip_css_gap(css, prelude_start)
    if block_start >= len(css) or css[block_start] != "{":
        return
    block_end = _consume_css_block(css, block_start)
    fragments: list[str] = []

    def record(fragment: str) -> str:
        fragments.append(fragment)
        return fragment

    _rewrite_css_urls(css[block_start:block_end], record)
    if fragments:
        raise CompositionError(
            "Cannot safely compose @font-face using local url(#...) references"
        )


def _consume_css_block(css: str, open_brace: int) -> int:
    depth = 1
    index = open_brace + 1
    while index < len(css):
        if css.startswith("/*", index):
            index = _consume_css_comment(css, index)
            continue
        if css[index] in "\"'":
            index = _consume_css_string(css, index)
            continue
        if css[index] == "{":
            depth += 1
        elif css[index] == "}":
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    return len(css)


def _rewrite_css(
    css: str,
    id_map: dict[str, str],
    map_fragment: Callable[[str], str],
    scope_id: str,
    keyframe_map: dict[str, str],
) -> str:
    css = _rewrite_css_urls(css, map_fragment)
    css = _rewrite_animation_declarations(css, keyframe_map)
    replacements: list[tuple[int, int, str]] = []
    contexts = ["rules"]
    segment_start = 0
    paren_depth = 0
    bracket_depth = 0
    index = 0
    while index < len(css):
        if css.startswith("/*", index):
            index = _consume_css_comment(css, index)
            continue
        if css[index] in "\"'":
            index = _consume_css_string(css, index)
            continue
        url_open = _css_url_open_paren(css, index)
        if url_open is not None:
            end, _ = _rewrite_css_url_function(
                css, index, url_open, lambda fragment: fragment
            )
            if end is not None:
                index = end
                continue

        char = css[index]
        if char == "(":
            paren_depth += 1
        elif char == ")" and paren_depth:
            paren_depth -= 1
        elif char == "[":
            bracket_depth += 1
        elif char == "]" and bracket_depth:
            bracket_depth -= 1
        elif char == "{" and paren_depth == bracket_depth == 0:
            header = css[segment_start:index]
            rewritten, child_context = _rewrite_css_header(
                header,
                contexts[-1],
                id_map,
                map_fragment,
                scope_id,
                keyframe_map,
            )
            if rewritten != header:
                replacements.append((segment_start, index, rewritten))
            contexts.append(child_context)
            segment_start = index + 1
        elif char == "}" and paren_depth == bracket_depth == 0:
            if len(contexts) > 1:
                contexts.pop()
            segment_start = index + 1
        elif char == ";" and paren_depth == bracket_depth == 0:
            segment_start = index + 1
        index += 1
    return _apply_replacements(css, replacements)


def _rewrite_css_header(
    header: str,
    parent_context: str,
    id_map: dict[str, str],
    map_fragment: Callable[[str], str],
    scope_id: str,
    keyframe_map: dict[str, str],
) -> tuple[str, str]:
    content_start = _skip_css_gap(header, 0)
    keyframe_end = _keyframes_keyword_end(header, content_start)
    if keyframe_end is not None:
        name_start = _skip_css_gap(header, keyframe_end)
        name_end = _consume_css_identifier(header, name_start)
        old_name = _css_unescape(header[name_start:name_end])
        new_name = keyframe_map.get(old_name, old_name)
        rewritten = (
            header[:name_start] + _css_escape_identifier(new_name) + header[name_end:]
        )
        return rewritten, "keyframes"

    stripped = header[content_start:]
    if stripped.startswith("@"):
        lower = _strip_css_comments(stripped).lower()
        nested_parent = parent_context in {"declarations", "nested_rules"}
        if lower.startswith("@scope"):
            return (
                _rewrite_scope_prelude(
                    header,
                    id_map,
                    map_fragment,
                    scope_id,
                    nested=nested_parent,
                ),
                "nested_rules" if nested_parent else "rules",
            )
        if lower.startswith("@starting-style"):
            return (
                header,
                "declarations" if nested_parent else "rules",
            )
        if lower.startswith(
            ("@media", "@supports", "@layer", "@container", "@document")
        ):
            return header, "nested_rules" if nested_parent else "rules"
        return header, "declarations"
    if parent_context == "keyframes":
        return header, "declarations"
    nested = parent_context in {"declarations", "nested_rules"}
    return (
        _rewrite_selector_segment(
            header, id_map, map_fragment, scope_id, nested=nested
        ),
        "declarations",
    )


def _rewrite_scope_prelude(
    header: str,
    id_map: dict[str, str],
    map_fragment: Callable[[str], str],
    scope_id: str,
    *,
    nested: bool,
) -> str:
    replacements: list[tuple[int, int, str]] = []
    index = 0
    while index < len(header):
        if header.startswith("/*", index):
            index = _consume_css_comment(header, index)
            continue
        if header[index] in "\"'":
            index = _consume_css_string(header, index)
            continue
        if header[index] != "(":
            index += 1
            continue
        end = _consume_balanced_function(header, index)
        if end <= index + 1:
            break
        selector = header[index + 1 : end - 1]
        rewritten = _rewrite_selector_segment(
            selector,
            id_map,
            map_fragment,
            scope_id,
            nested=nested,
        )
        replacements.append((index + 1, end - 1, rewritten))
        index = end
    return _apply_replacements(header, replacements)


def _rewrite_selector_segment(
    selector: str,
    id_map: dict[str, str],
    map_fragment: Callable[[str], str],
    scope_id: str,
    *,
    nested: bool,
) -> str:
    rewritten: list[str] = []
    for part in _split_selector_list(selector):
        for variant in _rewrite_single_selector(part, id_map, map_fragment):
            rewritten.append(_scope_selector(variant, scope_id, nested=nested))
    return ", ".join(rewritten)


def _rewrite_single_selector(
    selector: str,
    id_map: dict[str, str],
    map_fragment: Callable[[str], str],
) -> list[str]:
    output = [""]
    index = 0
    while index < len(selector):
        if selector.startswith("/*", index):
            end = _consume_css_comment(selector, index)
            output = [part + selector[index:end] for part in output]
            index = end
            continue
        char = selector[index]
        if char in "\"'":
            end = _consume_css_string(selector, index)
            output = [part + selector[index:end] for part in output]
            index = end
            continue
        if char == "[":
            end = _consume_attribute_selector(selector, index)
            token = selector[index:end]
            variants = _rewrite_attribute_selector(token, id_map, map_fragment)
            if len(output) * len(variants) > _MAX_SELECTOR_VARIANTS:
                raise CompositionError(
                    "Cannot safely compose CSS selector: case-insensitive IDREF "
                    f"expansion exceeds {_MAX_SELECTOR_VARIANTS} variants"
                )
            output = [part + variant for part in output for variant in variants]
            index = end
            continue
        if char == "#":
            end = _consume_css_identifier(selector, index + 1)
            if end > index + 1:
                old_id = _css_unescape(selector[index + 1 : end])
                new_id = map_fragment(old_id)
                output = [
                    part + f"#{_css_escape_identifier(new_id)}" for part in output
                ]
                index = end
                continue
        output = [part + char for part in output]
        index += 1
    return output


def _rewrite_attribute_selector(
    selector: str,
    id_map: dict[str, str],
    map_fragment: Callable[[str], str],
) -> list[str]:
    match = _ATTRIBUTE_SELECTOR_RE.match(selector)
    if match is None:
        return [selector]

    name = match.group("name").lower()
    operator = match.group("operator")
    raw_value = match.group("value")
    quote = raw_value[0] if raw_value[0] in "\"'" else ""
    encoded_value = raw_value[1:-1] if quote else raw_value
    value = _css_unescape(encoded_value)
    rewritten_values: list[str] = []
    case_insensitive = (
        _strip_css_comments(match.group("tail") or "").strip().lower() == "i"
    )

    if operator in {"^=", "$=", "*=", "|="}:
        _reject_unsafe_reference_selector(
            name,
            operator,
            value,
            case_insensitive,
            id_map,
        )
        return [selector]

    if name == "id" and operator == "=":
        rewritten_values = _css_attribute_references(
            id_map, map_fragment, value, case_insensitive
        )
    elif name == "href" and operator == "=" and value.startswith("#"):
        rewritten_values = [
            f"#{new_id}"
            for new_id in _css_attribute_references(
                id_map, map_fragment, value[1:], case_insensitive
            )
        ]
    elif name in _ARIA_IDREF_ATTRIBUTES:
        if operator == "~=":
            rewritten_values = _css_attribute_references(
                id_map, map_fragment, value, case_insensitive
            )
        elif operator == "=":
            tokens = value.split()
            value_options = [
                _css_attribute_references(id_map, map_fragment, token, case_insensitive)
                for token in tokens
            ]
            combinations = 1
            for options in value_options:
                combinations *= len(options)
                if combinations > _MAX_SELECTOR_VARIANTS:
                    raise CompositionError(
                        "Cannot safely compose CSS selector: case-insensitive "
                        "IDREF expansion exceeds "
                        f"{_MAX_SELECTOR_VARIANTS} variants"
                    )
            rewritten_values = [""]
            for options in value_options:
                rewritten_values = [
                    f"{prefix} {option}".strip()
                    for prefix in rewritten_values
                    for option in options
                ]

    if not rewritten_values:
        return [selector]

    tail = match.group("tail") or ""
    output: list[str] = []
    for rewritten in dict.fromkeys(rewritten_values):
        if quote:
            new_value = f"{quote}{_css_escape_string(rewritten, quote)}{quote}"
        else:
            new_value = _css_escape_identifier(rewritten)
        output.append(
            f"[{match.group('head')}{operator}{match.group('space')}{new_value}{tail}]"
        )
    return output


def _reject_unsafe_reference_selector(
    name: str,
    operator: str,
    value: str,
    case_insensitive: bool,
    id_map: dict[str, str],
) -> None:
    """Reject partial selectors whose matching target changes after ID rebasing."""
    if name not in {"id", "href", *_ARIA_IDREF_ATTRIBUTES}:
        return
    if name in _ARIA_IDREF_ATTRIBUTES:
        raise CompositionError(
            "Cannot safely compose partial CSS attribute selector on ARIA IDREF "
            f"attribute {name!r}"
        )

    def normalize(candidate: str) -> str:
        return candidate.casefold() if case_insensitive else candidate

    needle = normalize(value)

    def matches(candidate: str) -> bool:
        candidate = normalize(candidate)
        if operator == "^=":
            return candidate.startswith(needle)
        if operator == "$=":
            return candidate.endswith(needle)
        if operator == "*=":
            return needle in candidate
        return candidate == needle or candidate.startswith(f"{needle}-")

    candidates = (
        ((f"#{old_id}", f"#{new_id}") for old_id, new_id in id_map.items())
        if name == "href"
        else id_map.items()
    )
    matched_reference = False
    changed_reference = False
    for old, new in candidates:
        if matches(old):
            matched_reference = True
            changed_reference |= old != new
    if changed_reference:
        raise CompositionError(
            "Cannot safely compose partial CSS attribute selector on rewritten "
            f"{name!r} references"
        )
    if name == "href" and "#" in value and not matched_reference:
        raise CompositionError(
            "Cannot safely compose partial CSS attribute selector on local href "
            "references"
        )


def _css_attribute_references(
    id_map: dict[str, str],
    map_fragment: Callable[[str], str],
    value: str,
    case_insensitive: bool,
) -> list[str]:
    if not case_insensitive:
        return [map_fragment(value)]
    folded = value.casefold()
    mapped = list(
        dict.fromkeys(
            new_id for old_id, new_id in id_map.items() if old_id.casefold() == folded
        )
    )
    return mapped or [map_fragment(value)]


def _scope_selector(selector: str, scope_id: str, *, nested: bool) -> str:
    leading = selector[: len(selector) - len(selector.lstrip())]
    trailing = selector[len(selector.rstrip()) :]
    content = selector.strip()
    scope = f"#{_css_escape_identifier(scope_id)}"
    root = f"{scope} > svg"
    content = _rewrite_root_pseudo(content, root)
    if not nested and not content.startswith(scope):
        content = f"{scope} {content}"
    return f"{leading}{content}{trailing}"


def _rewrite_root_pseudo(selector: str, nested_root: str) -> str:
    output: list[str] = []
    index = 0
    while index < len(selector):
        if selector.startswith("/*", index):
            end = _consume_css_comment(selector, index)
            output.append(selector[index:end])
            index = end
            continue
        if selector[index] in "\"'":
            end = _consume_css_string(selector, index)
            output.append(selector[index:end])
            index = end
            continue
        pseudo_end = (
            _consume_css_identifier(selector, index + 1)
            if selector[index] == ":"
            else index
        )
        if (
            pseudo_end > index + 1
            and _css_unescape(selector[index + 1 : pseudo_end]).lower() == "root"
        ):
            joined = "".join(output)
            compound_start = _trailing_compound_start(joined)
            before = joined[:compound_start]
            compound = joined[compound_start:]
            compound = re.sub(
                r"^(?:(?:[-\w*]+)?\|)?(?:svg|\*)",
                "",
                compound,
                flags=re.IGNORECASE,
            )
            output = [before, nested_root, compound]
            index = pseudo_end
            continue
        output.append(selector[index])
        index += 1
    return "".join(output)


def _trailing_compound_start(selector: str) -> int:
    parentheses = 0
    brackets = 0
    index = len(selector) - 1
    while index >= 0:
        char = selector[index]
        if char == "]":
            brackets += 1
        elif char == "[" and brackets:
            brackets -= 1
        elif char == ")" and brackets == 0:
            parentheses += 1
        elif char == "(" and brackets == 0:
            if parentheses:
                parentheses -= 1
            else:
                return index + 1
        elif brackets == parentheses == 0 and (char.isspace() or char in ">+~,"):
            return index + 1
        index -= 1
    return 0


def _split_selector_list(selector: str) -> list[str]:
    parts: list[str] = []
    start = 0
    paren_depth = 0
    bracket_depth = 0
    index = 0
    while index < len(selector):
        if selector.startswith("/*", index):
            index = _consume_css_comment(selector, index)
            continue
        if selector[index] in "\"'":
            index = _consume_css_string(selector, index)
            continue
        char = selector[index]
        if char == "(":
            paren_depth += 1
        elif char == ")" and paren_depth:
            paren_depth -= 1
        elif char == "[":
            bracket_depth += 1
        elif char == "]" and bracket_depth:
            bracket_depth -= 1
        elif char == "," and paren_depth == bracket_depth == 0:
            parts.append(selector[start:index])
            start = index + 1
        index += 1
    parts.append(selector[start:])
    return parts


def _keyframes_keyword_end(css: str, index: int) -> int | None:
    for keyword in ("@-webkit-keyframes", "@keyframes"):
        end = index + len(keyword)
        if css[index:end].lower() == keyword and (
            end == len(css) or not _is_css_name_char(css[end])
        ):
            return end
    return None


def _rewrite_animation_declarations(css: str, keyframe_map: dict[str, str]) -> str:
    replacements: list[tuple[int, int, str]] = []
    index = 0
    while index < len(css):
        if css.startswith("/*", index):
            index = _consume_css_comment(css, index)
            continue
        if css[index] in "\"'":
            index = _consume_css_string(css, index)
            continue
        name_end = _consume_css_identifier(css, index)
        if name_end == index:
            index += 1
            continue
        function_open = _css_function_open_paren(css, index, name_end=name_end)
        if function_open is not None:
            index = _consume_balanced_function(css, function_open)
            continue
        property_name = _css_unescape(css[index:name_end]).lower()
        if property_name not in {
            "animation",
            "animation-name",
            "-webkit-animation",
            "-webkit-animation-name",
        }:
            index = name_end
            continue
        colon = _skip_css_gap(css, name_end)
        if colon >= len(css) or css[colon] != ":":
            index = name_end
            continue
        value_start = colon + 1
        value_end = _consume_declaration_value(css, value_start)
        value = css[value_start:value_end]
        shorthand = property_name in {"animation", "-webkit-animation"}
        rewritten = _rewrite_animation_value(value, keyframe_map, shorthand=shorthand)
        if rewritten != value:
            replacements.append((value_start, value_end, rewritten))
        index = value_end
    return _apply_replacements(css, replacements)


def _rewrite_animation_value(
    value: str, mapping: dict[str, str], *, shorthand: bool
) -> str:
    replacements: list[tuple[int, int, str]] = []
    for item_start, item_end in _top_level_comma_ranges(value):
        candidates: list[tuple[int, int, str, str]] = []
        shorthand_roles: set[str] = set()
        shorthand_name_seen = False
        index = item_start
        while index < item_end:
            if value.startswith("/*", index):
                index = _consume_css_comment(value, index)
                continue
            if value[index].isspace():
                index += 1
                continue
            if value[index] in "\"'":
                end = _consume_css_string(value, index)
                decoded = _css_unescape(value[index + 1 : end - 1])
                if (
                    shorthand
                    and shorthand_name_seen
                    and (decoded in mapping or candidates)
                ):
                    raise CompositionError(
                        "Cannot safely compose ambiguous CSS animation shorthand"
                    )
                if decoded in mapping:
                    candidates.append((index, end, decoded, value[index]))
                if shorthand:
                    shorthand_name_seen = True
                index = end
                continue
            if _starts_css_number(value, index, item_end):
                end = _consume_css_component(value, index, item_end)
                if shorthand:
                    component = value[index:end].lower()
                    if _CSS_TIME_RE.fullmatch(component):
                        role = (
                            "duration" if "duration" not in shorthand_roles else "delay"
                        )
                        shorthand_roles.add(role)
                    elif _CSS_NUMBER_RE.fullmatch(component):
                        shorthand_roles.add("iteration-count")
                index = end
                continue
            end = _consume_css_identifier(value, index)
            if end == index:
                index += 1
                continue
            decoded = _css_unescape(value[index:end])
            function_open = _skip_css_gap(value, end)
            if function_open < item_end and value[function_open] == "(":
                lower = decoded.lower()
                if lower == "var":
                    raise CompositionError(
                        "Cannot safely compose CSS animation using var()"
                    )
                if shorthand and (role := _ANIMATION_FUNCTION_ROLES.get(lower)):
                    shorthand_roles.add(role)
                index = _consume_balanced_function(value, function_open)
                continue
            lower = decoded.lower()
            if shorthand:
                role = _ANIMATION_SHORTHAND_ROLES.get(lower)
                if role is not None and role not in shorthand_roles:
                    shorthand_roles.add(role)
                elif lower in _ANIMATION_NAME_KEYWORDS:
                    if decoded in mapping:
                        raise CompositionError(
                            "Cannot safely compose CSS animation shorthand using "
                            f"reserved keyframe name {decoded!r}"
                        )
                elif not shorthand_name_seen:
                    shorthand_name_seen = True
                    if decoded in mapping:
                        candidates.append((index, end, decoded, ""))
                elif decoded in mapping or candidates:
                    raise CompositionError(
                        "Cannot safely compose ambiguous CSS animation shorthand"
                    )
            elif decoded in mapping and lower not in _ANIMATION_NAME_KEYWORDS:
                candidates.append((index, end, decoded, ""))
            index = end

        if shorthand and len(candidates) > 1:
            raise CompositionError(
                "Cannot safely compose ambiguous CSS animation shorthand"
            )
        for start, end, decoded, quote in candidates:
            alias = mapping[decoded]
            replacement = (
                f"{quote}{_css_escape_string(alias, quote)}{quote}"
                if quote
                else _css_escape_identifier(alias)
            )
            replacements.append((start, end, replacement))
    return _apply_replacements(value, replacements)


def _starts_css_number(value: str, index: int, end: int) -> bool:
    """Return whether a CSS number token starts at *index* (sign and integer
    part optional, per the CSS number grammar)."""
    if value[index] in "+-":
        index += 1
    if index < end and value[index] == ".":
        index += 1
    return index < end and value[index].isdigit()


def _top_level_comma_ranges(value: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    start = 0
    index = 0
    while index < len(value):
        if value.startswith("/*", index):
            index = _consume_css_comment(value, index)
            continue
        if value[index] in "\"'":
            index = _consume_css_string(value, index)
            continue
        if value[index] == "(":
            index = _consume_balanced_function(value, index)
            continue
        if value[index] == ",":
            ranges.append((start, index))
            start = index + 1
        index += 1
    ranges.append((start, len(value)))
    return ranges


def _consume_css_component(value: str, start: int, end: int) -> int:
    index = start + 1
    while index < end and not value[index].isspace() and value[index] not in ",;":
        if value[index] == "(":
            return _consume_balanced_function(value, index)
        index += 1
    return index


def _consume_declaration_value(css: str, start: int) -> int:
    paren_depth = 0
    index = start
    while index < len(css):
        if css.startswith("/*", index):
            index = _consume_css_comment(css, index)
            continue
        if css[index] in "\"'":
            index = _consume_css_string(css, index)
            continue
        if css[index] == "(":
            paren_depth += 1
        elif css[index] == ")" and paren_depth:
            paren_depth -= 1
        elif css[index] in ";}" and paren_depth == 0:
            break
        index += 1
    return index


def _apply_replacements(text: str, replacements: list[tuple[int, int, str]]) -> str:
    if not replacements:
        return text
    chunks: list[str] = []
    cursor = 0
    for start, end, replacement in sorted(replacements):
        if start < cursor:
            continue
        chunks.append(text[cursor:start])
        chunks.append(replacement)
        cursor = end
    chunks.append(text[cursor:])
    return "".join(chunks)


def _rewrite_css_urls(css: str, map_fragment: Callable[[str], str]) -> str:
    output: list[str] = []
    index = 0
    while index < len(css):
        if css.startswith("/*", index):
            end = _consume_css_comment(css, index)
            output.append(css[index:end])
            index = end
            continue
        if css[index] in "\"'":
            end = _consume_css_string(css, index)
            output.append(css[index:end])
            index = end
            continue
        url_open = _css_url_open_paren(css, index)
        if url_open is not None:
            end, replacement = _rewrite_css_url_function(
                css, index, url_open, map_fragment
            )
            if end is not None:
                output.append(replacement)
                index = end
                continue
        output.append(css[index])
        index += 1
    return "".join(output)


def _css_url_open_paren(css: str, index: int) -> int | None:
    if css[index : index + 3].lower() != "url" or (
        index > 0 and _is_css_name_char(css[index - 1])
    ):
        return None
    cursor = _skip_css_gap(css, index + 3)
    return cursor if cursor < len(css) and css[cursor] == "(" else None


def _css_function_open_paren(
    css: str, index: int, *, name_end: int | None = None
) -> int | None:
    """Return a function's opening parenthesis without inspecting its payload."""
    if name_end is None:
        name_end = _consume_css_identifier(css, index)
    if name_end == index:
        return None
    cursor = _skip_css_gap(css, name_end)
    return cursor if cursor < len(css) and css[cursor] == "(" else None


def _rewrite_css_url_function(
    css: str,
    start: int,
    open_paren: int,
    map_fragment: Callable[[str], str],
) -> tuple[int | None, str]:
    cursor = _skip_css_gap(css, open_paren + 1)
    value_start = cursor

    if cursor < len(css) and css[cursor] in "\"'":
        quote = css[cursor]
        content_start = cursor + 1
        end_quote = _consume_css_string(css, cursor) - 1
        if end_quote >= len(css) or css[end_quote] != quote:
            return None, ""
        cursor = _skip_css_gap(css, end_quote + 1)
        if cursor >= len(css) or css[cursor] != ")":
            return None, ""
        value = _css_unescape(css[content_start:end_quote])
        if not value.startswith("#"):
            return cursor + 1, css[start : cursor + 1]
        new_id = map_fragment(value[1:])
        replacement = (
            css[start:content_start]
            + _css_escape_string(f"#{new_id}", quote)
            + css[end_quote : cursor + 1]
        )
        return cursor + 1, replacement

    while cursor < len(css):
        if css[cursor] == ")":
            break
        if css[cursor] == "\\":
            cursor = _consume_css_escape(css, cursor)
        else:
            cursor += 1
    if cursor >= len(css):
        return None, ""

    value_end = cursor
    while value_end > value_start and css[value_end - 1].isspace():
        value_end -= 1
    value = _css_unescape(css[value_start:value_end])
    if not value.startswith("#"):
        return cursor + 1, css[start : cursor + 1]
    new_id = map_fragment(value[1:])
    replacement = (
        css[start:value_start]
        + f"#{_css_escape_url_fragment(new_id)}"
        + css[value_end : cursor + 1]
    )
    return cursor + 1, replacement


def _consume_css_comment(css: str, start: int) -> int:
    end = css.find("*/", start + 2)
    return len(css) if end == -1 else end + 2


def _consume_balanced_function(css: str, open_paren: int) -> int:
    depth = 1
    index = open_paren + 1
    while index < len(css):
        if css.startswith("/*", index):
            index = _consume_css_comment(css, index)
            continue
        if css[index] in "\"'":
            index = _consume_css_string(css, index)
            continue
        if css[index] == "(":
            depth += 1
        elif css[index] == ")":
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    return len(css)


def _skip_css_gap(css: str, start: int) -> int:
    index = start
    while index < len(css):
        if css[index].isspace():
            index += 1
        elif css.startswith("/*", index):
            index = _consume_css_comment(css, index)
        else:
            break
    return index


def _strip_css_comments(css: str) -> str:
    output: list[str] = []
    index = 0
    while index < len(css):
        if css.startswith("/*", index):
            index = _consume_css_comment(css, index)
        else:
            output.append(css[index])
            index += 1
    return "".join(output)


def _consume_css_string(css: str, start: int) -> int:
    quote = css[start]
    index = start + 1
    while index < len(css):
        if css[index] == "\\":
            index = _consume_css_escape(css, index)
        elif css[index] == quote:
            return index + 1
        else:
            index += 1
    return len(css)


def _consume_attribute_selector(css: str, start: int) -> int:
    index = start + 1
    while index < len(css):
        if css.startswith("/*", index):
            index = _consume_css_comment(css, index)
        elif css[index] in "\"'":
            index = _consume_css_string(css, index)
        elif css[index] == "]":
            return index + 1
        else:
            index += 1
    return len(css)


def _consume_css_identifier(css: str, start: int) -> int:
    index = start
    while index < len(css):
        if css[index] == "\\":
            next_index = _consume_css_escape(css, index)
            if next_index == index + 1:
                break
            index = next_index
        elif _is_css_name_char(css[index]):
            index += 1
        else:
            break
    return index


def _consume_css_escape(css: str, start: int) -> int:
    index = start + 1
    if index >= len(css):
        return index
    if css[index] in "\r\n\f":
        if css[index] == "\r" and index + 1 < len(css) and css[index + 1] == "\n":
            return index + 2
        return index + 1
    if css[index] in "0123456789abcdefABCDEF":
        digits = 0
        while (
            index < len(css) and digits < 6 and css[index] in "0123456789abcdefABCDEF"
        ):
            index += 1
            digits += 1
        if index < len(css) and css[index].isspace():
            index += 1
        return index
    return index + 1


def _css_unescape(value: str) -> str:
    output: list[str] = []
    index = 0
    while index < len(value):
        if value[index] != "\\":
            output.append(value[index])
            index += 1
            continue
        escape_end = _consume_css_escape(value, index)
        escaped = value[index + 1 : escape_end]
        if not escaped:
            index = escape_end
            continue
        hex_digits = ""
        for char in escaped[:6]:
            if char in "0123456789abcdefABCDEF":
                hex_digits += char
            else:
                break
        if hex_digits:
            codepoint = int(hex_digits, 16)
            if codepoint == 0 or codepoint > 0x10FFFF:
                output.append("\N{REPLACEMENT CHARACTER}")
            else:
                output.append(chr(codepoint))
        elif escaped[0] not in "\r\n\f":
            output.append(escaped[0])
        index = escape_end
    return "".join(output)


def _css_escape_identifier(value: str) -> str:
    output: list[str] = []
    for index, char in enumerate(value):
        if char == "\0":
            output.append("\N{REPLACEMENT CHARACTER}")
        elif (index == 0 and char.isdigit()) or (
            index == 1 and value.startswith("-") and char.isdigit()
        ):
            output.append(f"\\{ord(char):x} ")
        elif char.isalnum() or char in "-_" or ord(char) >= 0x80:
            output.append(char)
        else:
            output.append(f"\\{char}")
    return "".join(output)


def _css_escape_string(value: str, quote: str) -> str:
    return value.replace("\\", "\\\\").replace(quote, f"\\{quote}")


def _css_escape_url_fragment(value: str) -> str:
    output: list[str] = []
    for char in value:
        if char.isspace() or char in "\"'()\\":
            output.append(f"\\{char}")
        else:
            output.append(char)
    return "".join(output)


def _is_css_name_char(char: str) -> bool:
    return char.isalnum() or char in "-_" or ord(char) >= 0x80
