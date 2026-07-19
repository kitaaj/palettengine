"""Harmony schemes as hue offsets (in degrees) around a base hue on the OKLCH wheel.

A scheme yields a small set of hue *anchors*; the engine distributes the requested
number of colors across those anchors with lightness/chroma ramps. Working on the
OKLCH hue wheel (rather than HSL) keeps perceived hue relationships even.
"""

from __future__ import annotations

import random

__all__ = ["SCHEMES", "resolve_scheme", "scheme_hues"]

# Hue offsets from the base hue, in degrees.
SCHEMES: dict[str, list[float]] = {
    "monochromatic": [0.0],
    "analogous": [-30.0, 0.0, 30.0],
    "complementary": [0.0, 180.0],
    "split_complementary": [0.0, 150.0, 210.0],
    "triadic": [0.0, 120.0, 240.0],
    "tetradic": [0.0, 60.0, 180.0, 240.0],
    "square": [0.0, 90.0, 180.0, 270.0],
}

# Schemes "auto" may resolve to, and their relative selection weight.
_AUTO_CHOICES: list[tuple[str, float]] = [
    ("analogous", 3.0),
    ("complementary", 2.0),
    ("triadic", 1.5),
    ("split_complementary", 1.5),
    ("monochromatic", 1.0),
    ("tetradic", 1.0),
    ("square", 1.0),
]


def resolve_scheme(scheme: str, rng: random.Random) -> str:
    """Resolve ``"auto"`` to a concrete scheme (seeded); pass others through."""
    if scheme == "auto":
        names = [n for n, _ in _AUTO_CHOICES]
        weights = [w for _, w in _AUTO_CHOICES]
        return rng.choices(names, weights=weights, k=1)[0]
    if scheme not in SCHEMES:
        raise ValueError(f"unknown scheme {scheme!r}; choose from {sorted(SCHEMES)} or 'auto'")
    return scheme


def scheme_hues(scheme: str, base_hue: float) -> list[float]:
    """Absolute hue anchors (degrees, ``[0, 360)``) for a concrete scheme."""
    if scheme not in SCHEMES:
        raise ValueError(f"unknown scheme {scheme!r}")
    return [(base_hue + off) % 360.0 for off in SCHEMES[scheme]]
