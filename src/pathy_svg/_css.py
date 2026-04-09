"""Shared CSS inline-style helpers."""

from __future__ import annotations

import re


def style_property(style: str | None, prop: str) -> str | None:
    """Return a CSS property value from an inline style string."""
    if not style:
        return None
    match = re.search(rf"(?:^|;)\s*{re.escape(prop)}\s*:\s*([^;]+)", style)
    return match.group(1).strip() if match else None


def set_style_property(style: str | None, prop: str, value: str) -> str:
    """Set a CSS property in an inline style string, returning the updated style."""
    if not style:
        return f"{prop}:{value}"
    pattern = rf"(?:^|(?<=;))\s*{re.escape(prop)}\s*:\s*[^;]+"
    if re.search(pattern, style):
        return re.sub(pattern, f"{prop}:{value}", style)
    return f"{prop}:{value};{style}"
