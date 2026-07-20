"""Turn quantized image colors into a palette.

Two strategies:

- :func:`dominant_from_pixels` — the classic "most representative" colors (largest
  clusters). Faithful to the image, but often makes a mediocre *palette*.
- :func:`palette_from_pixels` — Colormind's insight, reframed: over-cluster the image,
  then randomly assemble many candidate palettes and keep the one the **generation
  scorer** likes best. This reuses ``generate.scorer`` so extracted and generated
  palettes are judged by the same standard of quality.

Over-clustering a low-diversity source (e.g. a two-tone image, or many video frames of
one scene) produces near-identical cluster centers. Both strategies therefore merge
perceptually-equal clusters and, when the source has fewer distinct colors than asked
for, fill the palette out with tints/shades — so the result always has ``size``
*visibly distinct* colors instead of repeated swatches.
"""

from __future__ import annotations

import random

import numpy as np

from ..color import clamp, clamp_oklch_to_gamut, oklab_distance, oklab_to_oklch
from ..generate.scorer import score
from ..model import Color, Palette
from .quantize import srgb_to_oklab

__all__ = ["dominant_from_pixels", "palette_from_pixels"]

# OKLab distance below which two cluster centers count as the same color.
_MERGE_DELTA = 0.025
# Lightness offsets tried (in order) when synthesizing tints/shades to fill a palette.
_L_OFFSETS = (0.16, -0.16, 0.30, -0.30, 0.24, -0.24, 0.40, -0.40)


def _cluster_colors(
    pixels: np.ndarray, k: int, seed: int | None
) -> tuple[list[Color], list[float]]:
    from .quantize import kmeans

    oklab = srgb_to_oklab(np.asarray(pixels, dtype=np.float64))
    centers, weights = kmeans(oklab, k, seed)
    colors = [Color(oklab_to_oklch((float(c[0]), float(c[1]), float(c[2])))) for c in centers]
    return colors, [float(w) for w in weights]


def _merge_similar(
    colors: list[Color], weights: list[float], min_delta: float = _MERGE_DELTA
) -> tuple[list[Color], list[float]]:
    """Collapse near-identical clusters, keeping the heaviest as representative."""
    order = sorted(range(len(colors)), key=lambda i: -weights[i])
    kept: list[Color] = []
    kept_w: list[float] = []
    for i in order:
        for j, k in enumerate(kept):
            if oklab_distance(colors[i].oklab, k.oklab) < min_delta:
                kept_w[j] += weights[i]
                break
        else:
            kept.append(colors[i])
            kept_w.append(weights[i])
    return kept, kept_w


def _pad_to_size(colors: list[Color], size: int, min_delta: float = _MERGE_DELTA) -> list[Color]:
    """Ensure exactly ``size`` distinct colors, adding tints/shades if the source is short."""
    out = list(colors[:size])
    if len(out) >= size:
        return out

    def distinct(c: Color) -> bool:
        return all(oklab_distance(c.oklab, o.oklab) >= min_delta for o in out)

    # Prefer lightness variants of the existing colors (a designer's tints & shades).
    for base in colors:
        L, C, H = base.oklch
        for dl in _L_OFFSETS:
            if len(out) >= size:
                return out
            cand = Color(clamp_oklch_to_gamut((clamp(L + dl, 0.06, 0.97), C, H)))
            if distinct(cand):
                out.append(cand)
    # Last resort (e.g. a single pure color): walk a monochromatic lightness ramp.
    step = 1
    while len(out) < size and colors:
        L, C, H = colors[(step - 1) % len(colors)].oklch
        out.append(Color(clamp_oklch_to_gamut((clamp(L + 0.09 * step, 0.06, 0.97), C, H))))
        step += 1
    return out[:size]


def _weighted_sample(rng: random.Random, weights: list[float], count: int) -> list[int]:
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
    """The most representative colors (largest merged clusters), ordered light-to-dark."""
    k = min(len(pixels), max(size * 2, size + 4))
    colors, weights = _merge_similar(*_cluster_colors(pixels, k, seed))
    ranked = [c for _, c in sorted(zip(weights, colors, strict=True), key=lambda t: -t[0])]
    return Palette(sorted(_pad_to_size(ranked, size), key=lambda c: c.L))


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
    colors, weights = _merge_similar(*_cluster_colors(pixels, k, seed))

    # Too few distinct source colors to choose among: use them all + tints/shades.
    if len(colors) <= size:
        return Palette(sorted(_pad_to_size(colors, size), key=lambda c: c.L))

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
