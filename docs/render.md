# Render backup deployment

## Create the web service

1. Connect this repository in Render and create a **Web Service**. Select the branch
   containing the Render settings change (normally `codex/yaara-deployment`).
2. Choose **Docker** as the runtime. Use the directory containing `Dockerfile` and
   `manage.py` as the service root (the repository root, unless the repository is
   nested). Dockerfile path: `./Dockerfile`; build context: `.`.
3. Leave the Docker command override empty. The image runs `sh scripts/start.sh`,
   which binds Gunicorn to Render's `PORT` and sends access/error logs to the console.
   Static files are collected during the Docker build and served by WhiteNoise.
4. Set the health check path to `/health/` (including the trailing slash). This
   endpoint checks database connectivity.

## Environment

| Variable | Value |
| --- | --- |
| `DEBUG` | `0` |
| `SECRET_KEY` | A long, random Django secret, kept stable across deployments |
| `DATABASE_URL` | Your PostgreSQL connection URL |
| `SIGNUP_ENABLED` | `1` to allow registration; optionally `0` afterward |
| `WEB_CONCURRENCY` | `2` initially (optional) |

The expected name is `SECRET_KEY`, not `PRIVATE_KEY`. Django does not need an SSH
private key. Generate a Django secret locally with
`python -c 'import secrets; print(secrets.token_urlsafe(64))'` and paste it into
Render's environment editor. Do not commit the value.

Render supplies `RENDER_EXTERNAL_HOSTNAME` automatically. The settings allow that
hostname and trust its HTTPS origin; no manually configured `ALLOWED_HOSTS` is
needed for the generated `.onrender.com` address. Railway's automatic hostname
support remains in place.

For a custom domain, add it in Render and set `ALLOWED_HOSTS=game.example.com` and
`CSRF_TRUSTED_ORIGINS=https://game.example.com`. Both variables accept comma-separated
values. Allowed hosts contain no scheme or path; trusted origins include `https://`.

## Database and migrations

For an independent backup, create Render PostgreSQL in the same region and use its
**Internal Database URL** in `DATABASE_URL`. A database hosted outside Render needs
its externally reachable URL, network access permissions and any TLS options
required by its provider. A Railway private/internal hostname will not resolve
from Render. A web backup using Railway's database still depends on that database
during a Railway outage.

Set Render's **Pre-Deploy Command** to:

```sh
python manage.py migrate --noinput
```

If your service plan does not support pre-deploy commands, set **Docker Command**
to the following fallback, which migrates before serving traffic:

```sh
sh scripts/start-render.sh
```

Use the fallback with a single instance and serialize deployments; do not run
concurrent migration commands. Do not migrate during the Docker image build.
Enter the command as plain text, without quotes or JSON brackets. The dedicated
script applies migrations and starts Gunicorn only if they succeed. Avoid inline
`sh -c` commands in this field: command parsing can preserve quotes literally.

A new database starts empty: it does not copy Railway accounts or games. To keep
existing data, restore a tested PostgreSQL backup into a new empty Render database
before migrations, following the dump/restore steps in `railway.md`. Rehearse this
before an outage and define how recently the backup must have been refreshed.

## Verify and find errors

Deploy, then open `https://YOUR-SERVICE.onrender.com/health/`. Expect HTTP 200.
Open the home page and test registration/login, a form submission and static
assets. Use Render's service **Logs** view for runtime logs; reproduce the failing
request while viewing it. Gunicorn access logs show the status and Django console
logs report rejected hosts, CSRF failures and unhandled application errors.

- **400 / Invalid HTTP_HOST:** confirm the deployed branch includes these settings
  and that `RENDER_EXTERNAL_HOSTNAME` matches the generated hostname. Add custom
  domains explicitly as described above.
- **403 / CSRF:** verify the trusted HTTPS origin for a custom domain and access
  the app over HTTPS. The existing settings recognize the proxy's forwarded HTTPS
  header and use secure cookies.
- **Startup fails:** check `SECRET_KEY`, `DATABASE_URL`, database reachability and
  migration output. Production deliberately refuses the default secret and SQLite.
- **Missing tables:** run migrations against the same database as the web service.

Keep `DEBUG=0` when diagnosing public deployments.

## Optional scheduled games

Manual games need only the web service. For automatic games, create a Render
**Background Worker** from the same Dockerfile with command
`python manage.py run_scheduler`. Give it the same `DEBUG`, `SECRET_KEY` and
`DATABASE_URL`; start it after migrations. It needs no public HTTP endpoint.
Choose one scheduler owner for the active database when failing over, and stop
the old scheduler before enabling the replacement.
