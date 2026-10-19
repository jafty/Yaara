# Railway deployment

This repository contains the Railway build and deployment configuration. A Git push triggers deployment when the Railway service is connected to `jafty/Yaara`, watches `codex/yaara-deployment`, and has automatic deployments enabled. Repository configuration alone does not prove that a deployment is live.

## Web and PostgreSQL

1. Connect the Railway service to `jafty/Yaara`, select the `codex/yaara-deployment` branch and enable automatic deployments, using the repository root. `railway.toml` selects the Dockerfile. If Railway waits for CI, deployment starts only after the checks succeed.
2. Add PostgreSQL 17. Set the web service's `DATABASE_URL` to its Railway reference, for example `${{Postgres.DATABASE_URL}}` (adapt the service name).
3. Configure these variables:

| Variable | Value |
| --- | --- |
| `DEBUG` | `0` |
| `SECRET_KEY` | A new long random secret; keep it stable across deployments |
| `DATABASE_URL` | Reference to the PostgreSQL service |
| `ALLOWED_HOSTS` | Custom public hostname without scheme, if applicable |
| `CSRF_TRUSTED_ORIGINS` | `https://your-custom-domain`, if applicable |
| `SIGNUP_ENABLED` | `1` initially; optionally `0` after creating your account |
| `WEB_CONCURRENCY` | `2` initially |

Railway's `RAILWAY_PUBLIC_DOMAIN` is automatically allowed and trusted. The start script honors `PORT`. Generate a secret locally with `python -c 'import secrets; print(secrets.token_urlsafe(64))'` and enter it in Railway variables, not a committed file.

4. Generate the public domain. The build installs pinned, checksum-verified dependencies and compiles French and English catalogs and collects static assets. Pre-deploy runs `python manage.py migrate --noinput`; Gunicorn runs as a non-root user. `/health/` checks database connectivity.
The compiled translation catalogs are included in Git and the Docker image. The report-content schema migration runs through the existing pre-deploy command; no manual translation compilation is needed on Railway.

5. Open the domain, register, and create a **manual V1** game. This mode requires no scheduler. Accounts, sessions, games and reports persist in PostgreSQL; the web container requires no volume.

Railway terminates HTTPS. Django trusts its forwarded HTTPS header and uses HTTPS redirects and secure cookies. Direct public container hosting requires a trusted TLS reverse proxy.

## Automatic calendar with Railway cron

The web service serves pages; a separate cron service closes due Moons using server time and the UTC deadlines stored in PostgreSQL. No browser must remain open. Reloading reads the persisted result; the countdown is informational and does not execute a turn. The existing browser refresh notice also preserves unfinished forms.

1. Keep the existing web service and PostgreSQL database. Deploy the web migrations first.
2. Add a second Railway service from **the same `jafty/Yaara` repository**, watching **`codex/yaara-deployment`**. Set its config file path to **`/railway.cron.toml`**. This file selects the Dockerfile, runs **`python manage.py tick_due`**, schedules **`*/5 * * * *`** (every five minutes, UTC), and disables automatic restart after the one-shot command exits.
3. Give the cron service `DATABASE_URL` referencing **the same PostgreSQL service** as the web app, the same stable `SECRET_KEY`, and `DEBUG=0`. It needs no domain, volume, web start command, or HTTP health check. Remove any inherited web health-check setting and any manually overridden start command. Verify the resulting cron schedule and start command in Railway's service settings after deployment.
4. If the continuous `run_scheduler` worker was previously enabled, stop it after the cron service is configured. Locks and tick records prevent duplicate resolution, but one scheduler is easier to operate.
5. Create an **Automatic** reign; ten-minute Moons are recommended for a five-minute cron. New reigns wait during the prologue. Press **Commencer le règne / Begin the reign** to establish the first deadline. Manual games stay manual; this deployment does not convert or rebalance existing games.
6. Check the cron execution logs after a deadline. Each processed game logs its UUID and `resolved`, or `unchanged or paused`. Reload Council: the open Moon should advance once, reports should carry the closed Moon, and the next deadline should advance from its prior value. Run the cron service manually once to verify its connection; an early run must leave the Moon unchanged.

Railway cron execution times are approximate. A deadline at 12:03 UTC may be processed around 12:05; orders close at 12:03 even while the cron job is pending. Five-minute games can work, but startup delay is more visible. Do not describe browser time as authoritative or allow a client clock to authorize a late order.

After a delay **greater than one full game interval**, the existing protection pauses the game and records a calendar report rather than consuming unattended decision windows. Resume it in Council to open a fresh interval. If games stop advancing, inspect cron executions, database connectivity, the chosen mode, pause state, and deployment/migration errors. A completed cron process should exit; do not run the long-lived scheduler as a cron command.

For verification in a Railway shell, `python manage.py tick_due` uses the same safe operation as cron. Do not manually edit snapshots, deadlines, or tick rows to force progress. Existing game snapshots keep their saved economy and roads.

### Continuous worker alternative

For five/ten-minute games, add a second service from the same repository and select `/railway.worker.toml` as its config file path. Share `DATABASE_URL`, `SECRET_KEY` and `DEBUG=0`. It runs `python manage.py run_scheduler`, checking due games every ten seconds. No public domain or HTTP health check is needed. Run the web service's migrations before starting the worker on a new schema.

Use either this worker or the cron setup above. The worker checks more regularly; both resolve the same stored deadlines through the same service.

All calendar entry points use the same transactional service. Deadlines advance from the stored calendar. A delay greater than one full interval pauses the game and records a letter; the owner resumes with a fresh interval. Manual games never advance on a page request.

## Verification and backups

```sh
uv sync --frozen
uv run ruff check .
uv run python manage.py collectstatic --noinput
uv run pytest
uv run python manage.py check --deploy
```

The deploy check expects production variables. Tests should use a disposable PostgreSQL database whose role can create a test database. Use Railway backups and keep a tested export before schema changes. With PostgreSQL 17 client tools:

```sh
pg_dump --dbname="$DATABASE_URL" --format=custom --file=yaara-backup.dump
```

Restore into a **new empty database**:

```sh
pg_restore --dbname="$RESTORE_DATABASE_URL" --no-owner --no-acl yaara-backup.dump
DATABASE_URL="$RESTORE_DATABASE_URL" python manage.py migrate --noinput
DATABASE_URL="$RESTORE_DATABASE_URL" python manage.py check
```

Keep services on the original database until restored users, snapshots, ticks and reports have been verified. Dump files contain password hashes and private state and must remain private. Restore is an operations procedure, not a game editing feature.

Email password reset is not configured. An authorized operator can run `python manage.py changepassword USERNAME` in Railway. Run `python manage.py clearsessions` periodically to remove expired sessions.

## Scope

Private, unranked solo games; active/passive opponents; V0/V1; manual/scheduled months; fixed final results. French/English responsive UI and local assets. No external fonts, LLM APIs, Redis, or frontend build system. Human multiplayer, email, competitive rankings and game-master edits remain future work. Computer opponents are basic; rule tests do not establish game balance.
