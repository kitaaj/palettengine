# palettengine

A perceptual, accessible color palette generator — a self-contained, improved take on
[Colormind](https://colormind.io). All color reasoning happens in **OKLab/OKLCH**
(perceptually uniform), generation is **deterministic and seedable**, and palettes are
**accessible by construction**.

## Why it's better than the tools it's inspired by

| | palettengine | typical generators |
|---|---|---|
| Color space | OKLCH (perceptually uniform) | RGB / HSL |
| Locks | **Hard** — locked colors return exactly | often drift |
| Palette size | 1–12 colors | fixed 5 |
| Reproducibility | seeded, deterministic | server RNG |
| Accessibility | WCAG contrast matrix, auto-fix, colorblind sim | none |
| Semantics | role assignment (bg/surface/text/primary/…) | anonymous swatches |
| Exports | CSS, SCSS, Tailwind, W3C tokens, JSON, SVG, GPL, ASE | copy hex |
| Explainability | transparent, tunable quality score | black box |

## Install

```bash
python -m pip install -e ".[dev,image,web]"   # library + extraction + server
cd web/frontend && npm install && npm run build
```

## CLI

```bash
palette generate --seed 42                             # reproducible palette
palette generate --base '#3b82f6' --scheme triadic --explain
palette generate --mode ui --roles light --export css > theme.css
palette generate --seed 7 --simulate deutan            # colorblind preview

palette extract photo.jpg --seed 1 --explain           # best-scoring palette from an image
palette extract clip.mp4 --mode ui --roles dark --export tokens

palette serve                                          # web UI + API at :8710
```

## Web UI

`palette serve` → http://127.0.0.1:8710

- Swatch editing with **hard locks**, drag-to-reorder, per-swatch **OKLCH sliders**
- `Space` to generate, `Ctrl+Z`/`Ctrl+Y` undo/redo, **shareable URLs**
- Image/video extraction with source preview and **re-roll**
- **Ambient mode** for videos: a live, glowing palette that follows playback in real
  time (fully client-side; GPU-blurred glow, warm-started OKLab k-means on a 32×18 frame)
- **WCAG contrast grid**, colorblind preview, light/dark **theme previews** from roles
- Export panel (all formats, copy or download), light/dark/system app theme

## JSON API

OpenAPI docs at `/docs`. Highlights:

- `POST /api/generate` — `{scheme, size, locks, seed, mode}` → colors (+ `text_on`),
  score breakdown, contrast matrix, light/dark role maps
- `POST /api/extract` — multipart image/video upload → same payload
- `POST /api/export`, `POST /api/simulate`, `GET /api/meta`
- **Colormind-compatible**: `POST /api/` and `GET /list/` accept existing Colormind
  clients unchanged — with hard locks

## Architecture

```
palettengine/
  color/           # sRGB / linear / OKLab / OKLCH / HSL / hex, WCAG contrast, ΔE
  harmony/         # 7 color-theory schemes + seeded auto
  generate/        # deterministic engine + transparent quality scorer
  accessibility/   # WCAG auto-fix, colorblind (CVD) simulation
  roles/           # semantic role assignment
  export/          # 8 output formats (incl. binary ASE)
  extract/         # image/video -> palette (perceptual k-means + shared scorer)
  cli.py           # palette generate / extract / serve
  server.py        # FastAPI JSON API + static UI + Colormind shims
web/frontend/      # Svelte 5 + Vite + TS SPA
tests/             # pytest + hypothesis (backend), vitest (frontend color math)
```

Design notes in [PLAN.md](PLAN.md).

## Development

```bash
./.venv/Scripts/python -m pytest          # backend: 121 tests
./.venv/Scripts/python -m ruff check .    # lint
./.venv/Scripts/python -m mypy palettengine
cd web/frontend && npm test               # frontend color math vs. reference vectors
cd web/frontend && npm run dev            # Vite dev server (proxies /api to :8710)
```

## License

MIT
