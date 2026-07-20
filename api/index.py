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
import traceback

# Ensure the repo root (which holds the `palettengine` package) is importable.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

# Image-only on serverless (see palettengine.server._video_enabled).
os.environ.setdefault("PALETTENGINE_NO_VIDEO", "1")

try:
    from palettengine.server import app
except Exception:  # pragma: no cover - startup diagnostic for the Vercel deploy
    # If the real app can't load, expose the reason instead of an opaque 500 so we can
    # see it via the deployed URL. Remove once the deployment is healthy.
    _tb = traceback.format_exc()
    _root_listing = sorted(os.listdir(_ROOT))[:60] if os.path.isdir(_ROOT) else []
    _cwd_listing = sorted(os.listdir(os.getcwd()))[:60]
    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/api/meta")
    @app.get("/api/{rest:path}")
    def _startup_error(rest: str = "") -> dict[str, object]:
        return {
            "startup_error": _tb,
            "file": __file__,
            "root": _ROOT,
            "cwd": os.getcwd(),
            "sys_path_head": sys.path[:6],
            "root_listing": _root_listing,
            "cwd_listing": _cwd_listing,
        }


__all__ = ["app"]
