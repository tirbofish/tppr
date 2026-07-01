# tppr on DigitalOcean Functions (serverless)

> ⚠️ **Status: experimental scaffold.** tppr is a Flask monolith (API + SPA),
> which is *not* a natural fit for FaaS. This deploy wraps the existing Flask
> WSGI app in a single HTTP-triggered function so the whole API runs
> serverlessly without rewriting the blueprints. The repo also has a
> first-class **App Platform** deploy (`uv run launch.py --deploy do`) which is
> the better-fitting DigitalOcean product for this architecture — prefer that
> unless you specifically need per-request serverless scaling.

## What this deploys

A single function `tppr/api` that:

1. Vendored backend source (`backend/src`) + the local `tppr_paper_extractor`
   package + `backend/assets` are copied into the function directory at deploy
   time by `launch.py`.
2. `api.py` is a WSGI adapter: it rebuilds a WSGI environ from the DO Functions
   HTTP event (`__ow_method`, `__ow_path`, `__ow_headers`, `__ow_query`,
   `__ow_body`) and calls the Flask app once per invocation (the app is created
   once and reused across warm invocations).
3. `requirements.txt` is installed remotely on DigitalOcean's Linux build fleet
   (`--remote-build`) so binary wheels (`psycopg2-binary`, `cryptography`,
   `Pillow`) resolve correctly.

The static SPA is **not** bundled by default — host it on DigitalOcean Spaces
CDN (or keep using `tppr.online` / App Platform for the frontend) and point the
frontend's `VITE_BACKEND_URL` at the function's web action URL.

## Prerequisites

- A DigitalOcean account with **Functions** enabled.
- `DIGITALOCEAN_ACCESS_TOKEN` in `.env` (token must include the `function:admin`
  scope). The launcher uses the cached `doctl` in `.doctl/bin/` (or one on PATH)
  and runs `doctl serverless install` + `doctl serverless connect` for you.
- A reachable **Supabase Postgres** database (the function connects on every
  cold start to prepare tables — see caveats).
- A strong `SECRET_KEY` (>= 32 chars) and `SUPABASE_URL`/`VITE_SUPABASE_*` in `.env`.

## Deploy

```bash
uv run launch.py --deploy do-fns
```

What it does:

- authenticates doctl with `DIGITALOCEAN_ACCESS_TOKEN`
- installs/connects the serverless plugin (`doctl serverless install`/`connect`)
- stages a deploy bundle in a temp dir (vendored backend + extractor + assets,
  optionally `frontend/dist` when `DO_FN_SERVE_FRONTEND=1`)
- writes a runtime env file from `.env` (`PRODUCTION=true`, `DATABASE_URL`,
  `SUPABASE_URL`, `SECRET_KEY`, `BACKEND_ALLOWED_ORIGINS`, …)
- runs `doctl serverless deploy <staged> --env <file> --remote-build --verbose-build`

Get the URL afterwards:

```bash
doctl serverless functions get tppr/api --url
```

The web action base looks like
`https://<namespace>.<region>.functions.ondigitalocean.app/tppr/api`.
Set the frontend `VITE_BACKEND_URL` to that base. Requests keep their Flask paths
(e.g. `/api/ping`), so the frontend calls `<base>/api/ping`.

## Environment variables (`.env`)

```
DIGITALOCEAN_ACCESS_TOKEN=dop_v1_your-token
DO_FN_RUNTIME=python:default        # optional; override after `doctl serverless status --languages`
DO_FN_SERVE_FRONTEND=0               # 1 to bundle frontend/dist into the function
SECRET_KEY=<32+ random chars>
SUPABASE_URL=https://your-project.supabase.co
DB_USER=... DB_PASSWORD=... DB_HOST=... DB_PORT=5432 DB_NAME=postgres
BACKEND_ALLOWED_ORIGINS=https://your-frontend.example
SUPABASE_SECRET_KEY=...              # optional, enables Supabase Storage uploads
```

## Serverless caveats

- **Cold-start DB prep:** `initialize_runtime()` connects to Supabase Postgres
  on every cold start to prepare tables. Expect higher latency on cold starts.
- **Rate limiting is best-effort:** `flask-limiter` uses in-memory storage, so
  limits are per warm function instance, not global. Use a shared store
  (`RATELIMIT_STORAGE_URI=redis://...`) if you need global limits.
- **Binary responses** (PDFs, images) are returned base64-encoded; DO Functions
  decodes these when the response `Content-Type` is a binary MIME. If a binary
  endpoint misbehaves, move that asset serving to Spaces.
- **Sessions/cookies:** multiple `Set-Cookie` headers are joined into one header.
- The frontend SPA is intentionally not served from the function by default for
  performance — each asset request would invoke the function otherwise.
