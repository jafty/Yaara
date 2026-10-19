# Test-first development policy

## Approved audit revision

Independent audit cases cover versioned yields at every level, saved economies without a marker, exact local affordability, atomic batch and expedition shortfalls, per-origin fixed-fee rounding, local debits and cancellation, each realm's two initial frontiers, further reach after capture, engagement ownership without hidden identifiers, and defender reports with public identity and survivor-dependent estimates. Existing cases explicitly select the old economy/map where they protect saved rules rather than new-game defaults.

HTTP acceptance cases cover idempotent authorized calendar start, POST-only mutation, cron execution without a browser and repeated-run safety, full-report anchors, news-first Council accounts with a jump link, and closure-review links on the main folios. Browser journeys exercise the new local-funding shortfall, two-target geography and batch workflows in both languages with JavaScript, no JavaScript, narrow screens and enlarged text. The full core coverage and PostgreSQL checkpoints remain mandatory.

The owner's policy is a standing requirement. Its basis is the design dossier, §26, plus the explicit requirement for one logical test per use-case variation. Conversation and test code are English; player-facing copy supports French and English, with canonical French engine messages preserved.

## Working sequence

1. Read the relevant rule. List its normal, rejection and boundary variations before editing behavior. Give each variation a stable case ID and a concrete expected outcome derived from the dossier or an explicit product decision, not from the implementation's output.
2. Write one independently collected logical test per variation. Parameter rows are separate cases with readable IDs. Several assertions may establish one outcome and its invariants; do not split one outcome into a test per assertion.
3. For new or corrected behavior, define the expected contract before implementing it. A failing regression is useful evidence when correcting a defect. Implement the smallest coherent solution and rerun the cases. Actual red-green baby steps and deliberately naive intermediate implementations are not required; do not manufacture failures when adding coverage for existing correct behavior.
4. Refactor only for a concrete benefit: clearer rules, less duplication, easier isolation, or an observed defect. AI does not make a test/code pair automatically correct. Both can share a mistaken assumption; compare expected results with the source and retain cross-cutting invariants.
5. Run affected checks during development, then all test layers before every push. Add the new IDs to the reviewed case catalog and inspect its diff. Summarize behavior changes and actual verification.

Existing tests can be reorganized without manufacturing a red phase or breaking working code. The initial implementation's historical test-first ordering cannot be established retroactively. New regressions must follow the sequence above.

## Direct inputs and native stubs

Use direct values or fixed state builders for pure rules. `tests/stubs.py` supplies small native Python collaborators:

- `FixedRandom`: a prescribed raid defense percentage and identity permutation. It supplies a draw, without recreating random generation or combat logic.
- `FixedClock`: a prescribed instant for scheduled application cases.
- `FailingBoundary`: a prescribed exception at a persistence/reporting boundary to exercise transaction rollback.

Use pytest's scoped `monkeypatch` to install these collaborators. Do not mock the rule being tested, derive expected values by calling production helpers, or build a second in-memory database. Seeded full-reign journeys additionally exercise the actual production random generator.

Use real PostgreSQL connections and transactions for locking, concurrent confirmations, constraints and rollback. Failure injection substitutes only the failing boundary; the database and rollback are real. Pure logic tests require neither a running database nor wall-clock waits.

## Traceability

Each collected test declares exactly one `@case("stable-id", "source requirement")` and one layer: `logic`, `integration`, or `journey`. Parameter IDs extend the stable ID. Broad journeys remain additional coverage and do not replace the individual rule variations in the logic suite.

`tests/case_ids.txt` is the reviewed list of collected variation IDs across all layers. Collection rejects missing metadata or duplicate IDs. Full verification also compares the collected set with the catalog, catching accidental removal or unreviewed additions. The JSON report includes each ID, source requirement, layer, node ID, phase outcomes and final outcome. Unrun and skipped cases remain distinguishable from passes.

The catalog enforces the declared mapping; it cannot discover an unspecified variation or prove exhaustive correctness. Review the variation list against the dossier whenever rules change. Do not weaken an expectation merely to make a failing test green.

## Complete core behavior coverage

The core comprises `simulation.engine`, `simulation.rules`, `simulation.projections` and `simulation.narration`. All their statements and branches must execute in the **logic suite alone**, with coverage's required total set to 100%. Add any new core module to the coverage source list. Do not omit branches, add coverage exemptions, remove real behavior or invoke unrelated code merely to satisfy the metric. Journey and integration execution cannot fill a gap in the logic gate.

