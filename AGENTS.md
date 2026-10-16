# Working on Yaara

- By default, commit and push completed changes directly to `origin/yaara-deployment` after the full push checkpoint passes. Do not create a pull request unless the owner explicitly requests one. Preserve existing deployment-branch changes; never force-push. Report push and deployment verification separately.

- Read `docs/design-source.fr.md` for game rules and `docs/decisions.md` for explicit implementation choices. Do not silently rebalance existing games.
- Conversation and code (including identifiers, tests and comments) are English. Player-visible copy supports French (the default) and English; keep the pure engine’s canonical French strings independent of request language. See `docs/localization.md`.
- In-game screens are a plain, image-free manuscript: a single reading column, restrained typography, and scribe narration. Use prose and accessible disclosures for accounts, letters and decrees; keep exact costs and consequences clear. The pre-game interface can retain its conventional web layout.
- Work in the existing checkout. Cloud tasks are already isolated; do not create worktrees unless requested.
- Keep the Python simulation independent of Django, storage, HTTP and clocks. Application services own authorization, per-game transactions, idempotency and persistence.
- Follow the established pseudo-TDD policy in `docs/testing.md`: define each logical use-case variation and its independent test before implementing it; use native Python stubs for external dependencies, or explicit inputs for pure functions. Preserve a one-to-one relationship between a specified variation and a logical test case. Parameterized rows count as separate cases; multiple assertions may verify one case.
- Run the entire existing suite, including real PostgreSQL integration tests and the browser smoke, for every push. CI must keep running all layers on pushes and PRs. A skip or a stubbed database is not evidence that a PostgreSQL requirement passed.
- Never send hidden opponent state or numerical combativity to the browser. Reports are immutable recipient-specific projections.
- Commands: `uv sync --frozen`, `uv run python manage.py migrate`, `uv run pytest --require-postgresql --fail-on-skip --check-case-catalog`, `uv run ruff check .`, `uv run python manage.py runserver`.
- Run PostgreSQL tests with `DATABASE_URL` pointing to a disposable database whose user can create test databases. Browser smoke: `uv run python scripts/browser_smoke.py` against a local running server.
- Keep each change coherent and playable. No extra agent framework or distributed architecture is needed. Summarize behavior, checks, and remaining limitations after changes.
- Give each collected variation a stable `@case` ID and requirement; review updates to `tests/case_ids.txt`. Refactor only for a concrete benefit. See `docs/testing.md` for native stubs, report generation and the complete push checkpoint.
- Require 100% statement and branch coverage of all native core modules from logic cases alone: `uv run coverage run -m pytest -q -m logic --fail-on-skip --check-case-catalog`, then `uv run coverage report`. No coverage exemptions or database-backed logic cases. Specify behavior and side effects before implementation; artificial red-green baby steps are unnecessary.
