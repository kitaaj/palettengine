"""Accessibility: WCAG contrast tooling and colorblind (CVD) simulation."""

from .cvd import CVD_KINDS, simulate, simulate_color, simulate_palette
from .wcag import auto_fix, best_text_color, contrast_matrix, ensure_readable

__all__ = [
    "CVD_KINDS",
    "auto_fix",
    "best_text_color",
    "contrast_matrix",
    "ensure_readable",
    "simulate",
    "simulate_color",
    "simulate_palette",
]
