# Deploying the API to Koyeb

The API runs on Koyeb's free instance (0.1 vCPU, 512 MB RAM, Frankfurt or
Washington, D.C.), built from the repo's [`Dockerfile`](../Dockerfile).
The free instance scales to zero after an hour without traffic and wakes in
about 1 to 5 seconds, compared with 30 to 80 seconds on Render's free tier.
The [keep-alive workflow](../.github/workflows/keep-alive.yml) pings it every
20 minutes, so it normally never sleeps at all.

The API has to run in a long-lived container rather than a serverless
function, because `/api/load-date` and `/api/load-dates` run the pipeline in
background threads after the request returns. The instance is as small as
Render's, so loading dates from the dashboard takes about as long as before.

Hugging Face Spaces was the first choice, but free accounts can no longer run
Docker or CPU Gradio Spaces. Only ZeroGPU is free, and it is meant for short
GPU bursts in ML demos rather than an always-on API.

## What is in the repo

| File | Purpose |
|---|---|
| [`Dockerfile`](../Dockerfile) | `python:3.13-slim`, installs `requirements.txt`, runs as a non-root user, serves `uvicorn api.main:app` on `$PORT` (7860 if unset) |
| [`.dockerignore`](../.dockerignore) | Keeps `venv/`, `raw/`, `staging/`, `frontend/`, `.env` and `samknows_sim/archives/` out of the image |
| [`.github/workflows/keep-alive.yml`](../.github/workflows/keep-alive.yml) | Pings `$BACKEND_URL/docs` every 20 minutes |

## One-time setup

1. **Sign up** at [koyeb.com](https://www.koyeb.com) with GitHub. Koyeb may
   ask for a card to verify the account (recent reports mention a temporary
   $29 pre-authorisation hold); the free instance itself is not charged.

2. **Create the service.** Choose *Create Service → Web service → GitHub*,
   install the Koyeb GitHub app for the `goeye-dashboard` repository, and
   pick it. Then set:
   - **Branch:** `main`
   - **Builder:** **Dockerfile** (path `Dockerfile`, no build or run
     command overrides)
   - **Instance:** **Free**, region **Frankfurt** or **Washington, D.C.**
     (whichever is closer to your Neon region)
   - **Ports:** `7860`, protocol HTTP, route path `/`
   - **Health check:** TCP on port 7860 (the default) is enough
   - **Service name:** e.g. `goeye-api`

3. **Add the environment variables** in the same form, under *Environment
   variables*. Use the **Secret** type for the sensitive ones:

   | Name | Value |
   |---|---|
   | `DATABASE_URL` | Neon connection string (pooled `-pooler` host works). Secret |
   | `JWT_SECRET` | Long random string, e.g. `python -c "import secrets; print(secrets.token_hex(32))"`. Reusing the Render value keeps existing sign-ins valid. Secret |
   | `SAMKNOWS_URL` | SamKnows (or simulated SamKnows Worker) base URL, needed for *Load dates* in the dashboard |
   | `SAMKNOWS_USER` | SamKnows user |
   | `SAMKNOWS_PASS` | SamKnows password. Secret |
   | `RAW_RETENTION_DAYS` | Days of raw rows to keep, e.g. `90`; `0` disables pruning |

4. **Deploy.** Koyeb builds the image and starts it; the logs show
   `Uvicorn running on http://0.0.0.0:7860` when it is up. The public URL is
   on the service page, like `https://goeye-api-<org>.koyeb.app`. Open
   `<url>/docs` to check it. Every push to `main` redeploys automatically.

5. **Point the front end at it.** In Vercel, open the project's
   *Settings → Environment Variables*, set `VITE_API_URL` to the Koyeb URL
   (no trailing slash) for Production, then **redeploy**
   (*Deployments → ⋯ → Redeploy*). Vite bakes `VITE_*` values in at build
   time, so the change does nothing until the front end is rebuilt.

6. **Turn on the keep-alive.** In GitHub, open *Settings → Secrets and
   variables → Actions → Variables* and add a repository variable
   `BACKEND_URL` with the same Koyeb URL. Run *Keep API awake* once from the
   Actions tab to confirm it gets an HTTP 200.

## Keeping it running

- GitHub turns off scheduled workflows in a public repo after 60 days without
  commits, which stops both the keep-alive and the nightly SamKnows job.
  Commit something at least every 60 days, or re-enable the workflows from
  the Actions tab when GitHub emails you. Even if pings stop, the API still
  works; the first request after an idle hour just takes a few seconds.
- Files the pipeline writes to `raw/` and `staging/` are lost when the
  instance restarts or scales to zero. That is fine: everything that matters
  is in Neon.

## Checking the image locally

```bash
docker build -t goeye-api .
```

```bash
docker run --rm -p 7860:7860 --env-file .env goeye-api
```

Then open <http://localhost:7860/docs>.

## Fallback: Render

The old Render service still works with the existing `Procfile`
(`uvicorn api.main:app --host 0.0.0.0 --port $PORT`) and the same
environment variables. Its free tier sleeps after 15 minutes idle and takes
30 to 80 seconds to wake. To use it as the main backend, point `BACKEND_URL`
at the Render URL and change the keep-alive schedule to `*/10 * * * *`;
staying awake all month uses nearly all of Render's 750 free instance hours.
