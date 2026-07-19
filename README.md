# palette-generator

A perceptual, accessible color palette generator — a self-contained, improved take on
[Colormind](https://colormind.io). All color reasoning happens in **OKLab/OKLCH** (perceptually
uniform), generation is **deterministic and seedable**, and palettes are **accessible by
construction** (WCAG contrast, colorblind-aware).

See [PLAN.md](PLAN.md) for the full design and roadmap.

## Status

Early development. Done: **Phase 0–4** — color foundation, generation engine + CLI,
accessibility (WCAG auto-fix + colorblind sim), semantic roles, exporters,
image/video extraction, and a **web UI + JSON API** (with Colormind-compatible
endpoints). Next: optional ML scoring layer.

## Layout

```
palette_generator/     # the library
  color/               # sRGB / linear / OKLab / OKLCH / HSL / hex, contrast, ΔE
  harmony/             # color-theory schemes
  generate/            # deterministic engine + transparent quality scorer
  accessibility/       # WCAG auto-fix, colorblind (CVD) simulation
  roles/               # semantic role assignment (primary/bg/text/…)
  export/              # JSON / CSS / SCSS / Tailwind / tokens / SVG / GPL / ASE
  extract/             # image/video -> palette (perceptual k-means + scorer)
  cli.py               # `palette generate` / `palette extract` / `palette serve`
  server.py            # FastAPI JSON API + static UI + Colormind-compatible shims
web/frontend/          # Svelte 5 + Vite SPA (swatches, locks, contrast grid, CVD, export)
tests/                 # pytest + hypothesis
```

## Web UI

```bash
cd web/frontend && npm install && npm run build   # once
palette serve                                     # http://127.0.0.1:8710
```

The JSON API lives under `/api/*` (see `/docs` for OpenAPI). Colormind clients work
as-is against `POST /api/` and `GET /list/` — with the improvement that locked input
colors are returned exactly.

## Examples

```bash
palette generate --seed 42                       # reproducible palette
palette generate --base '#3b82f6' --scheme triadic --explain
palette generate --mode ui --roles light --export css > theme.css
palette generate --seed 7 --simulate deutan      # colorblind preview

palette extract photo.jpg --seed 1 --explain     # best-scoring palette from an image
palette extract photo.jpg --faithful             # most representative colors
palette extract clip.mp4 --mode ui --roles dark --export tokens
```

Image/video extraction needs the extras: `pip install -e ".[image]"` (add `imageio` for video).

## Install (dev)

```bash
python -m pip install -e ".[dev]"
pytest
```

## License

MIT
