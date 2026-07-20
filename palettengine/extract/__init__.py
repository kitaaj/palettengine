"""Extract palettes from images and video.

Requires the ``[image]`` extra (numpy, Pillow); video also needs ``imageio``.
"""

from __future__ import annotations

from ..model import Palette
from .quantize import load_image_pixels, pixels_from_frames
from .select import dominant_from_pixels, palette_from_pixels

__all__ = [
    "extract_image",
    "extract_video",
    "palette_from_pixels",
    "dominant_from_pixels",
    "load_image_pixels",
    "pixels_from_frames",
    "is_video_path",
]

VIDEO_SUFFIXES = (".mp4", ".mov", ".mkv", ".avi", ".webm", ".gif", ".m4v")


def extract_image(
    path: str,
    size: int = 5,
    seed: int | None = None,
    mode: str = "general",
    faithful: bool = False,
    candidates: int = 300,
) -> Palette:
    """Extract a palette from an image file."""
    pixels = load_image_pixels(path)
    if faithful:
        return dominant_from_pixels(pixels, size, seed)
    return palette_from_pixels(pixels, size, seed, mode, candidates=candidates)


def extract_video(
    path: str,
    size: int = 5,
    seed: int | None = None,
    mode: str = "general",
    faithful: bool = False,
    max_frames: int = 20,
    candidates: int = 300,
) -> Palette:
    """Extract a single representative palette from a video clip."""
    import imageio.v3 as iio

    pixels = pixels_from_frames(iio.imiter(path), max_frames=max_frames)
    if faithful:
        return dominant_from_pixels(pixels, size, seed)
    return palette_from_pixels(pixels, size, seed, mode, candidates=candidates)


def is_video_path(path: str) -> bool:
    return path.lower().endswith(VIDEO_SUFFIXES)
