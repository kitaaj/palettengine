"""Color-vision-deficiency (colorblindness) simulation.

Uses the Machado, Oliveira & Fernandes (2009) matrices at full severity, applied in
**linear** sRGB (the space they are defined for). Simulating CVD lets the UI preview how
a palette looks to protan/deutan/tritan viewers, and lets the scorer later penalize
palettes whose colors collapse together under a deficiency.
"""

from __future__ import annotations

from ..color import RGB, clamp, linear_to_rgb, rgb_to_linear, rgb_to_oklch
from ..model import Color, Palette

__all__ = ["CVD_KINDS", "simulate", "simulate_color", "simulate_palette"]

# Machado et al. (2009), severity 1.0. Row-major 3x3, operating on linear RGB.
_MATRICES: dict[str, tuple[tuple[float, float, float], ...]] = {
    "protan": (
        (0.152286, 1.052583, -0.204868),
        (0.114503, 0.786281, 0.099216),
        (-0.003882, -0.048116, 1.051998),
    ),
    "deutan": (
        (0.367322, 0.860646, -0.227968),
        (0.280085, 0.672501, 0.047413),
        (-0.011820, 0.042940, 0.968881),
    ),
    "tritan": (
        (1.255528, -0.076749, -0.178779),
        (-0.078411, 0.930809, 0.147602),
        (0.004733, 0.691367, 0.303900),
    ),
}

CVD_KINDS: tuple[str, ...] = tuple(_MATRICES)


def simulate(rgb: RGB, kind: str) -> RGB:
    """Simulate how an sRGB color appears under the given deficiency."""
    try:
        m = _MATRICES[kind]
    except KeyError as exc:
        raise ValueError(f"unknown CVD kind {kind!r}; choose from {CVD_KINDS}") from exc
    r, g, b = rgb_to_linear(rgb)
    out = tuple(clamp(row[0] * r + row[1] * g + row[2] * b) for row in m)
    return linear_to_rgb(out)  # type: ignore[arg-type]


def simulate_color(color: Color, kind: str) -> Color:
    return Color(rgb_to_oklch(simulate(color.rgb, kind)))


def simulate_palette(palette: Palette, kind: str) -> Palette:
    return Palette([simulate_color(c, kind) for c in palette])
