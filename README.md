# palette-generator

A perceptual, accessible color palette generator — a self-contained, improved take on
[Colormind](https://colormind.io). All color reasoning happens in **OKLab/OKLCH** (perceptually
uniform), generation is **deterministic and seedable**, and palettes are **accessible by
construction** (WCAG contrast, colorblind-aware).

See [PLAN.md](PLAN.md) for the full design and roadmap.

## Status

Early development. Done: **Phase 0–2** — color foundation, generation engine + CLI,
accessibility (WCAG auto-fix + colorblind sim), semantic roles, and exporters.
Next: image/video extraction, then the web UI.

## Layout

```
palette_generator/     # the library
  color/               # sRGB / linear / OKLab / OKLCH / HSL / hex, contrast, ΔE
  harmony/             # color-theory schemes
  generate/            # deterministic engine + transparent quality scorer
  accessibility/       # WCAG auto-fix, colorblind (CVD) simulation
  roles/               # semantic role assignment (primary/bg/text/…)
  export/              # JSON / CSS / SCSS / Tailwind / tokens / SVG / GPL / ASE
  cli.py               # `palette generate`
web/                   # FastAPI backend + SPA (later phases)
tests/                 # pytest + hypothesis
```

## Examples

```bash
palette generate --seed 42                       # reproducible palette
palette generate --base '#3b82f6' --scheme triadic --explain
palette generate --mode ui --roles light --export css > theme.css
palette generate --seed 7 --simulate deutan      # colorblind preview
```

## Install (dev)

```bash
python -m pip install -e ".[dev]"
pytest
```

## License

MIT
