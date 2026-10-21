# Deploying the API to Render

The API runs on Render's free web service, started from the repo's
[`Procfile`](../Procfile) (`uvicorn api.main:app --host 0.0.0.0 --port $PORT`).
Render's free tier needs no card, but it puts a service to sleep after
15 minutes without incoming requests, and waking it takes 30 to 80 seconds.
An external pinger hits the API every 10 minutes so it never gets that far.

The API has to run in a long-lived process rather than a serverless
function, because `/api/load-date` and `/api/load-dates` run the pipeline in
background threads after the request returns.

## Render service settings

| Setting | Value |
|---|---|
| Type | Web service from the GitHub repo, branch `main` |
| Runtime | Python; build command `pip install -r requirements.txt`, start command from the `Procfile` |
| Instance | Free |
| Environment | `DATABASE_URL`, `JWT_SECRET`, `SAMKNOWS_URL`, `SAMKNOWS_USER`, `SAMKNOWS_PASS`, `RAW_RETENTION_DAYS` (see [`.env.example`](../.env.example)) |

Every push to `main` redeploys automatically. Expect one cold start right
after each deploy; the next ping wakes it again.

On Vercel, `VITE_API_URL` must point at the Render URL
(`https://<service>.onrender.com`, no trailing slash). Vite bakes `VITE_*`
values in at build time, so redeploy the front end after changing it.

## Keeping it awake

### cron-job.org (main pinger)

[cron-job.org](https://cron-job.org) is free, needs no card, and fires on
time, which matters with a 15-minute window.

1. Sign up and choose *Create cronjob*.
2. **URL:** `https://<service>.onrender.com/docs`
3. **Schedule:** every 10 minutes.
4. Save, then check the job's history after a few runs: each entry should be
   HTTP 200.

`/docs` is a small static page that doesn't touch the database, so the pings
cost Neon nothing.

### GitHub Actions (backup)

[`keep-alive.yml`](../.github/workflows/keep-alive.yml) pings
`$BACKEND_URL/docs` every 10 minutes as a second line of defence. GitHub
often runs scheduled workflows late, so it isn't reliable enough on its own.
To turn it on, add a repository variable `BACKEND_URL` with the Render URL
under *Settings → Secrets and variables → Actions → Variables*, then run
*Keep API awake* once from the Actions tab. Without the variable the job
skips the ping and shows a warning. The repo is public, so these runs use no
Actions minutes.

### Limits to know

- Render gives each account 750 free instance hours a month, shared by all
  free services in the account. One service awake all month uses about 744,
  so this only works while the API is the only free service running there.
  If the hours run out, Render suspends the service until the next month.
- GitHub turns off scheduled workflows in a public repo after 60 days
  without commits, which stops the backup ping and the nightly SamKnows job.
  Re-enable them from the Actions tab when GitHub emails you.
- Files the pipeline writes to `raw/` and `staging/` are lost when the
  service restarts. That is fine: everything that matters is in Neon.

## Moving to a Docker host later

The repo also has a [`Dockerfile`](../Dockerfile) (`python:3.13-slim`,
non-root user, serves on `$PORT`, 7860 if unset) and a
[`.dockerignore`](../.dockerignore), for hosts that build from a Dockerfile,
such as Koyeb, Fly.io or a paid Hugging Face Space. Koyeb's free instance
wakes in 1 to 5 seconds instead of 30 to 80, but it now asks for a card to
verify the account. To check the image locally:

```bash
docker build -t goeye-api .
```

```bash
docker run --rm -p 7860:7860 --env-file .env goeye-api
```

Then open <http://localhost:7860/docs>.
