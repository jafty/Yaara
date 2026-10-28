# Verification policy

## Specify behavior and use the right layer

Before changing logic, specify normal, rejection and boundary outcomes from current rules and decisions. Maintain one independently collected case per specified behavior variation; parameter rows are cases, and several assertions may establish one outcome. Add or update regression cases with the change. A failing regression is useful evidence; artificial red-green steps are unnecessary.

- Logic: database-free engine, rules, calendar, tactics, projections and narration. Assert outcomes and side effects, including unchanged authoritative state on rejection. These are the default systematic checks for logic changes.
- HTTP/application integration: routing, methods, CSRF, language, rendered contracts, authorization and service/persistence wiring. These cannot establish browser layout or actual JavaScript behavior.
- Real PostgreSQL: locking, races, constraints, transaction rollback, migrations and idempotency under concurrent delivery. SQLite and stubs do not establish these properties. Local integration verification uses a disposable PostgreSQL database.
- Journeys: cross-cutting simulation invariants and compatibility over multiple stages, additional to focused cases.
- Browser: real navigation, forms, JavaScript, focus, reflow, layout and assets. Assertions do not replace looking at captures for visual work.

Use fixed explicit inputs and native collaborators in `tests/stubs.py` for random draws, clocks and injected failures. Do not mock the rule under test, derive expected answers from production helpers or recreate a database. Keep logic independent of Django database fixtures.

## Select local checks by impact

| Change | Checks before a completed local commit / CI-gated deployment-branch push |
| --- | --- |
| Documentation only | Review factual consistency, links and diff; no invented behavior tests. |
| Isolated copy, CSS property or decorative artwork | Focused live-browser check of the changed state; inspect captures. Compile both catalogs for translated copy. Run relevant HTTP cases if a rendered contract changed. No unrelated core or PostgreSQL suite. |
| Client interaction, navigation, city-panel structure or shared layout | Relevant HTTP/application cases on PostgreSQL and focused browser flows, including affected native fallback. Run the full affected browser journey for shared shell/forms/asset-loading changes. |
| Rules, projections, narration or bounded application behavior | Complete logic suite and core coverage gate; affected integration/journey cases on PostgreSQL. Browser check when displayed behavior or player flow changes. |
| Schema, transactions, locking, authorization/privacy, calendar/scheduler, dependencies, runtime, CI or unclear/broad impact | Full local checkpoint, plus targeted cases for the changed boundary. |

For mixed batches, select checks per work package during iteration and use coherent commits. The combined release must satisfy the highest applicable level; unrelated presentation edits do not need the logic suite after every iteration. Split a delayed or uncertain feature into another branch when the finished fixes should ship first.

Line count does not determine risk. An alert-count calculation is behavior even when its UI is small. A saturation-only city-art adjustment is presentation only if asset choice, public fortification mapping and geography are unchanged.

Minor visual changes can break browser tests through real reflow/visibility regressions or obsolete DOM/style expectations. Focused verification reduces local cost; it does not guarantee that wider suites will pass. Inspect affected shared selectors and callers, and classify any later failure using the table below.

The focused presentation exception requires verified presentation-only impact, no altered input/data/auth/state contract, no shared-flow uncertainty, passing focused checks and no unexplained affected failure. A focused browser check may use a disposable app/database without rerunning PostgreSQL tests; a static mockup alone is insufficient. Record revision, route/state, language, viewport, actions, captures and observed result. Check 320/390px and desktop for responsive work; add 200% text, keyboard, no-JavaScript and reduced motion when affected. Check both languages for copy or language-sensitive layout.

For mobile map/city-panel changes verify native 680:500 map proportions, unchanged map dimensions across contexts, readable city names, unobscured controls, direct return, scroll/focus and native forms. For news counts, combine recipient/latest-Moon/exclusion cases with browser unread persistence, reading, reload, context navigation and separation from unresolved warnings.

All changed Python code needs relevant lint/format checks. Run full catalog collection when pytest cases or metadata change; not on every CSS iteration. Reuse successful evidence only while its relevant code and environment remain unchanged.

## Commands and traceability

`uv sync --frozen` installs the pinned environment. Fast core iteration:

```sh
uv run pytest -q -m logic --fail-on-skip
```

Each pytest case still requires one `@case("stable-id", "source requirement")` and one layer (`logic`, `integration`, `journey`). Logic methods require exactly three nonempty English Given/When/Then docstring lines. Keep meaningful IDs stable when selectors or wording change; review catalog removals and additions.

Check the catalog with full collection; do not compare a selected file's collected set with the full catalog:

```sh
uv run pytest --collect-only -q --check-case-catalog
```

After reviewing intentional case changes, generate the candidate catalog and inspect its diff:

```sh
uv run pytest --collect-only -q --case-report=/tmp/yaara-cases.json
uv run python -c 'import json; from pathlib import Path; rows=json.loads(Path("/tmp/yaara-cases.json").read_text()); Path("tests/case_ids.txt").write_text("\n".join(sorted(row["id"] for row in rows))+"\n")'
```

