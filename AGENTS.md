# Working on Yaara

- Read `docs/design-source.fr.md` for game rules and `docs/decisions.md` for explicit implementation choices. Do not silently rebalance existing games.
- Conversation and code (including identifiers, tests and comments) are English. All player-visible copy is French.
- In-game screens are a plain, image-free manuscript: a single reading column, restrained typography, and scribe narration. Use prose and accessible disclosures for accounts, letters and decrees; keep exact costs and consequences clear. The pre-game interface can retain its conventional web layout.
- Work in the existing checkout. Cloud tasks are already isolated; do not create worktrees unless requested.
- Keep the Python simulation independent of Django, storage, HTTP and clocks. Application services own authorization, per-game transactions, idempotency and persistence.
- For rule changes, write a meaningful example/boundary test first, implement the behavior, then run the relevant tests. Test concurrency against PostgreSQL, not a mock or SQLite.
- Never send hidden opponent state or numerical combativity to the browser. Reports are immutable recipient-specific projections.
- Commands: `uv sync --frozen`, `uv run python manage.py migrate`, `uv run pytest`, `uv run ruff check .`, `uv run python manage.py runserver`.
- Run PostgreSQL tests with `DATABASE_URL` pointing to a disposable database whose user can create test databases. Browser smoke: `uv run python scripts/browser_smoke.py` against a local running server.
- Keep each change coherent and playable. No extra agent framework or distributed architecture is needed. Summarize behavior, checks, and remaining limitations after changes.
