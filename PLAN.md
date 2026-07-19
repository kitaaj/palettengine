# Palette Generator — Design & Build Plan

An improved, self-contained color palette generator inspired by [Colormind](https://colormind.io),
built as a **Python library + CLI** with a **web UI** on top. Core generation is a **hybrid**:
a deterministic, perceptual color-theory engine as the backbone, with an **optional** learned
model layer added later. No GPU required to ship v1.

---

## 1. How Colormind works (from the source articles)

**Palette generation (`generating-color-palettes-with-deep-learning`)**
- Early attempt used an **LSTM** (sequence model). It "averaged" and produced dull browns/greys
  because the model hedges to avoid being wrong.
- Switched to a **GAN** (modified `pix2pix`) reframed as **color inpainting**: given a partial
  5-color palette, fill in the blanks. This produces *plausible, cohesive* palettes instead of
  averaged ones.
- Trained on **Adobe Color** data + a hand-picked selection of **Dribbble** palettes.
- The **L1 term** in the generator trades off randomness vs. colorfulness (high L1 = less random,
  duller). Final product is an **ensemble** of models with varied hyperparameters.
- Operates in **RGB**, fixed **5-color** palettes.

**Image extraction (`extracting-colors-from-photos-and-video`)**
- Standard tools use **color quantization** (MMCQ / median-cut, k-means). These optimize for
  *perceptual fidelity to the image*, not for *good palettes*, and return only one "answer."
- Colormind uses **generative-MMCQ**: brute-force random candidate palettes, scored by a
  **learned classifier** ("gatekeeper") trained on hand-picked good/bad examples. Good = strong
  inter-color contrast + an overarching theme. Output is RNG-driven → many valid palettes per image.

**API (`api-access`)**
- REST: `POST http://colormind.io/api/` with `{"model":"default"}` → `{"result":[[r,g,b]×5]}`.
- Locking: `{"input":[[44,43,44],[90,83,82],"N","N","N"]}` — `"N"` marks a slot to fill.
- `GET /list/` returns available models; `default` and `ui` always present, others rotate daily.
- **Notably, locked input colors still shift slightly in the output** — locks aren't truly hard.
- Free for personal/non-commercial use only.

---

## 2. Where Colormind falls short (our opportunities)

| Limitation | Our improvement |
|---|---|
| Fixed 5 colors | **Variable palette size** (3–10+) |
| RGB space (perceptually non-uniform) | Work in **OKLCH/OKLab** for uniform lightness/chroma control |
| No accessibility awareness | **WCAG contrast**, guaranteed text/bg pairs, **colorblind** simulation |
| Locks aren't hard | **True hard locks** + soft "nudge" locks as an option |
| No semantic meaning | **Role assignment** (primary/secondary/accent/bg/surface/text) |
| No exports | **CSS vars, Tailwind, design tokens (W3C), SCSS, JSON, SVG, ASE/GPL** |
| No harmony control | User-selectable **harmony** (analogous, complementary, triadic, etc.) |
| Server + daily-rotating models, opaque | **Self-contained, deterministic, explainable**; seedable RNG |
| Commercial use restricted | Our own code → **we set the license** |
| Median-cut extraction | **Perceptual clustering + palette-quality scoring** |

---

## 3. Design goals

1. **Perceptual first** — all reasoning in OKLCH/OKLab; convert to sRGB only at the edges.
2. **Deterministic & seedable** — same seed + constraints → same palette (reproducible; testable).
3. **Constraint-driven** — locks, harmony, contrast targets, and roles are hard/soft constraints
   the engine satisfies, not afterthoughts.
4. **Explainable** — every generated palette can report *why* (harmony type, contrast ratios, roles).
5. **Accessible by construction** — palettes intended for UI ship WCAG-valid pairings.
6. **Library-first** — the engine is a clean Python package; CLI, web API, and UI are thin layers.
7. **ML-optional** — the learned layer is a pluggable *scorer/refiner*, never a hard dependency.

---

## 4. Architecture

```
palette_generator/               # the Python package (the core)
├── color/                       # color primitives & conversions
│   ├── spaces.py                # sRGB ↔ linear ↔ OKLab ↔ OKLCH ↔ HSL, hex
│   ├── difference.py            # ΔE (CIEDE2000 / OKLab distance)
│   └── contrast.py              # WCAG 2.1 ratio + APCA (Lc)
├── harmony/                     # color-theory generators
│   ├── schemes.py               # analogous, complementary, triadic, tetradic, mono, split-comp
│   └── constraints.py           # lock handling, spacing, chroma/lightness ramps
├── generate/                    # the palette engine
│   ├── engine.py                # orchestrates: seed → harmony → constraint-solve → refine
│   ├── scorer.py                # palette-quality scoring (contrast, balance, theme)
│   └── ml/                      # OPTIONAL learned layer (lazy-imported)
│       ├── scorer_model.py      # "gatekeeper" classifier (good/bad palette)
│       └── refiner_model.py     # optional inpainting/refinement model
├── extract/                     # image/video → palette
│   ├── quantize.py              # perceptual k-means / octree in OKLab
│   ├── candidates.py            # generative candidate palettes (MMCQ-style)
│   └── video.py                 # frame sampling + temporal aggregation
├── roles/                       # semantic role assignment
│   └── assign.py                # map palette → primary/secondary/accent/bg/surface/text
├── export/                      # serializers
│   ├── css.py  tailwind.py  tokens.py  scss.py  svg.py  ase.py  json.py
├── accessibility/
│   ├── wcag.py                  # pass/fail, auto-fix to nearest passing color
│   └── cvd.py                   # colorblind (protan/deutan/tritan) simulation
├── cli.py                       # `palette` command
└── api.py                       # optional in-process helpers for the web backend

web/                             # web UI + backend (thin layer over the package)
├── backend/                     # FastAPI app: /generate /extract /export /simulate
└── frontend/                    # SPA (interactive editor)
```

---

## 5. Core engine design

**Color space.** All internal math in **OKLab/OKLCH** (perceptually uniform; lets us control
lightness and chroma independently — impossible cleanly in RGB/HSL). Convert to sRGB/hex only for
I/O, with gamut-clamping (reduce chroma until in-gamut, preserving hue & lightness).

**Generation pipeline** (`engine.py`):
1. **Seed** — from a base color, a harmony choice, an image, a text/mood, or pure RNG (seedable).
2. **Harmony** — place hues per the chosen scheme on the OKLCH hue wheel.
3. **Ramp** — distribute lightness/chroma to guarantee spacing and a coherent theme.
4. **Constraint-solve** — honor **hard locks** exactly; satisfy contrast/role constraints; if the
   requested size > harmony anchors, interpolate/rotate to fill.
5. **Score & refine** — rank candidate variations with `scorer.py` (and the ML scorer if enabled);
   return the best, or N diverse options.

**Scoring** (`scorer.py`, deterministic, no ML needed): weighted sum of
- inter-color perceptual distance (avoid muddy/too-close colors),
- lightness distribution (a good spread, not all mid-tones — fixes the LSTM "dull" failure),
- chroma balance (not all neon, not all grey),
- harmony adherence, and
- (for UI palettes) presence of valid text/bg contrast pairs.

**Hard vs. soft locks.** Unlike Colormind, locked colors are preserved *exactly* by default;
a `soft=True` option allows small nudges when the user wants suggestions to adapt.

---

## 6. Accessibility module

- **WCAG 2.1** contrast ratios + optional **APCA (Lc)** for modern guidance.
- `check(palette)` → matrix of pairwise ratios and pass/fail at AA/AAA for normal/large text.
- `auto_fix(fg, bg, target)` → nudge lightness in OKLCH until the pair passes, minimal visual change.
- **CVD simulation** (`cvd.py`): protanopia/deuteranopia/tritanopia transforms so users can preview
  and so the scorer can penalize palettes that collapse under colorblindness.
- Web UI shows a live contrast grid + a "colorblind preview" toggle.

---

## 7. Image / video extraction

- Downscale, convert to **OKLab**, then cluster (**k-means** or octree) for perceptual grouping.
- **Generative candidates** (`candidates.py`): mirror Colormind's generative-MMCQ — sample many
  candidate palettes from the image's color distribution, then rank with the **same `scorer.py`**
  used for generation (unifies "extracted" and "generated" quality). Seedable → reproducible.
- **Video** (`video.py`): sample keyframes (scene-change or fixed interval), aggregate color
  histograms across frames, then extract as above → one palette representative of the clip.
- Optional: feed the extracted anchors back into the generator as locks to "clean up" a rough
  extraction into a polished palette.

---

## 8. Semantic roles + exports

**Roles** (`roles/assign.py`): given a palette, assign
`background`, `surface`, `primary`, `secondary`, `accent`, `text`, `muted` — chosen by lightness,
chroma, and contrast so the result is directly usable as a UI theme (light *and* dark variants).

**Exports** (each a small serializer):
- **CSS** custom properties, **SCSS** variables
- **Tailwind** config snippet
- **W3C Design Tokens** JSON
- Plain **JSON** / hex list
- **SVG** swatch sheet, **ASE**/**GPL** for Adobe/GIMP

---

## 9. Optional ML layer (phase 2+, pluggable)

Kept optional and lazy-imported so the library never *requires* it.
- **Gatekeeper scorer** — a small classifier (good vs. bad palette), Colormind-style, trained on
  public palette datasets. Plugs into `scorer.py` as an extra term.
- **Refiner** — optional inpainting model (transformer over OKLCH tokens, or a small GAN) for
  "fill the blanks" suggestions, matching Colormind's core trick but in perceptual space and with
  *true* hard locks enforced in post-processing.
- **Data sources**: public palette collections (e.g., open datasets, ColourLovers-style dumps),
  clearly documented for licensing. Training is offline; the shipped artifact is a small model file.

---

## 10. Web UI + backend

**Backend** — **FastAPI** thin layer over the package:
`POST /generate` (harmony, size, locks, seed), `POST /extract` (image/video upload),
`POST /export` (format), `POST /simulate` (CVD), `GET /health`.
Keep a **Colormind-compatible** `/api/` shape too, so existing clients can point at us.

**Frontend** — SPA (React or Svelte) with:
- editable swatch row, per-swatch **lock**, drag-to-reorder, size selector,
- harmony picker, **seed** field (reproducible), "generate variations",
- **contrast grid** + **colorblind preview**, role labels, live **export** panel,
- image/video drop-zone for extraction.

---

## 11. Tech stack

- **Language**: Python 3.11+. Package managed with `pyproject.toml` (uv or Poetry).
- **Core deps**: `numpy`, `Pillow` (images), `imageio`/`av` (video). Color math hand-rolled in
  `color/spaces.py` (no heavy dep needed) or `coloraide` for validation.
- **Backend**: `FastAPI` + `uvicorn`.
- **ML (optional)**: `scikit-learn` (k-means, small classifier) first; `torch` only if we build a
  refiner. Isolated in an extra: `pip install palette-generator[ml]`.
- **Testing**: `pytest`, `hypothesis` (property tests for color round-trips), snapshot tests.
- **Quality**: `ruff` + `mypy`.
- **Frontend**: Vite + React/Svelte + TypeScript.

---

## 12. Phased roadmap

**Phase 0 — Foundation (scaffold)**
- `pyproject.toml`, package skeleton, CI (ruff/mypy/pytest), README.
- `color/spaces.py` with full conversions + property tests (round-trip within ε).

**Phase 1 — Core engine (MVP library)**
- `harmony/schemes.py`, `generate/engine.py`, `generate/scorer.py`, hard locks, variable size.
- `cli.py`: `palette generate --base '#3b82f6' --harmony analogous --size 5 --seed 42`.
- Deterministic output; snapshot tests. **Milestone: usable palettes from the CLI.**

**Phase 2 — Accessibility + roles + exports**
- `accessibility/wcag.py` + `cvd.py`; `roles/assign.py`; all exporters.
- CLI flags for contrast targets and export format. **Milestone: UI-ready themes out of the box.**

**Phase 3 — Image/video extraction**
- `extract/quantize.py`, `candidates.py`, `video.py`, reusing the scorer.
- CLI: `palette extract photo.jpg --size 5`. **Milestone: parity+ with Colormind's image feature.**

**Phase 4 — Web UI + API**
- FastAPI backend + Colormind-compatible endpoint; SPA editor with locks, contrast grid, exports.
- **Milestone: interactive product.**

**Phase 5 — Optional ML layer**
- Assemble/clean a palette dataset; train gatekeeper scorer; (stretch) refiner model.
- Ship as optional extra; A/B against the deterministic scorer. **Milestone: learned quality lift.**

---

## 13. Validation & testing

- **Color correctness**: property-based round-trip tests for every space conversion.
- **Determinism**: same seed+constraints → identical palette (snapshot tests).
- **Accessibility**: assert generated UI palettes meet requested WCAG level; verify `auto_fix`
  produces a passing pair with minimal ΔE.
- **Extraction**: golden-image tests; assert extracted anchors are within ΔE tolerance of known dominant colors.
- **Perceptual sanity**: scorer-vs-human spot checks; guard against the "all mid-tone/dull" failure mode.

---

## 14. Risks & mitigations

- **"Good palette" is subjective** → make the scorer transparent and tunable; expose weights; offer
  diverse options rather than one answer (as Colormind does with RNG).
- **Gamut clamping artifacts** in OKLCH→sRGB → clamp by reducing chroma, preserve hue/lightness; test edges.
- **ML dataset licensing** → prefer clearly-licensed/open palette sources; keep ML optional so the
  core product ships regardless.
- **Scope creep** (video, ASE, APCA) → all are additive; the phased plan keeps a shippable core at Phase 1.

---

## 15. Immediate next steps

1. Scaffold the package (`pyproject.toml`, dirs, CI) — Phase 0.
2. Implement and test `color/spaces.py` (the foundation everything else builds on).
3. Implement `harmony/schemes.py` + `generate/engine.py` for a first CLI palette.
