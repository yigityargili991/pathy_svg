"""CSS animation injection for animated heatmaps."""

from __future__ import annotations

from lxml import etree

SVG_NS = "http://www.w3.org/2000/svg"


def inject_animation(
    tree: etree._ElementTree,
    nsmap: dict,
    *,
    effect: str = "pulse",
    duration: float = 2.0,
    delay_by: str = "value",
    loop: bool = True,
    data_order: list[str] | None = None,
) -> None:
    """Inject CSS keyframe animations into the SVG. Modifies tree in-place.

    Effects:
        - "pulse": Scale up and down
        - "fade_in": Fade from transparent to opaque
        - "sequential": Appear one by one in order
        - "blink": Toggle visibility
    """
    root = tree.getroot()

    # Find or create <defs>
    defs = root.find(f"{{{SVG_NS}}}defs")
    if defs is None:
        defs = etree.SubElement(root, f"{{{SVG_NS}}}defs")
        root.insert(0, defs)

    iteration = "infinite" if loop else "1"

    if effect == "pulse":
        keyframes = (
            "@keyframes pathy-pulse {"
            "  0%, 100% { transform: scale(1); transform-origin: center; }"
            "  50% { transform: scale(1.05); transform-origin: center; }"
            "}"
        )
        rule = f"animation: pathy-pulse {duration}s ease-in-out {iteration};"

    elif effect == "fade_in":
        keyframes = "@keyframes pathy-fade {  0% { opacity: 0; }  100% { opacity: 1; }}"
        rule = f"animation: pathy-fade {duration}s ease-in {iteration};"

    elif effect == "blink":
        keyframes = (
            "@keyframes pathy-blink {  0%, 100% { opacity: 1; }  50% { opacity: 0.2; }}"
        )
        rule = f"animation: pathy-blink {duration}s step-start {iteration};"

    elif effect == "sequential":
        # Each element gets a staggered delay
        if data_order:
            n = len(data_order)
            keyframes = (
                "@keyframes pathy-seq {"
                "  0% { opacity: 0; }"
                "  10% { opacity: 1; }"
                "  100% { opacity: 1; }"
                "}"
            )
            css_parts = [keyframes]
            for i, eid in enumerate(data_order):
                delay = (i / n) * duration
                css_parts.append(
                    f'[id="{eid}"] {{ animation: pathy-seq {duration}s ease-in {iteration}; '
                    f"animation-delay: {delay:.2f}s; opacity: 0; }}"
                )
            style = etree.SubElement(defs, f"{{{SVG_NS}}}style")
            style.text = "\n".join(css_parts)
            return
        else:
            keyframes = (
                "@keyframes pathy-seq {"
                "  0% { opacity: 0; }"
                "  10% { opacity: 1; }"
                "  100% { opacity: 1; }"
                "}"
            )
            rule = f"animation: pathy-seq {duration}s ease-in {iteration};"
    else:
        raise ValueError(f"Unknown animation effect: {effect!r}")

    # Apply to all colorable elements with fill set
    css = f"{keyframes}\npath, rect, circle, ellipse, polygon {{ {rule} }}"
    style = etree.SubElement(defs, f"{{{SVG_NS}}}style")
    style.text = css
