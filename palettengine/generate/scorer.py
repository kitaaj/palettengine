"""Deterministic palette-quality scoring.

This is the transparent, no-ML "gatekeeper" (in Colormind's terms). It scores a
candidate palette on a handful of perceptual criteria and returns a weighted sum;
the engine keeps the highest-scoring candidate. An optional ML scorer can later add
another term without changing this interface.

Design notes
------------
- All reasoning is perceptual (OKLab/OKLCH), which is what lets us detect "muddy"
  (too-close) colors and dull (low-spread) palettes — the failure mode Colormind's
  early LSTM had.
- Each term is normalized to roughly ``[0, 1]`` and saturates, so no single term can
  dominate. Weights are explicit and tunable.
"""

from __future__ import annotations

from statistics import mean

from ..color import contrast_ratio, oklab_distance
from ..model import Color

__all__ = ["score", "score_breakdown", "WEIGHTS"]

# Relative weight of each scoring term. Tunable; exposed for experiments and the UI.
WEIGHTS: dict[str, float] = {
    "distinctness": 2.5,  # colors should be perceptually separable (not muddy)
    "lightness_spread": 1.5,  # a good range of light-to-dark (not all mid-tones)
    "chroma_variety": 1.0,  # a mix of vivid and muted, not monotone saturation
    "not_grey": 0.8,  # avoid an accidental all-grey palette
    "contrast": 2.0,  # UI mode only: a usable text/background pair must exist
}


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def score_breakdown(colors: list[Color], mode: str = "general") -> dict[str, float]:
    """Per-term scores (each ~``[0, 1]``) for a palette. Useful for explainability."""
    n = len(colors)
    if n == 0:
        return {}
    labs = [c.oklab for c in colors]
    Ls = [c.L for c in colors]
    Cs = [c.C for c in colors]

    # Distinctness: the closest pair sets the muddiness; target min ΔE ≈ 0.12.
    if n > 1:
        min_d = min(
            oklab_distance(labs[i], labs[j]) for i in range(n) for j in range(i + 1, n)
        )
    else:
        min_d = 1.0
    distinctness = _clamp01(min_d / 0.12)

    # Lightness spread: reward a range approaching ~0.6 in OKLab L.
    lightness_spread = _clamp01((max(Ls) - min(Ls)) / 0.6)

    # Chroma variety: reward a spread between the most muted and most vivid.
    chroma_variety = _clamp01((max(Cs) - min(Cs)) / 0.10)

    # Not-grey: mean chroma should clear a low floor (~0.05) unless deliberately mono.
    not_grey = _clamp01(mean(Cs) / 0.05)

    out = {
        "distinctness": distinctness,
        "lightness_spread": lightness_spread,
        "chroma_variety": chroma_variety,
        "not_grey": not_grey,
    }

    if mode == "ui":
        # Reward the best available text/background contrast, saturating at WCAG AAA (7:1).
        rgbs = [c.rgb for c in colors]
        best_ratio = max(
            (contrast_ratio(rgbs[i], rgbs[j]) for i in range(n) for j in range(i + 1, n)),
            default=1.0,
        )
        out["contrast"] = _clamp01((best_ratio - 1.0) / (7.0 - 1.0))

    return out


def score(colors: list[Color], mode: str = "general") -> float:
    """Weighted total quality score for a palette (higher is better)."""
    return sum(WEIGHTS[k] * v for k, v in score_breakdown(colors, mode).items())
