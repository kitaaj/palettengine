"""The palette generation engine.

Pipeline (see PLAN.md §5):
    seed -> base hue -> harmony anchors -> sample candidates -> score -> best

Generation is **deterministic**: the same ``seed`` plus the same constraints always
produces the same palette. Locks are **hard** by default — a locked slot is returned
exactly as given (unlike Colormind, whose "locked" colors drift).
"""

from __future__ import annotations

import random

from ..color import OKLCH, clamp, clamp_oklch_to_gamut
from ..harmony import resolve_scheme, scheme_hues
from ..model import Color, Palette
from .scorer import score

__all__ = ["generate", "DEFAULT_CANDIDATES"]

DEFAULT_CANDIDATES = 240

# Lightness envelope per mode: (min, max) OKLab L the ramp spans.
_L_ENVELOPE: dict[str, tuple[float, float]] = {
    "general": (0.35, 0.90),
    "ui": (0.15, 0.97),  # wider, so a dark text + light surface pair is reachable
}


def _normalize_locks(
    locks: dict[int, str] | None, size: int
) -> dict[int, OKLCH]:
    out: dict[int, OKLCH] = {}
    for idx, value in (locks or {}).items():
        if not 0 <= idx < size:
            raise ValueError(f"lock index {idx} out of range for size {size}")
        out[idx] = Color.from_hex(value).oklch if isinstance(value, str) else value
    return out


def _sample(
    rng: random.Random,
    hues: list[float],
    size: int,
    locks: dict[int, OKLCH],
    mode: str,
) -> list[Color]:
    """Draw one candidate palette: a jittered lightness ramp over the hue anchors."""
    lo, hi = _L_ENVELOPE.get(mode, _L_ENVELOPE["general"])
    base_chroma = rng.uniform(0.06, 0.16)

    # Even lightness ramp across the envelope, with a little per-slot jitter.
    if size == 1:
        targets = [rng.uniform(lo, hi)]
    else:
        targets = [lo + (hi - lo) * i / (size - 1) for i in range(size)]

    colors: list[Color] = []
    for i in range(size):
        if i in locks:
            colors.append(Color(locks[i]))
            continue
        L = clamp(targets[i] + rng.uniform(-0.05, 0.05), 0.04, 0.98)
        hue = (hues[i % len(hues)] + rng.uniform(-8.0, 8.0)) % 360.0
        # Taper chroma toward the light/dark extremes (both gamut- and taste-driven).
        taper = 1.0 - abs(L - 0.6) / 0.9
        chroma = max(0.0, base_chroma * taper + rng.uniform(-0.03, 0.03))
        colors.append(Color(clamp_oklch_to_gamut((L, chroma, hue))))
    return colors


def generate(
    *,
    base: str | None = None,
    scheme: str = "auto",
    size: int = 5,
    locks: dict[int, str] | None = None,
    seed: int | None = None,
    mode: str = "general",
    candidates: int = DEFAULT_CANDIDATES,
) -> Palette:
    """Generate a palette.

    Parameters
    ----------
    base:
        Optional base color (hex). Seeds the primary hue and, unless a lock already
        occupies slot 0, is pinned there so it appears in the result.
    scheme:
        A key of :data:`palettengine.harmony.SCHEMES`, or ``"auto"``.
    size:
        Number of colors (>= 1).
    locks:
        Map of ``{index: hex}`` to preserve exactly.
    seed:
        RNG seed for reproducibility. ``None`` uses fresh randomness.
    mode:
        ``"general"`` or ``"ui"`` (widens lightness range and rewards a contrast pair).
    candidates:
        How many candidates to sample before choosing the best.
    """
    if size < 1:
        raise ValueError("size must be >= 1")
    rng = random.Random(seed)

    lock_map = _normalize_locks(locks, size)
    if base is not None and 0 not in lock_map:
        lock_map[0] = Color.from_hex(base).oklch

    # Base hue: explicit base > first locked color > random.
    if base is not None:
        base_hue = Color.from_hex(base).H
    elif lock_map:
        base_hue = lock_map[min(lock_map)][2]
    else:
        base_hue = rng.uniform(0.0, 360.0)

    concrete_scheme = resolve_scheme(scheme, rng)
    hues = scheme_hues(concrete_scheme, base_hue)

    best: list[Color] | None = None
    best_score = float("-inf")
    for _ in range(max(1, candidates)):
        cand = _sample(rng, hues, size, lock_map, mode)
        s = score(cand, mode)
        if s > best_score:
            best, best_score = cand, s

    assert best is not None
    return Palette(best)
