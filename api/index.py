"""Vercel serverless entry point for the Palettengine API.

Vercel's Python runtime serves the ASGI ``app`` exported here. All ``/api/*`` (plus the
Colormind-compatible ``/list/`` and the OpenAPI docs) are routed to this function by
``vercel.json``; the static SPA is served from the CDN.

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

from palettengine.server import app  # noqa: E402

__all__ = ["app"]
