# Deploying Palettengine to Vercel

Palettengine deploys to Vercel as **one project**: the Svelte SPA is served statically
from the CDN, and the FastAPI backend runs as a Python serverless function.

## What works on Vercel

- Generate, export, simulate, roles, contrast, the Colormind-compatible `/api/` + `/list/`
  shims, and the OpenAPI docs at `/docs` — all fast and cheap (pure Python, no heavy deps).
- **Image** extraction (numpy + Pillow).

## Rate limiting

The API is public and unauthenticated by design (no user data, and the Colormind-compatible
shim is meant to be curled directly). To keep it from becoming a cost/abuse vector on Vercel's
metered serverless model, requests are throttled per IP: a generous global default (120/min),
tighter caps on the expensive/abuse-prone routes (`/api/extract` 10/min, `/api/generate` and the
`/api/` shim 30/min each), and an explicit 8MB upload cap on `/api/extract` independent of
Vercel's own body-size limit. Exceeding a limit returns `429`.

Counters are in-process, not backed by a shared store, so on serverless they're per warm
instance rather than a single global count — a real deterrent against naive scripted abuse, not
a hard guarantee against a distributed attacker. If that gap ever matters, swap the limiter's
storage for Redis (e.g. Upstash, which has a Vercel-native free tier).

## What does not (by design)

- **Video extraction** is disabled. Serverless functions can't run ffmpeg reliably and cap
  request bodies at ~4.5 MB. The function sets `PALETTENGINE_NO_VIDEO=1`, so `/api/meta`
  reports `"video": false`, the UI offers image-only upload, and any video upload returns
  `415`. To get video, run the backend on a container host (Render / Fly.io / Railway) and
  point the SPA at it instead.

## Files that make it work

- `api/index.py` — the serverless entry; exposes the FastAPI `app` and forces image-only.
- `requirements.txt` — runtime deps for the function (no imageio/ffmpeg).
- `vercel.json` — builds the SPA, serves `web/frontend/dist`, routes `/api/*`, `/list/*`,
  `/docs`, `/openapi.json` to the function, and bundles the `palettengine` package source.
- `.vercelignore` — keeps the venv, tests, and node_modules out of the upload.

## Deploy

```bash
npm i -g vercel        # once
vercel                 # preview deploy (first run links/creates the project)
vercel --prod          # production
```

Vercel auto-detects `api/index.py` + `requirements.txt` (Python) and runs the
`buildCommand` for the frontend. No dashboard configuration is required; everything is in
`vercel.json`.

### Notes / gotchas

- **First deploy validates the setup.** The config follows Vercel's documented ASGI +
  static pattern, but Vercel's Python builder specifics can shift — if `/api/*` 404s, check
  that the function built (Vercel dashboard → Functions) and that the rewrites resolved.
- **Cold starts**: the first request after idle imports numpy lazily only on `/api/extract`;
  generate/export/simulate stay light.
- **Python version**: Vercel picks a recent Python 3.x automatically. Pin via the project
  settings if you need a specific one.
- Same-origin: the SPA calls `/api/...` on its own domain, so there is no CORS setup and no
  API base URL to configure.
