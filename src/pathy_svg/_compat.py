"""Optional import guards for dependencies that aren't always available."""

from __future__ import annotations

import importlib
from typing import Any


def _lazy_import(module_name: str, extra: str) -> Any:
    """Try to import a module, raising a helpful error if missing."""
    try:
        return importlib.import_module(module_name)
    except ImportError:
        raise ImportError(
            f"{module_name} is required for this feature. "
            f"Install it with: pip install pathy-svg[{extra}]"
        ) from None


def require_cairosvg():
    """Import and return cairosvg, or raise with install instructions."""
    return _lazy_import("cairosvg", "export")


def require_pillow():
    """Import and return PIL, or raise with install instructions."""
    return _lazy_import("PIL", "export")


def require_ipython_display():
    """Import and return IPython.display, or raise with install instructions."""
    return _lazy_import("IPython.display", "full")


def require_click():
    """Import and return click, or raise with install instructions."""
    return _lazy_import("click", "cli")
