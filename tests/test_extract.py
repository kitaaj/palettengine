"""Tests for image/video color extraction (synthetic inputs, no codecs needed)."""

from __future__ import annotations

import numpy as np
import pytest

from palette_generator.color import delta_e_ok, hex_to_rgb
from palette_generator.extract import (
    dominant_from_pixels,
    is_video_path,
    palette_from_pixels,
    pixels_from_frames,
)
from palette_generator.extract.quantize import kmeans, srgb_to_oklab

RNG = np.random.default_rng(0)


def _blob(hex_color: str, n: int) -> np.ndarray:
    """A cluster of pixels near a target sRGB color."""
    base = np.array(hex_to_rgb(hex_color))
    noise = RNG.normal(0.0, 0.01, size=(n, 3))
    return np.clip(base + noise, 0.0, 1.0)


def _three_color_image() -> np.ndarray:
    return np.concatenate(
        [_blob("#e63946", 500), _blob("#457b9d", 500), _blob("#f1faee", 500)]
    )


# --------------------------------------------------------------------------- #
# conversions & kmeans
# --------------------------------------------------------------------------- #
def test_srgb_to_oklab_matches_scalar_reference() -> None:
    from palette_generator.color import rgb_to_oklab

    rgb = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.2, 0.4, 0.7]])
    got = srgb_to_oklab(rgb)
    for i in range(3):
        assert tuple(got[i]) == pytest.approx(rgb_to_oklab(tuple(rgb[i])), abs=1e-9)


def test_kmeans_recovers_separated_clusters() -> None:
    pts = np.concatenate([_blob("#ff0000", 300), _blob("#00ff00", 300), _blob("#0000ff", 300)])
    oklab = srgb_to_oklab(pts)
    centers, weights = kmeans(oklab, 3, seed=1)
    assert len(centers) == 3
    assert weights.sum() == pytest.approx(1.0)
    # Each cluster gets roughly a third of the weight.
    assert all(0.2 < w < 0.45 for w in weights)


def test_kmeans_deterministic() -> None:
    oklab = srgb_to_oklab(_three_color_image())
    a, _ = kmeans(oklab, 4, seed=7)
    b, _ = kmeans(oklab, 4, seed=7)
    assert np.array_equal(a, b)


def test_kmeans_handles_fewer_points_than_k() -> None:
    pts = srgb_to_oklab(_blob("#123456", 2))
    centers, weights = kmeans(pts, 5, seed=0)
    assert len(centers) == 2
    assert weights.sum() == pytest.approx(1.0)


# --------------------------------------------------------------------------- #
# palette extraction
# --------------------------------------------------------------------------- #
def test_palette_from_pixels_size_and_determinism() -> None:
    px = _three_color_image()
    a = palette_from_pixels(px, size=5, seed=3).hexes()
    b = palette_from_pixels(px, size=5, seed=3).hexes()
    assert len(a) == 5
    assert a == b


def test_palette_sorted_by_lightness() -> None:
    px = _three_color_image()
    pal = palette_from_pixels(px, size=5, seed=3)
    lights = [c.L for c in pal]
    assert lights == sorted(lights)


def test_faithful_extraction_recovers_source_colors() -> None:
    px = _three_color_image()
    pal = dominant_from_pixels(px, size=3, seed=0)
    targets = [hex_to_rgb(h) for h in ("#e63946", "#457b9d", "#f1faee")]
    # Every source color should be close to some extracted color.
    for t in targets:
        assert min(delta_e_ok(t, c.rgb) for c in pal) < 0.08


def test_all_extracted_colors_in_gamut() -> None:
    from palette_generator.color import in_gamut

    for c in palette_from_pixels(_three_color_image(), size=6, seed=2):
        assert in_gamut(c.rgb)


# --------------------------------------------------------------------------- #
# video frame pooling
# --------------------------------------------------------------------------- #
def test_pixels_from_frames_streams_and_bounds() -> None:
    frames = [np.full((40, 40, 3), v, dtype=np.uint8) for v in range(0, 250, 5)]
    pooled = pixels_from_frames(frames, max_frames=3, frame_stride=15, max_dim=8)
    assert pooled.shape[1] == 3
    assert pooled.max() <= 1.0  # normalized from uint8


def test_pixels_from_frames_empty_raises() -> None:
    with pytest.raises(ValueError):
        pixels_from_frames([], max_frames=3)


def test_is_video_path() -> None:
    assert is_video_path("clip.MP4")
    assert not is_video_path("photo.png")
