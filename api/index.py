"""Vercel serverless entry point for the Palettengine API.

Vercel's Python runtime looks for a literal, top-level, unindented ``app = ...``
assignment in this file (it scans for the pattern rather than executing the module to
resolve names), so the loading logic lives in a function and only the final assignment
sits at column 0.

Serverless can't run ffmpeg or accept large uploads, so video extraction is disabled
here — the API advertises image-only via ``/api/meta`` and rejects video with 415.
"""

from __future__ import annotations

import os
import sys

# Ensure the repo root (which holds the `palettengine` package) is importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Image-only on serverless (see palettengine.server._video_enabled).
os.environ.setdefault("PALETTENGINE_NO_VIDEO", "1")


def _load_app():
    from palettengine.server import app as real_app

    return real_app


app = _load_app()

__all__ = ["app"]
