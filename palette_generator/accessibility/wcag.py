"""WCAG contrast tooling: inspect pairs and repair unreadable ones.

``auto_fix`` is the key primitive: given a foreground and a fixed background, it nudges
the foreground's **lightness only** (preserving hue and chroma) to the nearest value that
meets a WCAG target — the minimal perceptual change that makes text readable.
"""

from __future__ import annotations

from ..color import WCAG_LEVELS, clamp_oklch_to_gamut, contrast_ratio
from ..model import Color, Palette

__all__ = ["contrast_matrix", "best_text_color", "auto_fix", "ensure_readable"]

# Lightness-search resolution for auto_fix. 512 steps => < 0.2% L granularity, well
# below 8-bit output precision, while staying instant.
_L_STEPS = 512


def contrast_matrix(palette: Palette) -> list[list[float]]:
    """Full matrix of pairwise WCAG contrast ratios (diagonal is 1.0)."""
    colors = list(palette)
    return [[contrast_ratio(a.rgb, b.rgb) for b in colors] for a in colors]


def best_text_color(bg: Color, candidates: list[Color]) -> Color:
    """The candidate with the highest contrast against ``bg``."""
    if not candidates:
        raise ValueError("candidates must be non-empty")
    return max(candidates, key=lambda c: contrast_ratio(c.rgb, bg.rgb))


def _target_ratio(level: str, large: bool) -> float:
    try:
        return WCAG_LEVELS[(level.upper(), large)]
    except KeyError as exc:
        raise ValueError(f"unknown WCAG level {level!r}") from exc


def auto_fix(fg: Color, bg: Color, level: str = "AA", large: bool = False) -> Color:
    """Return a foreground color meeting the WCAG target against ``bg``.

    Preserves the foreground hue and chroma and moves lightness the least amount needed.
    If the target is unreachable at this hue/chroma (e.g. AAA against a mid-grey), returns
    the maximum-contrast color available — callers can re-check with ``passes_wcag``.
    """
    bg_rgb = bg.rgb
    target = _target_ratio(level, large)
    if contrast_ratio(fg.rgb, bg_rgb) >= target:
        return fg

    L0, C, H = fg.oklch
    feasible: list[tuple[float, Color]] = []
    fallback: tuple[float, Color] | None = None
    for i in range(_L_STEPS + 1):
        L = i / _L_STEPS
        cand = Color(clamp_oklch_to_gamut((L, C, H)))
        ratio = contrast_ratio(cand.rgb, bg_rgb)
        if ratio >= target:
            feasible.append((abs(L - L0), cand))
        if fallback is None or ratio > fallback[0]:
            fallback = (ratio, cand)

    if feasible:
        return min(feasible, key=lambda t: t[0])[1]
    assert fallback is not None
    return fallback[1]


def ensure_readable(
    palette: Palette, bg: Color, level: str = "AA", large: bool = False
) -> Palette:
    """Return a copy of ``palette`` with every color made readable against ``bg``."""
    return Palette([auto_fix(c, bg, level, large) for c in palette])
