# Yaara

A playable strategy game of rival oasis kingdoms. Govern three cities, develop production, send raids and capture your rivals' cities. French interface; English Python code. Prepared for Railway with Django 5.2 LTS, Python 3.13 and PostgreSQL 17.

## Play locally

```sh
uv sync --frozen
uv run python manage.py migrate
uv run python manage.py runserver
```

Open the local server, create an account, then start a **V1 / manual** reign. SQLite is the default local solo fallback. Use PostgreSQL for production and concurrency tests.

For PostgreSQL, copy `.env.example` to `.env`, choose a local password and random secret, export those variables in your shell, then:

```sh
docker compose up -d database
uv run python manage.py migrate
uv run python manage.py runserver
```

Django does not load `.env` automatically. It is ignored by Git. In the current cloud workspace, use `.venv/bin/python` directly if `uv`'s default cache directory is read-only.

## Playable features

- Nine-city map and private games against two active or passive opponents.
- V0/V1, local stocks, annual harvest, growth and Fidèle renewal.
- Batched construction, equipment, raids, captures, relief, siege and returns by origin.
- Decree previews, atomic confirmation, target reservation and V1 cancellation.
- Dated private reports and a plain French manuscript for play: scribe narration, unfolding city accounts, letters and dictated decrees. Account and reign-selection pages retain their conventional layout.
- Manual months or a five/ten-minute worker; persistent games and fixed results.

The default reign lasts ten years. The first harvest arrives at month 12; initial captures are deliberately unaffordable. The game includes a rules summary.

## Deployment and development

- [Railway setup, variables, scheduler and backups](docs/railway.md)
- [Original design dossier](docs/design-source.fr.md)
- [Implemented rules and quick start](docs/rules.md)
- [Architecture and working method](docs/architecture.md)
- [Prototype decisions and limitations](docs/decisions.md)
- [Agent instructions](AGENTS.md)

```sh
uv run pytest
uv run ruff check .
uv run python manage.py check
```

Set `DATABASE_URL` to a disposable PostgreSQL database for real concurrency tests; SQLite explicitly skips them. For the browser smoke, run the server separately, install Chromium (`uv run playwright install chromium`) or set `CHROMIUM_PATH`, then run `uv run python scripts/browser_smoke.py`. It creates a disposable account and saves ignored screenshots under `artifacts/`.

Production dependencies are locked in `uv.lock` and exported with hashes to `requirements.txt`. After dependency changes, run `uv lock` and `uv export --frozen --no-dev --format requirements-txt --no-header --output-file requirements.txt`.

No external game assets or paid APIs are required. Human multiplayer and competitive rankings remain future work.
