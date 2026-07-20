"""FastAPI server: JSON API over the library, plus the built web UI.

Endpoints
---------
- ``POST /api/generate``  — generate a palette (locks, scheme, seed, mode…)
- ``POST /api/extract``   — upload an image/video, get a palette back
- ``POST /api/export``    — serialize a list of hex colors to any export format
- ``POST /api/simulate``  — colorblind-simulate a list of hex colors
- ``GET  /api/meta``      — schemes, formats, CVD kinds, role names
- ``POST /api/``, ``GET /list/`` — Colormind-compatible shims
- ``GET  /``              — the built Svelte UI (when ``web/frontend/dist`` exists)

Run with ``palette serve`` or ``uvicorn palettengine.server:app``.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field

from .accessibility import CVD_KINDS, contrast_matrix, simulate_palette
from .color import contrast_ratio
from .export import BINARY_FORMATS, FORMATS
from .export import export as export_palette
from .generate import generate
from .generate.scorer import score, score_breakdown
from .harmony import SCHEMES
from .model import Color, Palette
from .roles import ROLE_ORDER, assign_roles

__all__ = ["app", "create_app"]

_HEX = r"^#?[0-9a-fA-F]{6}$|^#?[0-9a-fA-F]{3}$"


def _video_enabled() -> bool:
    """Video extraction needs ffmpeg + large uploads, which serverless can't provide.

    Deployments that can't support it (e.g. Vercel) set ``PALETTENGINE_NO_VIDEO=1`` so
    the API advertises image-only and rejects video cleanly instead of crashing.
    """
    return os.getenv("PALETTENGINE_NO_VIDEO", "") == ""


# --------------------------------------------------------------------------- #
# request/response models
# --------------------------------------------------------------------------- #
class GenerateRequest(BaseModel):
    base: str | None = Field(default=None, pattern=_HEX)
    scheme: str = "auto"
    size: int = Field(default=5, ge=1, le=12)
    locks: dict[int, str] = Field(default_factory=dict)
    seed: int | None = None
    mode: Literal["general", "ui"] = "general"
    candidates: int = Field(default=240, ge=1, le=2000)


class HexPaletteRequest(BaseModel):
    colors: list[str] = Field(min_length=1, max_length=16)


class ExportRequest(HexPaletteRequest):
    format: str
    roles_theme: Literal["none", "light", "dark"] = "none"


class SimulateRequest(HexPaletteRequest):
    kind: str


class ColormindRequest(BaseModel):
    model: str = "default"
    input: list[Any] | None = None


# --------------------------------------------------------------------------- #
# serialization helpers
# --------------------------------------------------------------------------- #
def _text_on(color: Color) -> str:
    """Black or white, whichever has the higher WCAG contrast on ``color``."""
    rgb = color.rgb
    black = contrast_ratio((0.0, 0.0, 0.0), rgb)
    white = contrast_ratio((1.0, 1.0, 1.0), rgb)
    return "#000000" if black >= white else "#ffffff"


def _palette_payload(palette: Palette, mode: str = "general") -> dict[str, Any]:
    colors = list(palette)
    return {
        "colors": [
            {
                "hex": c.hex,
                "oklch": [round(v, 4) for v in c.oklch],
                "text_on": _text_on(c),
            }
            for c in colors
        ],
        "score": round(score(colors, mode), 4),
        "breakdown": {k: round(v, 4) for k, v in score_breakdown(colors, mode).items()},
        "contrast": [[round(x, 2) for x in row] for row in contrast_matrix(palette)],
        "roles": {
            theme: {name: color.hex for name, color in assign_roles(palette, theme).items()}
            for theme in ("light", "dark")
        },
    }


def _parse_hexes(hexes: list[str]) -> Palette:
    try:
        return Palette([Color.from_hex(h) for h in hexes])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# --------------------------------------------------------------------------- #
# app factory
# --------------------------------------------------------------------------- #
def create_app() -> FastAPI:
    app = FastAPI(title="palettengine", version="0.2.0")

    @app.post("/api/generate")
    def api_generate(req: GenerateRequest) -> dict[str, Any]:
        try:
            palette = generate(
                base=req.base,
                scheme=req.scheme,
                size=req.size,
                locks=req.locks or None,
                seed=req.seed,
                mode=req.mode,
                candidates=req.candidates,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return _palette_payload(palette, req.mode)

    @app.post("/api/extract")
    async def api_extract(
        file: Annotated[UploadFile, File()],
        size: Annotated[int, Form()] = 5,
        seed: Annotated[int | None, Form()] = None,
        mode: Annotated[Literal["general", "ui"], Form()] = "general",
        faithful: Annotated[bool, Form()] = False,
    ) -> dict[str, Any]:
        try:
            from . import extract as ex
        except ImportError as exc:
            raise HTTPException(
                status_code=501, detail="server lacks the [image] extra"
            ) from exc

        suffix = Path(file.filename or "upload.png").suffix or ".png"
        if ex.is_video_path(suffix) and not _video_enabled():
            raise HTTPException(
                status_code=415,
                detail="video extraction is not available on this deployment; upload an image",
            )
        data = await file.read()
        if not data:
            raise HTTPException(status_code=422, detail="empty upload")
        # extract_* take paths, so buffer the upload to a temp file.
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            fn = ex.extract_video if ex.is_video_path(suffix) else ex.extract_image
            palette = fn(tmp_path, size=size, seed=seed, mode=mode, faithful=faithful)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        finally:
            Path(tmp_path).unlink(missing_ok=True)
        return _palette_payload(palette, mode)

    @app.post("/api/export")
    def api_export(req: ExportRequest) -> Response:
        if req.format not in FORMATS:
            raise HTTPException(status_code=422, detail=f"unknown format {req.format!r}")
        palette = _parse_hexes(req.colors)
        roles = None if req.roles_theme == "none" else assign_roles(palette, req.roles_theme)
        data = export_palette(palette, req.format, roles)
        if req.format in BINARY_FORMATS:
            return Response(
                content=data,
                media_type="application/octet-stream",
                headers={"Content-Disposition": f'attachment; filename="palette.{req.format}"'},
            )
        return PlainTextResponse(str(data))

    @app.post("/api/simulate")
    def api_simulate(req: SimulateRequest) -> dict[str, Any]:
        if req.kind not in CVD_KINDS:
            raise HTTPException(status_code=422, detail=f"unknown CVD kind {req.kind!r}")
        palette = _parse_hexes(req.colors)
        return {"colors": simulate_palette(palette, req.kind).hexes()}

    @app.get("/api/meta")
    def api_meta() -> dict[str, Any]:
        return {
            "schemes": [*sorted(SCHEMES), "auto"],
            "formats": list(FORMATS),
            "cvd_kinds": list(CVD_KINDS),
            "roles": list(ROLE_ORDER),
            "modes": ["general", "ui"],
            "video": _video_enabled(),
        }

    # ------------------------------------------------------------------ #
    # Colormind-compatible shims: POST /api/ and GET /list/
    # ------------------------------------------------------------------ #
    @app.post("/api/")
    async def colormind_api(request: Request) -> dict[str, Any]:
        # Colormind clients send raw JSON without a Content-Type header
        # (`curl --data-binary`), so parse the body ourselves.
        import json as _json

        try:
            req = ColormindRequest.model_validate(_json.loads(await request.body()))
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=422, detail=f"invalid body: {exc}") from exc

        locks: dict[int, str] = {}
        if req.input:
            if len(req.input) > 12:
                raise HTTPException(status_code=422, detail="input too long")
            for i, item in enumerate(req.input):
                if isinstance(item, list) and len(item) == 3:
                    r, g, b = (max(0, min(255, int(v))) for v in item)
                    locks[i] = f"#{r:02x}{g:02x}{b:02x}"
                # anything else ("N") is a free slot
        size = len(req.input) if req.input else 5
        mode = "ui" if req.model == "ui" else "general"
        palette = generate(size=size, locks=locks or None, mode=mode)
        result = [[round(v * 255) for v in c.rgb] for c in palette]
        return {"result": result}

    @app.get("/list/")
    def colormind_list() -> dict[str, Any]:
        return {"result": ["default", "ui"]}

    # ------------------------------------------------------------------ #
    # static frontend (mounted last so /api/* wins)
    # ------------------------------------------------------------------ #
    dist = Path(__file__).resolve().parent.parent / "web" / "frontend" / "dist"
    if dist.is_dir():
        from fastapi.staticfiles import StaticFiles

        app.mount("/", StaticFiles(directory=str(dist), html=True), name="ui")

    return app


app = create_app()
