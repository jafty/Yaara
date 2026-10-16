# Yaara

A playable strategy game of rival oasis kingdoms. Govern three cities, develop production, send raids and capture your rivals' cities. French and English interfaces; English Python code. Prepared for Railway with Django 5.2 LTS, Python 3.13 and PostgreSQL 17.

## Play locally

```sh
uv sync --frozen
uv run python scripts/compile_translations.py
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
- Dated private reports in French and English, a persistent resource ribbon, textual house accounts, optional city folios, realm-wide multi-city work checklists and expedition forms, and an explicit draft/seal flow. Account and reign-selection pages retain their conventional layout. Change languages in the footer, including on an unsealed draft.
- Manual Moons or a five/ten-minute worker; persistent games and fixed results. New reigns open at Moon 1; saved legacy calendars retain their timing.

The default reign lasts ten years. The first harvest arrives at the closure of Moon 12; initial captures are deliberately unaffordable. The game includes a rules summary. Older reports without structured narration remain labelled original French archives; new reports switch languages when read.

## Deployment and development

- [Railway setup, variables, scheduler and backups](docs/railway.md)
- [Original design dossier](docs/design-source.fr.md)
- [Implemented rules and quick start](docs/rules.md)
- [Architecture and working method](docs/architecture.md)
- [Test-first policy, native stubs and case catalog](docs/testing.md)
- [Prototype decisions and limitations](docs/decisions.md)
- [Agent instructions](AGENTS.md)

```sh
uv run pytest --require-postgresql --fail-on-skip --check-case-catalog
uv run ruff check .
uv run python manage.py check
```

Set `DATABASE_URL` to a disposable PostgreSQL database for real concurrency tests; SQLite explicitly skips them. For the browser smoke, run the server separately, install Chromium (`uv run playwright install chromium`) or set `CHROMIUM_PATH`, then run `uv run python scripts/browser_smoke.py`. It creates a disposable account and saves ignored screenshots under `artifacts/`.

Production dependencies are locked in `uv.lock` and exported with hashes to `requirements.txt`. After dependency changes, run `uv lock` and `uv export --frozen --no-dev --format requirements-txt --no-header --output-file requirements.txt`.

No external game assets or paid APIs are required. Human multiplayer and competitive rankings remain future work.
