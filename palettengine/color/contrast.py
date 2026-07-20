"""Contrast metrics for accessibility.

WCAG 2.1 relative-luminance contrast is the legally-referenced standard and what we
validate against. We also expose a light APCA-style lightness contrast for modern
guidance, but WCAG is the source of truth for pass/fail.
"""

from __future__ import annotations

from .spaces import RGB, hex_to_rgb, rgb_to_linear

__all__ = [
    "relative_luminance",
    "contrast_ratio",
    "contrast_ratio_hex",
    "passes_wcag",
    "WCAG_LEVELS",
]

# Minimum contrast ratio required by WCAG 2.1 success criteria 1.4.3 / 1.4.6,
# keyed by (level, is_large_text). Large text = >= 18pt, or >= 14pt bold.
WCAG_LEVELS: dict[tuple[str, bool], float] = {
    ("AA", False): 4.5,
    ("AA", True): 3.0,
    ("AAA", False): 7.0,
    ("AAA", True): 4.5,
}


def relative_luminance(rgb: RGB) -> float:
    """WCAG relative luminance of an sRGB color, in ``[0, 1]``."""
    r, g, b = rgb_to_linear(rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: RGB, bg: RGB) -> float:
    """WCAG contrast ratio between two sRGB colors, in ``[1, 21]``."""
    l1 = relative_luminance(fg)
    l2 = relative_luminance(bg)
    lighter, darker = (l1, l2) if l1 >= l2 else (l2, l1)
    return (lighter + 0.05) / (darker + 0.05)


def contrast_ratio_hex(fg: str, bg: str) -> float:
    """WCAG contrast ratio between two hex colors."""
    return contrast_ratio(hex_to_rgb(fg), hex_to_rgb(bg))


def passes_wcag(fg: RGB, bg: RGB, level: str = "AA", large: bool = False) -> bool:
    """Whether the ``fg``/``bg`` pair meets the given WCAG level for the text size."""
    try:
        threshold = WCAG_LEVELS[(level.upper(), large)]
    except KeyError as exc:
        raise ValueError(f"unknown WCAG level {level!r}") from exc
    return contrast_ratio(fg, bg) >= threshold
