"""Turn quantized image colors into a palette.

Two strategies:

- :func:`dominant_from_pixels` — the classic "most representative" colors (largest
  clusters). Faithful to the image, but often makes a mediocre *palette*.
- :func:`palette_from_pixels` — Colormind's insight, reframed: over-cluster the image,
  then randomly assemble many candidate palettes and keep the one the **generation
  scorer** likes best. This reuses ``generate.scorer`` so extracted and generated
  palettes are judged by the same standard of quality.
"""

from __future__ import annotations

import random

import numpy as np

from ..color import oklab_to_oklch
from ..generate.scorer import score
from ..model import Color, Palette
from .quantize import srgb_to_oklab

__all__ = ["dominant_from_pixels", "palette_from_pixels"]


def _cluster_colors(
    pixels: np.ndarray, k: int, seed: int | None
) -> tuple[list[Color], list[float]]:
    from .quantize import kmeans

    oklab = srgb_to_oklab(np.asarray(pixels, dtype=np.float64))
    centers, weights = kmeans(oklab, k, seed)
    colors = [Color(oklab_to_oklch((float(c[0]), float(c[1]), float(c[2])))) for c in centers]
    return colors, [float(w) for w in weights]


def _weighted_sample(
    rng: random.Random, weights: list[float], count: int
) -> list[int]:
    """Sample ``count`` distinct indices without replacement, proportional to weight."""
    idxs = list(range(len(weights)))
    w = list(weights)
    chosen: list[int] = []
    for _ in range(min(count, len(idxs))):
        total = sum(w)
        r = rng.uniform(0.0, total)
        acc = 0.0
        for pos, wi in enumerate(w):
            acc += wi
            if acc >= r:
                chosen.append(idxs.pop(pos))
                w.pop(pos)
                break
    return chosen


def dominant_from_pixels(
    pixels: np.ndarray, size: int = 5, seed: int | None = None
) -> Palette:
    """The ``size`` largest perceptual clusters, ordered light-to-dark."""
    colors, weights = _cluster_colors(pixels, size, seed)
    ranked = [c for _, c in sorted(zip(weights, colors, strict=True), key=lambda t: -t[0])]
    return Palette(sorted(ranked[:size], key=lambda c: c.L))


def palette_from_pixels(
    pixels: np.ndarray,
    size: int = 5,
    seed: int | None = None,
    mode: str = "general",
    oversample: int = 4,
    candidates: int = 300,
) -> Palette:
    """Extract a high-quality palette by scoring many candidate selections."""
    rng = random.Random(seed)
    k = min(len(pixels), max(size * oversample, size + 4))
    colors, weights = _cluster_colors(pixels, k, seed)

    best: list[Color] | None = None
    best_score = float("-inf")
    for _ in range(max(1, candidates)):
        picked = _weighted_sample(rng, weights, size)
        cand = [colors[i] for i in picked]
        s = score(cand, mode)
        if s > best_score:
            best, best_score = cand, s

    assert best is not None
    return Palette(sorted(best, key=lambda c: c.L))
