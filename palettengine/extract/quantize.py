"""Perceptual quantization for color extraction.

Pixels are converted to OKLab (vectorized with numpy) and clustered with a seeded
k-means, so grouping happens in a perceptually-uniform space rather than in raw RGB.
The OKLab matrix constants mirror :mod:`palettengine.color.spaces`; they are
duplicated here only so the core color module can stay numpy-free.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import numpy.typing as npt

__all__ = [
    "srgb_to_oklab",
    "kmeans",
    "load_image_pixels",
    "pixels_from_frames",
]

F = npt.NDArray[np.float64]


def _srgb_to_linear(a: F) -> F:
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def srgb_to_oklab(rgb: F) -> F:
    """Convert an ``(..., 3)`` array of sRGB values in ``[0, 1]`` to OKLab."""
    lin = _srgb_to_linear(rgb)
    r, g, b = lin[..., 0], lin[..., 1], lin[..., 2]
    lp = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    mp = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    sp = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = np.cbrt(lp), np.cbrt(mp), np.cbrt(sp)
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return np.stack([L, a, bb], axis=-1)


def _kmeanspp(points: F, k: int, rng: np.random.Generator) -> F:
    """k-means++ seeding for stable, well-spread initial centers."""
    n = len(points)
    first = int(rng.integers(n))
    centers = [points[first]]
    d2 = ((points - points[first]) ** 2).sum(axis=1)
    for _ in range(1, k):
        total = float(d2.sum())
        if total <= 0.0:  # all remaining points coincide
            centers.append(points[int(rng.integers(n))])
            continue
        idx = int(rng.choice(n, p=d2 / total))
        centers.append(points[idx])
        d2 = np.minimum(d2, ((points - points[idx]) ** 2).sum(axis=1))
    return np.array(centers)


def kmeans(
    points: F, k: int, seed: int | None = None, iters: int = 32
) -> tuple[F, F]:
    """Cluster ``points`` (N x D) into ``k`` groups.

    Returns ``(centers, weights)`` where ``weights`` are the fractional cluster sizes.
    Deterministic for a given ``seed``.
    """
    n = len(points)
    if n <= k:
        return points.copy(), np.full(n, 1.0 / max(n, 1))

    rng = np.random.default_rng(seed)
    centers = _kmeanspp(points, k, rng)
    labels = np.zeros(n, dtype=np.int64)
    for _ in range(iters):
        dists = ((points[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        new_labels = dists.argmin(axis=1)
        new_centers = np.array(
            [
                points[new_labels == j].mean(axis=0) if np.any(new_labels == j) else centers[j]
                for j in range(k)
            ]
        )
        converged = np.array_equal(new_labels, labels) and np.allclose(new_centers, centers)
        centers, labels = new_centers, new_labels
        if converged:
            break

    counts = np.array([float(np.sum(labels == j)) for j in range(k)])
    return centers, counts / counts.sum()


def load_image_pixels(path: str, max_dim: int = 128) -> F:
    """Load an image as an ``(N, 3)`` array of sRGB pixels in ``[0, 1]`` (downscaled)."""
    from PIL import Image

    with Image.open(path) as im:
        rgb = im.convert("RGB")
        rgb.thumbnail((max_dim, max_dim))
        arr = np.asarray(rgb, dtype=np.float64) / 255.0
    return arr.reshape(-1, 3)


def _downsize(frame: npt.NDArray[np.generic], max_dim: int) -> F:
    """Strided downscale of one HxWx3 frame to an ``(N, 3)`` sRGB float array."""
    h, w = frame.shape[:2]
    step = max(1, max(h, w) // max_dim)
    small = frame[::step, ::step, :3]
    arr = small.astype(np.float64)
    if np.issubdtype(frame.dtype, np.integer):
        arr /= 255.0
    return arr.reshape(-1, 3)


def pixels_from_frames(
    frames: Iterable[npt.NDArray[np.generic]],
    max_frames: int = 20,
    frame_stride: int = 15,
    max_dim: int = 96,
) -> F:
    """Pool pixels from an iterable of video frames (each an ``HxWx3`` array).

    Streams frames, keeping every ``frame_stride``-th up to ``max_frames``, so memory
    stays bounded regardless of clip length.
    """
    pools: list[F] = []
    for i, frame in enumerate(frames):
        if i % frame_stride:
            continue
        pools.append(_downsize(np.asarray(frame), max_dim))
        if len(pools) >= max_frames:
            break
    if not pools:
        raise ValueError("no frames to sample")
    return np.concatenate(pools, axis=0)
