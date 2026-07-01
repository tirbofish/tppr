# Deployment

To deploy this project for yourself, you will need the following things: 

- Google Cloud Platform (optional, can try to host yourself but GCP is recommended)
- Supabase Account (again, can be self-hosted, but Supabase is specifically required for auth and db)

## GCP
If you are using Google Cloud Platform, you can easily deploy using the launch script:

```bash
uv run launch.py --deploy gcp
```

It will run you through the steps for deployment, or it might just error out and you will have to debug it :/

## DigitalOcean App Platform

The launcher can deploy to DigitalOcean App Platform:

```bash
uv run launch.py --deploy do
```

What it does:

- downloads `doctl` into `.doctl/` automatically if it is not already on `PATH`
- authenticates using `DIGITALOCEAN_ACCESS_TOKEN` from `.env` when present
- otherwise starts `doctl auth init` in an interactive terminal
- defaults to `DO_DEPLOY_MODE=image`, which builds a Docker image locally, pushes it to DigitalOcean Container Registry, and deploys that image to App Platform
- creates or reuses a DigitalOcean Container Registry automatically
- creates or updates the App Platform app with `doctl apps create --upsert`
- uses `deploy/Dockerfile.digitalocean`, which builds the React frontend and serves it from the Flask backend

Useful `.env` values:

```bash
DIGITALOCEAN_ACCESS_TOKEN=dop_v1_your-token
DO_APP_NAME=tppr
DO_REGION=syd
DO_DEPLOY_MODE=image
DO_REGISTRY_NAME=tppr
DO_REGISTRY_REGION=syd1
DO_REGISTRY_TIER=basic
DO_IMAGE_REPOSITORY=tppr
DOCTL_VERSION=1.123.0 # optional pin; defaults to latest doctl release
SECRET_KEY=a-long-random-production-secret
VITE_SUPABASE_PUBLISHABLE_KEY=your-supabase-publishable-key
```

`DO_DEPLOY_MODE=image` requires Docker to be installed and running locally, but it
does not require DigitalOcean GitHub OAuth. If you prefer DigitalOcean to build
from GitHub, set `DO_DEPLOY_MODE=github` and `DO_APP_REPO=github-owner/repo-name`
after connecting GitHub in the DigitalOcean control panel.

## Other cloud platforms
Host the frontend as a static website:

```bash
cd frontend
bun install
bun run build
```

Then copy the `frontend/dist/` folder.

For the backend, just upload the folder and launch with `uv`. 

> [!NOTE]
> I have not attempted to deploy to any other platform than either local or GCP. If you can pull it off, please update the launch.py script and open a PR, or just open a PR and add instructions and I will change it. 

## DigitalOcean Functions (serverless)

tppr can also deploy to DigitalOcean **Functions** (FaaS) — note this is a
*different product* from App Platform above. Because tppr is a Flask monolith,
the Functions deploy wraps the whole Flask app in a single HTTP-triggered
function via a WSGI adapter (`deploy/functions/`). This is an experimental
path; prefer App Platform (`--deploy do`) unless you need per-request
serverless scaling.

```bash
uv run launch.py --deploy do-fns
```

It stages a function bundle (vendored backend source + the local
`tppr-paper-extractor` package + assets, optionally the built `frontend/dist`),
injects runtime env from `.env`, and runs
`doctl serverless deploy --remote-build`. You need `DIGITALOCEAN_ACCESS_TOKEN`
(with `function:admin` scope) in `.env` and a reachable Supabase Postgres.

See `deploy/functions/README.md` for the full prerequisites, the function URL
retrieval, and serverless caveats (cold-start DB prep, in-memory rate limits,
binary response handling).