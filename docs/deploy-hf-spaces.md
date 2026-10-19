# Deploying the API to Hugging Face Spaces

The API runs as a Docker Space on the free **CPU Basic** hardware
(2 vCPU, 16 GB RAM). A free Space only sleeps after about 48 hours with no
traffic, and the [keep-alive workflow](../.github/workflows/keep-alive.yml)
pings it every 12 hours, so in practice it stays awake and answers in well
under a second. Render's free tier, by contrast, sleeps after 15 minutes and
takes 30 to 80 seconds to wake.

The API has to run in a long-lived container rather than a serverless
function, because `/api/load-date` and `/api/load-dates` run the pipeline in
background threads after the request returns.

## What is in the repo

| File | Purpose |
|---|---|
| [`Dockerfile`](../Dockerfile) | `python:3.13-slim`, installs `requirements.txt`, runs as uid 1000, serves `uvicorn api.main:app` on port 7860 |
| [`.dockerignore`](../.dockerignore) | Keeps `venv/`, `raw/`, `staging/`, `frontend/`, `.env` and `samknows_sim/archives/` out of the image |
| [`docs/hf-space/README.md`](hf-space/README.md) | The Space's own README; its front matter (`sdk: docker`, `app_port: 7860`) tells Hugging Face how to run it |
| [`.github/workflows/keep-alive.yml`](../.github/workflows/keep-alive.yml) | Pings `$BACKEND_URL/docs` every 12 hours |

The repository's main `README.md` is not used by the Space. Hugging Face reads
the Space configuration from the front matter of the `README.md` at the root
of the *Space* repo, so the upload steps below put `docs/hf-space/README.md`
there instead.

## One-time setup

1. **Create the Space.** On huggingface.co choose *New Space*, pick the
   **Docker** SDK with the **Blank** template, hardware **CPU Basic (free)**,
   and visibility **Public**. The dashboard calls the API from the browser,
   and a private Space would need a Hugging Face token on every request.
   The Space URL will be `https://<hf-user>-<space-name>.hf.space`.

2. **Add the secrets.** In the Space, open *Settings → Variables and secrets*
   and add each of these as a **Secret** (not a public variable):

   | Name | Value |
   |---|---|
   | `DATABASE_URL` | Neon connection string (pooled `-pooler` host works) |
   | `JWT_SECRET` | Long random string, e.g. `python -c "import secrets; print(secrets.token_hex(32))"`. Reusing the Render value keeps existing sign-ins valid |
   | `SAMKNOWS_URL` | SamKnows (or simulated SamKnows Worker) base URL, needed for *Load dates* in the dashboard |
   | `SAMKNOWS_USER` | SamKnows user |
   | `SAMKNOWS_PASS` | SamKnows password |
   | `RAW_RETENTION_DAYS` | Days of raw rows to keep, e.g. `90`; `0` disables pruning |

   Secrets are exposed to the container as environment variables, which is
   what `database.py`, `api/main.py` and `pipeline/` read. Changing a secret
   restarts the Space.

3. **Upload the code.** With the Hugging Face CLI
   (`pip install -U huggingface_hub`, then `hf auth login` with a *write*
   token), run from the repo root:

   ```bash
   hf upload <hf-user>/<space-name> . . --repo-type=space --exclude "venv/*" "env/*" ".env" "raw/*" "staging/*" "frontend/*" "samknows_sim/archives/*" ".git/*" "*.log" "README.md"
   ```

   ```bash
   hf upload <hf-user>/<space-name> docs/hf-space/README.md README.md --repo-type=space
   ```

   The Space builds the image and starts it; the *Logs* tab shows the build
   and `Uvicorn running on http://0.0.0.0:7860`. Open
   `https://<hf-user>-<space-name>.hf.space/docs` to check it.
   Re-run the first command whenever the backend changes.

4. **Point the front end at it.** In Vercel, open the project's
   *Settings → Environment Variables*, set `VITE_API_URL` to
   `https://<hf-user>-<space-name>.hf.space` (no trailing slash) for
   Production, then **redeploy** (*Deployments → ⋯ → Redeploy*). Vite bakes
   `VITE_*` values in at build time, so the change does nothing until the
   front end is rebuilt.

5. **Turn on the keep-alive.** In GitHub, open *Settings → Secrets and
   variables → Actions → Variables* and add a repository variable
   `BACKEND_URL` with the same Space URL. Run *Keep API awake* once from the
   Actions tab to confirm it gets an HTTP 200.

## Checking the image locally

```bash
docker build -t goeye-api .
```

```bash
docker run --rm -p 7860:7860 --env-file .env goeye-api
```

Then open <http://localhost:7860/docs>. `--env-file .env` passes the same
variables the Space gets from its secrets.

## Fallback: Render

The old Render service still works with the existing `Procfile`
(`uvicorn api.main:app --host 0.0.0.0 --port $PORT`) and the same
environment variables. Its free tier sleeps after 15 minutes idle, so to use
it as the main backend, point `BACKEND_URL` at the Render URL and change the
keep-alive schedule to `*/10 * * * *`. GitHub may delay scheduled runs, so
expect an occasional cold start. Staying awake all month uses nearly all of
Render's 750 free instance hours.
