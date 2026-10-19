# Deploying the API to Hugging Face Spaces

The API runs as a **Gradio** Space on the free **CPU Basic** hardware
(2 vCPU, 16 GB RAM). Docker Spaces are a paid option, but a Gradio Space only
runs `python app.py` and serves whatever listens on port 7860, so
[`app.py`](../app.py) starts the normal FastAPI app there and mounts a small
Gradio status page at `/ui`.

A free Space sleeps only after about 48 hours with no traffic, and the
[keep-alive workflow](../.github/workflows/keep-alive.yml) pings it every
12 hours, so in practice it stays awake and answers in well under a second.
Render's free tier, by contrast, sleeps after 15 minutes and takes 30 to 80
seconds to wake.

The API has to run in a long-lived process rather than a serverless
function, because `/api/load-date` and `/api/load-dates` run the pipeline in
background threads after the request returns.

## What is in the repo

| File | Purpose |
|---|---|
| [`app.py`](../app.py) | Space entry point: the FastAPI app from `api/main.py`, a status page at `/ui`, `/` redirecting there, served by uvicorn on port 7860 |
| [`docs/hf-space/README.md`](hf-space/README.md) | The Space's own README. Its front matter (`sdk: gradio`, `sdk_version: 6.14.0`, `python_version: "3.12"`, `app_file: app.py`) tells Hugging Face how to run it |
| [`.github/workflows/keep-alive.yml`](../.github/workflows/keep-alive.yml) | Pings `$BACKEND_URL/docs` every 12 hours |
| [`Dockerfile`](../Dockerfile), [`.dockerignore`](../.dockerignore) | Not used by the Gradio Space; ready for any Docker host (a paid Docker Space, Koyeb, Fly) if you move later |

The repository's main `README.md` is not used by the Space. Hugging Face reads
the Space configuration from the front matter of the `README.md` at the root
of the *Space* repo, so the upload steps below put `docs/hf-space/README.md`
there instead.

**Why Gradio 6.14.0:** Gradio 6.15 and later need Starlette 1.x, while the
pinned `fastapi==0.135.1` uses Starlette 0.52. 6.14.0 is the newest release
that installs alongside `requirements.txt` without conflicts. Gradio is not
added to `requirements.txt`; the Space installs it from `sdk_version`. If you
upgrade FastAPI to a Starlette 1.x release later, you can raise
`sdk_version` too.

## One-time setup

1. **Create the Space.** On huggingface.co choose *New Space*, pick the
   **Gradio** SDK with the **Blank** template, hardware **CPU Basic (free)**,
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

   Secrets are exposed to the app as environment variables, which is what
   `database.py`, `api/main.py` and `pipeline/` read. Changing a secret
   restarts the Space.

3. **Upload the code.** Install the Hugging Face CLI and sign in with a
   *write* token (create one under *Settings → Access Tokens*):

   ```bash
   pip install -U huggingface_hub
   ```

   ```bash
   hf auth login
   ```

   Then, from the repo root, upload the code and put the Space README in
   place (the second command overwrites the template's `README.md`):

   ```bash
   hf upload <hf-user>/<space-name> . . --repo-type=space --exclude "venv/*" "env/*" ".env" "raw/*" "staging/*" "frontend/*" "samknows_sim/archives/*" ".git/*" ".idea/*" "*.log" "README.md"
   ```

   ```bash
   hf upload <hf-user>/<space-name> docs/hf-space/README.md README.md --repo-type=space
   ```

   The Space installs `requirements.txt` and Gradio, then runs `app.py`; the
   *Logs* tab shows `Uvicorn running on http://0.0.0.0:7860` when it is up.
   Open `https://<hf-user>-<space-name>.hf.space/docs` to check it. Re-run the
   first command whenever the backend changes.

4. **Point the front end at it.** In Vercel, open the project's
   *Settings → Environment Variables*, set `VITE_API_URL` to
   `https://<hf-user>-<space-name>.hf.space` (no trailing slash) for
   Production, then **redeploy** (*Deployments → ⋯ → Redeploy*). Vite bakes
   `VITE_*` values in at build time, so the change does nothing until the
   front end is rebuilt.

5. **Turn on the keep-alive.** In GitHub, open *Settings → Secrets and
   variables → Actions → Variables* and add a repository variable
   `BACKEND_URL` with the same Space URL. The workflow must be on the default
   branch (`main`) for its schedule to run. Run *Keep API awake* once from
   the Actions tab to confirm it gets an HTTP 200.

## Keeping it running

- GitHub turns off scheduled workflows in a public repo after 60 days without
  commits, which stops both the keep-alive and the nightly SamKnows job.
  Commit something at least every 60 days, or re-enable the workflows from
  the Actions tab when GitHub emails you.
- Files the pipeline writes to `raw/` and `staging/` are lost when the Space
  restarts. That is fine: everything that matters is in Neon.

## Running the Space entry point locally

`app.py` needs Gradio, which is not in `requirements.txt`. In a separate
virtual environment:

```bash
pip install -r requirements.txt gradio==6.14.0
```

```bash
python app.py
```

Then open <http://localhost:7860/docs>. For everyday development keep using
`uvicorn api.main:app` as described in the main README.

## Fallback: Render

The old Render service still works with the existing `Procfile`
(`uvicorn api.main:app --host 0.0.0.0 --port $PORT`) and the same
environment variables. Its free tier sleeps after 15 minutes idle, so to use
it as the main backend, point `BACKEND_URL` at the Render URL and change the
keep-alive schedule to `*/10 * * * *`. GitHub may delay scheduled runs, so
expect an occasional cold start. Staying awake all month uses nearly all of
Render's 750 free instance hours.
