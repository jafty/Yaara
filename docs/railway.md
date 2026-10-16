# Railway deployment

This repository is prepared for Railway; it has not been published to your account.

## Web and PostgreSQL

1. Push the project to GitHub, then create a Railway service from that repository, using the repository root. `railway.toml` selects the Dockerfile.
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

4. Generate the public domain. The build installs pinned, checksum-verified dependencies, compiles French and English catalogs and collects static assets. Apply migration `0002_report_content` before starting the updated web and calendar services; existing game calendars and original archives are preserved. Pre-deploy runs `python manage.py migrate --noinput`; Gunicorn runs as a non-root user. `/health/` checks database connectivity.
5. Open the domain, register, and create a **manual V1** game. This mode requires no scheduler. Accounts, sessions, games and reports persist in PostgreSQL; the web container requires no volume.

Railway terminates HTTPS. Django trusts its forwarded HTTPS header and uses HTTPS redirects and secure cookies. Direct public container hosting requires a trusted TLS reverse proxy.

## Optional automatic calendar

For five/ten-minute games, add a second service from the same repository and select `/railway.worker.toml` as its config file path. Share `DATABASE_URL`, `SECRET_KEY` and `DEBUG=0`. It runs `python manage.py run_scheduler`, checking due games every ten seconds. No public domain or HTTP health check is needed. Run the web service's migrations before starting the worker on a new schema.

Alternatively, schedule `python manage.py tick_due` using Railway cron. Timing is approximate; the worker checks more regularly. Do not apply the web health-check configuration to a one-shot cron job.

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

Private, unranked solo games; active/passive opponents; V0/V1; manual/scheduled months; fixed final results. French responsive UI and local assets. No external fonts, LLM APIs, Redis, or frontend build system. Human multiplayer, email, competitive rankings and game-master edits remain future work. Computer opponents are basic; rule tests do not establish game balance.
