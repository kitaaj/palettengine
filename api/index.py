"""Vercel serverless entry point for the Palettengine API.

Vercel's Python runtime looks for a literal, top-level, unindented ``app = ...``
assignment in this file (it appears to scan for the pattern rather than execute the
module), so all the loading logic lives in a function and only the final assignment
sits at column 0.

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


def _load_app():
    try:
        from palettengine.server import app as real_app

        return real_app
    except Exception:  # pragma: no cover - startup diagnostic for the Vercel deploy
        # If the real app can't load, expose the reason instead of an opaque 500 so we
        # can see it via the deployed URL. Remove once the deployment is confirmed healthy.
        tb = traceback.format_exc()
        root_listing = sorted(os.listdir(_ROOT))[:60] if os.path.isdir(_ROOT) else []
        cwd_listing = sorted(os.listdir(os.getcwd()))[:60]

        from fastapi import FastAPI

        diag = FastAPI()

        @diag.get("/api/meta")
        @diag.get("/api/{rest:path}")
        def _startup_error(rest: str = "") -> dict[str, object]:
            return {
                "startup_error": tb,
                "file": __file__,
                "root": _ROOT,
                "cwd": os.getcwd(),
                "sys_path_head": sys.path[:6],
                "root_listing": root_listing,
                "cwd_listing": cwd_listing,
            }

        return diag


app = _load_app()

__all__ = ["app"]