For each behavior, specify normal outcomes, rejection causes, equality boundaries, state transitions and side effects. A rejection test must also establish that authoritative state did not change. A successful command must assert the relevant reservations, debits, movements, reports or result, rather than merely checking that no exception occurred. Each parameter row is one independent variation. Fixed native inputs and collaborators remain the default; do not substitute the production rule under test.

Complete coverage means the current finite set of specified behavior classes, not enumerating every integer, seed or sequence of commands. Statement and branch coverage are necessary checks, not a proof of every possible path or correctness: loops admit unbounded sequences and different inputs can traverse the same branches. Review the cases against the rules and decisions as well as the missing-coverage report. Unspecified behavior must be clarified rather than invented just to add a test.

The logic layer cannot request Django database fixtures or a `django_db` marker; pytest-django also blocks unrequested database access. Database transactions and concurrency remain real PostgreSQL integration requirements.

Run the independent core gate:

```bash
uv run coverage run -m pytest -q -m logic --fail-on-skip --check-case-catalog --case-report=artifacts/core-cases.json
uv run coverage report
uv run coverage json
```

The JSON case and coverage reports are CI artifacts. `coverage report` fails if even one core statement or branch is uncovered.

To refresh the catalog after reviewing new or intentionally changed variations:

```bash
uv run pytest --collect-only -q --case-report=/tmp/yaara-cases.json
uv run python -c 'import json; from pathlib import Path; rows=json.loads(Path("/tmp/yaara-cases.json").read_text()); Path("tests/case_ids.txt").write_text("\n".join(sorted(row["id"] for row in rows))+"\n")'
```

## Natural-language scenarios

Keep pytest and the existing one-case-per-variation mapping. Use the
Given/When/Then scenario convention from behaviour-driven development as strict
English docstrings for every `logic` test method. A separate Gherkin runner would
duplicate the current parameterized cases and their traceability without adding
a useful execution boundary. This is scenario documentation within the existing
test-first policy, not a claim that prose proves exhaustive coverage.

Each docstring has exactly three nonempty lines in this order:

```python
@case("cancellation-releases-reservations", "Design §26.2: V1 cancellation releases reservations")
def test_cancellation_releases_reservations(reserved_raid):
    """Given a confirmed V1 raid.
    When the player cancels it before departure.
    Then the target, funds and people are all released.
    """
    ...
```

State the starting facts, the action and the observable outcome. Explain the
rule rather than narrating Python statements. Parameterized methods may name
row inputs in braces, such as `{month}` or `{expected}`. Collection expands these
using that row's explicit inputs and includes the resulting `scenario` in the
JSON case report. Each row retains its own stable case ID, requirement, layer
and outcome. The docstring does not replace assertions or the source requirement.
Collection rejects missing or malformed logic scenarios, so new methods cannot
silently omit their description. Journeys and integration cases retain their
existing metadata; the strict docstring contract applies to the logic layer.

Language selection is a presentation concern. Keep French rule/report assertions
where they establish a French narration or disclosure requirement. Assert
structured facts and stable identifiers for rule outcomes; add explicit
translation tests instead of loosening old expectations or making core tests
depend on the active browser language.

## Every push

With `DATABASE_URL` pointing to a disposable PostgreSQL database whose user can create test databases:

```bash
uv run ruff check .
uv run ruff format --check .
uv run coverage run -m pytest -q -m logic --fail-on-skip --check-case-catalog --case-report=artifacts/core-cases.json
uv run coverage report
uv run coverage json
uv run python manage.py makemigrations --check --dry-run
uv run pytest -q --require-postgresql --fail-on-skip --check-case-catalog --case-report=artifacts/test-cases.json
# With the application running against the development database:
uv run python scripts/browser_smoke.py
```

CI runs all layers on pushes and PRs against PostgreSQL 17 and 18, and uploads the case report even on failure. Required runs reject SQLite, skipped cases and expected failures. Never report a skipped PostgreSQL check as passed. Record the database versions actually verified locally; CI results are separate evidence.

During iteration, `uv run pytest -q -m logic` is the fast pure-core loop. It does not replace the full push checkpoint. Presentation-only changes need no invented game-logic tests, but all existing layers still run before pushing.

## Evidence from this compliance pass

Grouped allocation, siege, raid, target lifecycle, construction timing, authorization, HTTP and calendar checks have independent cases. Additional prescribed-draw military cases cover departure/combat/return accounting, protection boundaries, local stock movements, capture effects and wall repair. Longer invariant/reproducibility journeys are retained separately.

The zero-defender reporting regression was observed failing before its fix: an unopposed encounter claimed to reveal equipment. The corrected report says no defenders were encountered and discloses no equipment. This changes narration only, not combat balance.

## Bilingual folio and Moon regression coverage

