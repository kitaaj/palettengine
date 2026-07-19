# palette-generator

A perceptual, accessible color palette generator — a self-contained, improved take on
[Colormind](https://colormind.io). All color reasoning happens in **OKLab/OKLCH** (perceptually
uniform), generation is **deterministic and seedable**, and palettes are **accessible by
construction** (WCAG contrast, colorblind-aware).

See [PLAN.md](PLAN.md) for the full design and roadmap.

## Status

Early development. Current: **Phase 0/1** — package scaffold and the color-space foundation.

## Layout

```
palette_generator/     # the library (engine, color math, exports, extraction)
  color/               # sRGB / linear / OKLab / OKLCH / HSL / hex, contrast, ΔE
web/                   # FastAPI backend + SPA (later phases)
tests/                 # pytest + hypothesis
```

## Install (dev)

```bash
python -m pip install -e ".[dev]"
pytest
```

## License

MIT
