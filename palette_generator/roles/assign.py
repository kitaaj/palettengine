"""Assign semantic UI roles to a palette.

Colormind returns five anonymous swatches; a designer still has to decide which is the
background, which is text, which is the primary accent. This module makes that decision
using lightness and chroma, and guarantees the ``text`` role is readable on ``background``
(via :func:`palette_generator.accessibility.auto_fix`), producing a drop-in light or dark theme.
"""

from __future__ import annotations

from ..accessibility import auto_fix
from ..color import contrast_ratio
from ..model import Color, Palette

__all__ = ["ROLE_ORDER", "assign_roles"]

# Stable output order (drives exporters and UI).
ROLE_ORDER: tuple[str, ...] = (
    "background",
    "surface",
    "text",
    "primary",
    "secondary",
    "accent",
    "muted",
)


def assign_roles(palette: Palette, theme: str = "light") -> dict[str, Color]:
    """Map a palette to named roles for a ``"light"`` or ``"dark"`` theme.

    Small palettes may reuse a color for more than one role; ``text`` is always contrast-
    corrected against the chosen background so it is guaranteed readable.
    """
    if theme not in ("light", "dark"):
        raise ValueError(f"theme must be 'light' or 'dark', got {theme!r}")
    colors = list(palette)
    if not colors:
        raise ValueError("cannot assign roles to an empty palette")

    by_light = sorted(colors, key=lambda c: c.L)
    background = by_light[-1] if theme == "light" else by_light[0]
    # Surface: the next color inward from the background edge (falls back to background).
    surface = (by_light[-2] if len(by_light) > 1 else background) if theme == "light" else (
        by_light[1] if len(by_light) > 1 else background
    )

    # Text: the palette color with the most contrast on the background, made AA-readable.
    text = auto_fix(max(colors, key=lambda c: contrast_ratio(c.rgb, background.rgb)), background)

    # Accents by chroma; prefer mid-lightness colors for primary/secondary so they read
    # as brand colors rather than as the background or text.
    mid = [c for c in colors if 0.30 <= c.L <= 0.80] or colors
    primary = max(mid, key=lambda c: c.C)
    secondary = max((c for c in mid if c is not primary), key=lambda c: c.C, default=primary)
    accent = max(colors, key=lambda c: c.C)
    muted = min(colors, key=lambda c: c.C)

    return {
        "background": background,
        "surface": surface,
        "text": text,
        "primary": primary,
        "secondary": secondary,
        "accent": accent,
        "muted": muted,
    }
