# Simulated SamKnows feed

The production GoEye pipeline pulled a daily `.tar.gz` export from a SamKnows
server: an HTTP Basic-auth protected directory listing of
`YYYYMMDD-<client>.tar.gz` archives, each containing `deltadata/curr_*.csv`.
This folder recreates that server with synthetic data, so the real pipeline
(`pipeline/run_pipeline.py`) runs unchanged in the public demo.

```
GitHub Actions (daily 00:30 UTC)
  ├─ publish: generate_archive.py ──► Workers KV namespace "ARCHIVES"
  │                                          ▲
  │            Cloudflare Worker (Basic auth, "Index of /") ── serves ──┘
  │                     ▲
  └─ ingest:  run_pipeline.py ── list → download → extract → parse → aggregate → prune
                        │
                        ▼
                  Neon PostgreSQL  ◄── FastAPI backend ◄── dashboard
```

The dashboard's date picker also lists the server's archives (`/api/available-dates`)
and can load any of them on demand through the same pipeline.

## What's in an archive

`generate_archive.py` writes the same files, headers and units as the real export
(RTTs in microseconds, KSA local timestamps) for the 11 demo units seeded by
`seed_demo_data.py`:

- 29 game latency files, social media, video conferencing, DNS v4/v6, disconnections
- ~5,200 rows/day, ~130 KB compressed
- GO outperforms the STC/Mobily "KSA Average", with an evening peak (18:00–24:00)
- About one day in eight has an incident: one operator degrades for a few hours
  (higher failure rates and latency, plus clustered disconnections)
- Deterministic: the same date always produces a byte-identical archive

Archives expire from the server after 120 days (KV TTL set at upload). Raw rows
older than `RAW_RETENTION_DAYS` (default 90) are deleted after each run.
Daily and hourly aggregates are kept indefinitely. This keeps the database well
under Neon's free storage limit.

## Local development

```bash
python samknows_sim/generate_archive.py --days 14          # → samknows_sim/archives/
python samknows_sim/serve_local.py --user demo --password demo
```

In `.env`:

```
SAMKNOWS_URL=http://127.0.0.1:8765/
SAMKNOWS_USER=demo
SAMKNOWS_PASS=demo
```

Then run `python pipeline/run_pipeline.py --days 14`, or load dates from the dashboard.

To test the Worker itself locally (simulated KV, no Cloudflare account needed):

```bash
cd samknows_sim/worker
printf 'SAMKNOWS_USER=demo\nSAMKNOWS_PASS=demo\n' > .dev.vars
npx wrangler@4 kv key put 20261018-goeye-demo.tar.gz --path ../archives/20261018-goeye-demo.tar.gz \
  --binding ARCHIVES --metadata '{"size":130523,"uploaded":"2026-10-19T00:30:00Z"}' --local
npx wrangler@4 dev --port 8787
```

## One-time cloud setup (free tier, no card needed)

Everything runs on the Cloudflare Workers free plan (Workers + Workers KV). The
feed uses ~16 MB of KV's 1 GB and one write per day of the 1,000/day allowance.

1. **Cloudflare**: create a free account, then from `samknows_sim/worker/`:

   ```bash
   npx wrangler@4 login
   npx wrangler@4 kv namespace create ARCHIVES
   ```

   Paste the printed `id` into `wrangler.toml` (replacing
   `REPLACE_WITH_KV_NAMESPACE_ID`) and commit it. It's an identifier, not a secret.
   Then:

   ```bash
   npx wrangler@4 deploy
   npx wrangler@4 secret put SAMKNOWS_USER
   npx wrangler@4 secret put SAMKNOWS_PASS
   ```

   `deploy` prints the server URL, e.g. `https://goeye-samknows.<subdomain>.workers.dev/`.

2. **Cloudflare API token** for CI: Dashboard → My Profile → API Tokens → Create
   token → *Create Custom Token* with the *Account → Workers KV Storage → Edit*
   permission. Note your Account ID (dashboard home → right sidebar).

3. **GitHub repository secrets** (Settings → Secrets and variables → Actions):

   | Secret | Value |
   |--------|-------|
   | `CLOUDFLARE_API_TOKEN` | token from step 2 |
   | `CLOUDFLARE_ACCOUNT_ID` | your account ID |
   | `SAMKNOWS_URL` | Worker URL from step 1 (with trailing `/`) |
   | `SAMKNOWS_USER` / `SAMKNOWS_PASS` | same values as the Worker secrets |
   | `DATABASE_URL` | Neon connection string |

4. **Backend host**: set the same `SAMKNOWS_URL`, `SAMKNOWS_USER` and `SAMKNOWS_PASS`
   environment variables, so the dashboard can list and load server dates.

5. **Backfill**: Actions → *SamKnows daily drop* → Run workflow, with `days` = 30.
   After that the schedule adds one day every night.
