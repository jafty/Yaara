# Yaara

A playable strategy game of rival oasis kingdoms. Govern three cities, develop production, send raids and capture your rivals' cities. French and English interfaces; English Python code. Prepared for Railway with Django 5.2 LTS, Python 3.13 and PostgreSQL 17.

## Play locally

```sh
uv sync --frozen
uv run python scripts/compile_translations.py
uv run python manage.py migrate
uv run python manage.py runserver
```

Open the local server and start a private **manual** reign without registration. Saving into an account is optional. SQLite is the default local solo fallback. Use PostgreSQL for production and concurrency tests.

For PostgreSQL, copy `.env.example` to `.env`, choose a local password and random secret, export those variables in your shell, then:

```sh
docker compose up -d database
uv run python manage.py migrate
uv run python manage.py runserver
```

Django does not load `.env` automatically. It is ignored by Git. In the current cloud workspace, use `.venv/bin/python` directly if `uv`'s default cache directory is read-only.

## Playable features

- Nine-city map, immediate guest solo against computer opponents, and three-human shared reigns with self-selected territories, custom house names, remaining spots and automatic start at 3/3.
- Optional confirmed email subscriptions for guests and accounts: starts, captures, annual harvests and an opt-in daily raid digest, using standard SMTP or local sendmail.
- Current rules with local funding, seasonal crop raids, annual harvest, growth and Fidèle renewal; older saves retain their rules.
- Eight building families, batched local construction, origin-specific equipment/transport/siege gear, raids, captures, relief and returns.
- Decree previews, atomic confirmation, target reservation and pre-departure cancellation.
- Dated private reports in French and English, a persistent resource ribbon, textual house accounts, optional city folios, realm-wide multi-city work checklists and expedition forms, and an explicit draft/seal flow. Account and reign-selection pages retain their conventional layout. Change languages in the footer, including on an unsealed draft.
- Manual Moons or a five/ten-minute worker; persistent games and fixed results. New reigns open at Moon 1; saved legacy calendars retain their timing.
- End-of-reign book for your house or all houses (owner only), with chronological letters and complete or compact JSON downloads. For a past game, open the book, choose your house or all houses, and use “Download the discussion summary (compact JSON)”. It retains letters, monthly economy, city/order changes and final accounts without replaying the game. Monthly accounts begin with newly recorded closures; older gaps are explicit.

The default reign lasts ten years. The first harvest arrives at the closure of Moon 12. The game includes a rules summary. Older reports without structured narration remain labelled original French archives; new reports switch languages when read.

## Deployment and development

- [Render backup deployment, variables and troubleshooting](docs/render.md)
- [Railway setup, variables, scheduler and backups](docs/railway.md)
- [Current gameplay reference](docs/gameplay-review-prompt.fr.md)
- [Future ideas backlog](docs/backlog.fr.md)
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

No external game assets or paid APIs are required. Competitive rankings remain future work.

## Recruitment and shared reigns

The public entrance offers a private manual solo game without registration. Guests can keep
their existing reign by creating an account or attaching it to an authenticated account.
The warm manuscript presentation uses compact contextual frescoes, restrained dividers,
clear resource labels and an explicit link from a sealed order to Moon closure. Technical
JSON exports stay in secondary completed-book controls.

Official shared games use the same current nine-city rules with three human houses.
Bootstrap an existing registered operator account after migrations:

```sh
uv run python manage.py grant_operator USERNAME
```

Open `/manage/`, choose the duration, cadence and agreed play windows, then share the
room's recruitment link. Each guest chooses an available starting territory and a
house name. Remaining spots update as players join; the third claim starts the game
automatically and waiting players enter Council. Keep the separate private return
link shown in the lobby and email-preferences page: the common recruitment link
cannot reopen an occupied house. A registered operator can
join a house while retaining their management session. A returning anonymous link
authenticates only the low-privilege seat, never that linked registered account.

Existing rooms retain their operator start; new rooms start at three claimed houses
with active invitations. There is no extra readiness step. Shared Moons receive a full first
interval and use the server scheduler. A standard 120-Moon reign spans twenty hours of
advancing calendar time, so advertise common play windows and pause between sessions.
An absent player gives no new orders; there is no automatic replacement bot.

Rotating or suspending a seat link invalidates its previous bearer link and seat sessions;
an independently authenticated linked registered account retains its membership access.
Guest solo progress remains owned by its original identity when visiting a shared seat;
the same browser offers a server-authorized way to resume that solo before saving it.
Players retain their own completed book; shared all-house analysis is operator-only after
completion. Existing solo saves retain their rules, clock alignment and archive policy.

See [the shared-reign behavior contract](docs/multiplayer-contract.md) and
[Railway deployment and scheduler instructions](docs/railway.md).

Players can optionally open **Email notifications**, enter an address without
registering, select updates and confirm their address. Raid emails default off and
group into at most one digest per 24 hours. The database queue is drained by the
existing calendar worker or `python manage.py send_notifications`. Outgoing email
stays disabled until standard SMTP or local sendmail is configured on web and worker;
see [the notification contract](docs/recruitment-notifications.md) and Railway setup.