Existing exact-date cases explicitly select calendar version one, preserving their original expectations for existing saves. New independent cases cover Moon 1, departure/combat/return dates, twelve-closure harvests, final dates, retries, scheduled closure/pause boundaries, city privacy, translated recipient reports and reopening signed drafts. The two-year calendar equivalence journey compares complete city, order, work, mission, result, report and combat-audit outputs against the established simulation.

The browser smoke runs the full journey in both French and English, changes the language of the same stored letters, and checks 390px and 320px layouts. It uses real forms, CSRF, JavaScript cost estimates and persisted game state. Compile both catalogs before running it.

The realm-wide batch regression starts directly on Decrees, selects two cities, checks the single read-only preview and seals one atomic order. Busy-team exclusion has its own HTTP case. Both browser languages exercise select-all, clear, live batch totals, one seal/cancellation for two cities, and optional city-folio preselection.

## Local forge and mobile folio revision

The 2026-10-19 cases specify city forge quotes at the population floor, equality and above it; version, ownership, team-slot, level and atomic affordability rejections; batch cancellation; frozen prices, completion and capture; mixed expedition strength frozen at departure; local raid/capture defense; mixed relief caps and qualitative encounter reports; private projections and ordinary bot commands. Existing realm-equipment cases explicitly select forge version one, protecting saved reigns rather than changing their expected rules.

Independent bilingual HTTP cases cover the three navigation destinations, active state on secondary folios, public map privacy, local forge preview/seal and legacy snapshots with no forge marker. The browser journey additionally checks live affordability, a local forge batch, city map links, all nine cities fitting at 320px, 44px navigation/map hit areas, compact headers and native construction submission with JavaScript disabled. Screenshots are retained as local test artifacts; they do not replace assertions or the PostgreSQL checkpoint.

## Contextual atlas revision

Independent cases cover stable irregular public geography, bilingual default/own/reachable/unreachable city panels, native raid/capture preselection, and commands hidden for engaged, paused, finished and eliminated states. The existing public-map case now requires no drawn road edges and verifies privacy. The browser journey selects a city in the atlas, checks capture preselection, completes the existing raid journey, and exercises map selection and raid preselection with JavaScript disabled at 320px in both languages. Resource icons retain accessible translated names.

The geography revision separately specifies each realm's five initial targets on the fifteen-road mesh, all connected friendly origins, road uniqueness and maximum degree, plus unchanged legacy-ring projection without a version marker. Existing combat/calendar fixtures explicitly use map version one to preserve their original outcomes; new UI and browser cases exercise version two.

## Named works and merged forge list

Independent cases specify each named upgrade and repair with its exact quote, legacy forge availability at ordinary/reinforced/complete equipment and while busy, bilingual city-forge names, one shared work list for both forge rule versions, and read-only lists for paused/finished reigns. The browser journey checks the single Works heading and named granary/forge captions before its existing batch preview/seal/cancel and no-JavaScript paths.

## Territory map, density and forge affordability

Independent cases specify bounded territory polygons around every city, complete sheet coverage, stable borders on capture, all viewers on legacy/mesh roads, and bilingual committed-target markers for both own and rival cities. Forge cases cover one Measure below, exactly at and above affordability, plus visible/disabled translated submit controls. The browser journey checks keyboard city selection, marker states, 320px/390px account/lobby/game overflow, 16px text and 44px checklist targets, alongside its existing no-JavaScript paths. A separate local Chromium reproduction verifies a legacy forge shortfall and successful read-only preview at exact funds.

## Mixed-stage construction choices and benefits

Independent cases cover ordinary/enlarged/completed granaries in one list, active and sealed team commitments, repair prerequisites and absent/intact walls, exact economic changes and qualitative military benefits, an atomic 1,700,000-Measure mixed-stage batch, and bilingual read-only completed/busy lists. The browser journey completes one granary and reserves another city's forge to check mixed choices, visible benefits and optional builder advice. Computed typography checks ensure visible body text stays smaller than headings, including with enlarged text, and no-JavaScript batch previews remain covered.

## First steps and discoverable accounts

Independent bilingual HTTP cases cover creation-only prologue redirects, each of the four read-only pages, invalid page bounds, membership protection, contextual V0/V1 and manual/scheduled guidance, the unchanged running automatic clock, local available-versus-total city balances, and the validate/review/seal reservation boundary for works, legacy equipment and expeditions. The existing Council ordering case now requires the compact ledger before news.

The browser journey traverses the complete prologue in both languages, checks every page at 320px/390px and enlarged text, and checks guide and replay pages with the existing responsive hierarchy assertions. Native guide/replay/previous/skip/city-folio navigation also runs with JavaScript disabled alongside the existing batch and expedition journeys.
