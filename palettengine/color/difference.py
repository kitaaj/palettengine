"""Perceptual color difference.

For our purposes (spacing colors within a palette, matching extracted colors) the
Euclidean distance in OKLab is a good, cheap perceptual metric. We also provide a
hue-weighted variant used by the scorer to reason about OKLCH spacing.
"""

from __future__ import annotations

import math

from .spaces import RGB, OKLab, rgb_to_oklab

__all__ = ["oklab_distance", "delta_e_ok", "rgb_distance"]


def oklab_distance(a: OKLab, b: OKLab) -> float:
    """Euclidean distance between two OKLab colors."""
    return math.dist(a, b)


def delta_e_ok(a: RGB, b: RGB) -> float:
    """Perceptual difference (OKLab ΔE) between two sRGB colors."""
    return oklab_distance(rgb_to_oklab(a), rgb_to_oklab(b))


def rgb_distance(a: RGB, b: RGB) -> float:
    """Naive Euclidean distance in sRGB (not perceptual — for comparison/tests only)."""
    return math.dist(a, b)
