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
| `GUEST_PLAY_ENABLED` | `1` (default) enables immediate solo play without signup |
| `GUEST_RETENTION_DAYS` | `30` idle days by default; a registered save is retained |
| `GUEST_STARTS_PER_HOUR` | `60` per network address by default |
| `GUEST_GLOBAL_STARTS_PER_HOUR` | `500` across the deployment by default |
| `WEB_CONCURRENCY` | `2` initially |

Railway's `RAILWAY_PUBLIC_DOMAIN` is automatically allowed and trusted. The start script honors `PORT`. Generate a secret locally with `python -c 'import secrets; print(secrets.token_urlsafe(64))'` and enter it in Railway variables, not a committed file.

4. Generate the public domain. The build installs pinned, checksum-verified dependencies and compiles French and English catalogs and collects static assets. Pre-deploy runs `python manage.py migrate --noinput`; Gunicorn runs as a non-root user. `/health/` checks database connectivity.
The compiled translation catalogs are included in Git and the Docker image. The report-content schema migration runs through the existing pre-deploy command; no manual translation compilation is needed on Railway.

5. Open the domain and choose **Play without signing up** to start a manual solo game immediately. Saving it into a new or existing account retains its progress. Registered users can also configure their own solo games. Manual games require no scheduler. Accounts, sessions, games and reports persist in PostgreSQL; the web container requires no volume.

Railway terminates HTTPS. Django trusts its forwarded HTTPS header and uses HTTPS redirects and secure cookies. Direct public container hosting requires a trusted TLS reverse proxy.

## Multiplayer operator setup

After migrations, grant the existing organizer account permission in a Railway shell:

```sh
python manage.py grant_operator USERNAME
```

Open `/manage/`, create a shared reign, and share its recruitment link. Players choose an available starting territory and name their house without an account. The page shows remaining spots; the third claim starts the reign automatically. Each player must keep their separate private return link, available in the waiting room and email-preferences page. The common recruitment link never grants access to an occupied house. The organizer may also choose a spot while retaining management access.

The management page updates as players enter. Existing rooms retain their operator Start button; new rooms start at 3/3 with active invitations. Waiting players enter Council automatically, with a native refresh link when JavaScript is unavailable. The organizer can pause/resume the common calendar, rotate recruitment, or replace/suspend a private link from the same room. Private-link rotation invalidates previous bearer links and seat sessions; an already linked registered account retains its account access. See `docs/multiplayer-contract.md` for the authorization boundary.

Shared games require the cron service or continuous worker below. Their first Moon receives one full interval from the organizer's start, unlike the aligned first deadline of an individually configured automatic solo game. No browser advances the shared calendar. Verify the scheduler on the production database before recruiting a live group.

Application access logs retain method, status, timing and response size without paths, queries or referrers. Django request and worker-error logs redact private invitation paths. Hosting/CDN logs are outside this application configuration: disable full-URL logging there or restrict its access and retention, since a private invitation URL grants access to its house.

Run `python manage.py cleanup_guests` periodically alongside session cleanup to remove expired, unclaimed private solo trials. The command excludes retained accounts and shared-seat identities; see `docs/guest-access.md`. The address budget uses the connection address supplied to Django, not untrusted forwarded headers; check proxy topology before tuning it.

## Automatic calendar with Railway cron

The web service serves pages; a separate cron service closes due Moons using server time and the UTC deadlines stored in PostgreSQL. No browser must remain open. Reloading reads the persisted result; the countdown is informational and does not execute a turn. The existing browser refresh notice also preserves unfinished forms.

Player and operator pages display those same instants in `Europe/Paris`, labelled
“heure de Paris” / “Paris time”, with automatic winter/summer changes. UTC remains
the storage and cron timezone: 08:22 UTC is 09:22 in French winter time and 10:22
in summer. A pending-resolution banner means the order deadline has passed; it
does not establish that the scheduler has processed the Moon. For a five-minute
cron, a deadline at 08:22 UTC will normally be picked up around 08:25 UTC. If it
remains pending beyond the next cron run, inspect that service's logs and the
operator's shared calendar state. A tied score does not block closure 120.

1. Keep the existing web service and PostgreSQL database. Deploy the web migrations first.
2. Add a second Railway service from **the same `jafty/Yaara` repository**, watching **`codex/yaara-deployment`**. Set its config file path to **`/railway.cron.toml`**. This file selects the Dockerfile, runs **`python manage.py tick_due`**, schedules **`*/5 * * * *`** (every five minutes, UTC), and disables automatic restart after the one-shot command exits.
3. Give the cron service `DATABASE_URL` referencing **the same PostgreSQL service** as the web app, the same stable `SECRET_KEY`, and `DEBUG=0`. It needs no domain, volume, web start command, or HTTP health check. Remove any inherited web health-check setting and any manually overridden start command. Verify the resulting cron schedule and start command in Railway's service settings after deployment.
4. If the continuous `run_scheduler` worker was previously enabled, stop it after the cron service is configured. Locks and tick records prevent duplicate resolution, but one scheduler is easier to operate.
5. Create an **Automatic** reign; ten-minute Moons are recommended for a five-minute cron. New reigns wait during the prologue. Press **Commencer le règne / Begin the reign** to begin immediately and set the first deadline at the next five/ten-minute mark (:00, :05, … or :00, :10, …). The first Moon may be shorter; this is stated before starting. Running legacy calendars keep their stored deadlines. Manual games stay manual; this deployment does not convert or rebalance existing games.
6. Check the cron execution logs after a deadline. Each processed game logs its UUID and `resolved`, or `unchanged or paused`. Reload Council: the open Moon should advance once, reports should carry the closed Moon, and the next deadline should advance from its prior value. Run the cron service manually once to verify its connection; an early run must leave the Moon unchanged.