The configured 100% statement/branch core gate remains required for native-core changes and full verification. Run logic alone under coverage; integration/journeys cannot fill its gaps. Review behavior and invariants as well as coverage. Do not add exclusions or calls with no meaningful assertion to meet a percentage.

```sh
uv run coverage run -m pytest -q -m logic --fail-on-skip --check-case-catalog --case-report=artifacts/core-cases.json
uv run coverage report
uv run coverage json
```

## Diagnose failures before choosing a remedy

| Finding | Verification and action |
| --- | --- |
| Real regression | Reproduce the violated contract, fix implementation and rerun the case plus affected coverage. Block completion/release. |
| Intentional behavior change | Cite the accepted requirement; update code and expectations together, preserving rejection/privacy/invariant coverage. Rerun old/new affected flows and review any catalog changes. |
| Stale test | Verify removal/replacement was authorized and inspect the actual replacement UI. Replace obsolete selectors with checks of the surviving user outcome. Delete only a truly retired contract with a recorded reason; do not restore removed UI to satisfy a selector. |
| Unrelated baseline failure | Reproduce the same failure at the identified base SHA using the same command, dependencies and disposable environment, without disturbing dirty work. Record node/case ID, error, base/candidate SHAs, reproduction, impact, issue/task and follow-up date. If not reproduced, call it unclassified, not pre-existing. |
| Environment problem | Record the error and missing evidence, repair/retry or leave explicitly unverified. It is not a product pass. |

An unexpected failure first triggers investigation; run broader checks when its cause suggests wider impact or remains unclear. It does not automatically require every suite for a proven obsolete selector.

Do not silently ignore, broadly skip, xfail, weaken expectations or relabel a failed run as green. A baseline defect may be committed on an isolated branch with clear WIP status and passing affected checks. Repair stale tests as part of the change when justified. The deployment branch/production require the release checks below; known failures do not silently exempt them. Any exceptional release needs the owner's explicit acceptance of the specific failure and impact, recorded with an expiry and repair task; CI must remain visibly failed. Authorization, privacy, corruption and scheduler-integrity failures must be fixed before release.

## Commit, push and production

No Railway preview environment or per-branch deployment is required. Verify non-deployment branches with a local application and disposable data. The owner can playtest after release; keep releases small and reversible because their personal acceptance then occurs on the deployed version. Never substitute production for disposable automated browser testing.

- Completed local commit: applicable checks above pass; inspect staged diff and include only task files. WIP commits on isolated branches may record incomplete checks/failures explicitly.
- Non-deployment push: affected checks plus explicit WIP/failure disclosure; CI still runs fully.
- Deployment-branch push: synchronize and recheck the combined result. If Railway's wait-for-CI gate is verified, applicable local checks suffice before pushing; full CI must pass on the resulting SHA before production. If that gate is absent or unknown, require the full local checkpoint before pushing because the push may deploy immediately.
- Production: full required CI on the exact release SHA, reviewed migration/compatibility impact and recoverability for data changes, then verify actual web and cron/worker revision/status. Check health and affected production flow without creating disposable test games or changing real game state. For scheduling work, verify scheduler execution and persisted outcomes through an authorized operational procedure. Never run destructive/local browser scripts against production.

Full checkpoint: set `DATABASE_URL` to disposable PostgreSQL with test-database creation rights. Compile translations; lint and format; run the core gate above; then:

```sh
uv run python scripts/compile_translations.py
uv run ruff check .
uv run ruff format --check .
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py migrate --noinput
uv run python manage.py collectstatic --noinput
uv run pytest -q --require-postgresql --fail-on-skip --check-case-catalog --case-report=artifacts/test-cases.json
uv export --frozen --no-dev --format requirements-txt --no-header --output-file /tmp/requirements.txt
diff -u requirements.txt /tmp/requirements.txt
```

Start the disposable server with `uv run python manage.py runserver 127.0.0.1:8000 --noreload --nothreading`, then run `uv run python scripts/browser_smoke.py` and `uv run python scripts/recruitment_browser_smoke.py`. The game smoke also invokes `run_map_journeys()` from `scripts/map_browser_smoke.py`, so map coverage is included in that command and in CI. For a focused map/workspace/header/navigation check, run `uv run python scripts/map_browser_smoke.py` directly; do not repeat it after a successful unchanged full game smoke. Check its Chromium-path prerequisite.

Current CI runs on every push and PR with PostgreSQL 17 and 18, enforces the full pytest and core coverage gates and invokes the game (including map journeys) and recruitment browser scripts. A failed earlier step prevents later checks; report those as not run. Skips/expected failures are rejected. It uploads case/coverage JSON with `if: always()`; browser captures and server logs are not currently uploaded by that step. Report actual commands, database versions, outcomes and missing evidence separately from CI and deployment status.