Railway cron execution times are approximate. A closure due at 12:10 UTC may be processed slightly later; orders close at 12:10 even while the cron job is pending. Older calendars may still have deadlines such as 12:03 UTC, processed around 12:05. Five-minute games can work, but startup delay is more visible. Do not describe browser time as authoritative or allow a client clock to authorize a late order.

After a delay **greater than one full game interval**, the existing protection pauses the game and records a calendar report rather than consuming unattended decision windows. Resume it in Council to open a fresh interval. If games stop advancing, inspect cron executions, database connectivity, the chosen mode, pause state, and deployment/migration errors. A completed cron process should exit; do not run the long-lived scheduler as a cron command.

For verification in a Railway shell, `python manage.py tick_due` uses the same safe operation as cron. Do not manually edit snapshots, deadlines, or tick rows to force progress. Existing game snapshots keep their saved economy and roads.

### Continuous worker alternative

For five/ten-minute games, add a second service from the same repository and select `/railway.worker.toml` as its config file path. Share `DATABASE_URL`, `SECRET_KEY` and `DEBUG=0`. It runs `python manage.py run_scheduler`, checking due games every ten seconds. No public domain or HTTP health check is needed. Run the web service's migrations before starting the worker on a new schema.

Use either this worker or the cron setup above. The worker checks more regularly; both resolve the same stored deadlines through the same service.

All calendar entry points use the same transactional service. Deadlines advance from the stored calendar. A delay greater than one full interval pauses the game and records a letter; the owner resumes with a fresh interval. Manual games never advance on a page request.

## Verification and backups

### Optional email notifications

Apply migration `0005_game_auto_start_game_recruitment_version_and_more` before
updating web and calendar services. Email is disabled by default. It uses Django's
built-in SMTP backend; no notification API, broker or new dependency is required.
Set these on **both web and cron/worker services**:

| Variable | Value |
| --- | --- |
| `EMAIL_NOTIFICATIONS_ENABLED` | `1` after transport is ready |
| `PUBLIC_BASE_URL` | Canonical HTTPS origin, for example `https://your-hostname` |
| `DEFAULT_FROM_EMAIL` | Sender address accepted by your mail server |
| `EMAIL_HOST`, `EMAIL_PORT` | Your SMTP server and port |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Credentials if the server needs them |
| `EMAIL_USE_TLS` | `1` for STARTTLS, commonly port 587 |
| `EMAIL_USE_SSL` | `1` for implicit TLS, commonly port 465; do not enable both TLS modes |

A self-hosted/local MTA is also possible using
`EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` and its host/port, or
`django.core.mail.backends.sendmail.EmailBackend` when a sendmail binary exists
in the deployment image. The standard image does not install an MTA. SMTP is a
transport requirement, not an external notification processor. Configure sender
DNS and mail-server access in your hosting environment; this change supplies no
SMTP credentials and does not establish live deliverability.

Players open **Email notifications** in the waiting room or any game, provide an
optional address, select events, and confirm the email within 48 hours. This
works for guest seats; event emails include their current private return link.
Solo guest mail still requires that browser's guest cookie for game access; email
confirmation does not convert or recover a solo identity. Raids default off and
are delayed/grouped for at most one digest per 24 hours. Harvest letters from
one closure are sent together. Clearing the address or using the native POST
unsubscribe page cancels pending mail without registration. A mail scanner's GET
does not subscribe or unsubscribe anyone.

`tick_due` drains the outbox after processing games, so the existing cron or
continuous worker needs no extra service. For installations without that worker,
schedule `python manage.py send_notifications` every five minutes. The command
is also safe for manual testing against a disposable mail backend. Failures retry
with bounded backoff; expired five-minute delivery leases recover worker crashes.
Transport occurs outside database locks. SMTP delivery is at-least-once, and a
message already in transport cannot be recalled by unsubscribing. Application
logs redact invitation, recruitment and email-action credentials; restrict full
URL logging in the hosting layer as well.

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

Private, unranked guest/account solo games and operator-managed three-house multiplayer; active/passive solo opponents; compatible saved rules; manual/scheduled months; fixed final results. French/English responsive UI and local assets. No external fonts, LLM APIs, Redis, or frontend build system. Email, competitive rankings and game-master state edits remain future work. Computer opponents are basic; rule tests do not establish game balance.
