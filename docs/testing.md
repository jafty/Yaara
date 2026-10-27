# Test-first development policy

## Approved audit revision

Independent audit cases cover versioned yields at every level, saved economies without a marker, exact local affordability, atomic batch and expedition shortfalls, per-origin fixed-fee rounding, local debits and cancellation, each realm's two initial frontiers, further reach after capture, engagement ownership without hidden identifiers, and defender reports with public identity and survivor-dependent estimates. Existing cases explicitly select the old economy/map where they protect saved rules rather than new-game defaults.

HTTP acceptance cases cover idempotent authorized calendar start, POST-only mutation, cron execution without a browser and repeated-run safety, full-report anchors, news-first Council accounts with a jump link, and closure-review links on the main folios. Browser journeys exercise the new local-funding shortfall, two-target geography and batch workflows in both languages with JavaScript, no JavaScript, narrow screens and enlarged text. CI retains the full core coverage and PostgreSQL checkpoints; local selection follows the verification levels below.

The owner's policy is a standing requirement. Its basis is the design dossier, §26, plus the explicit requirement for one logical test per use-case variation. Conversation and test code are English; player-facing copy supports French and English, with canonical French engine messages preserved.

## Working sequence

1. Read the relevant rule. List its normal, rejection and boundary variations before editing behavior. Give each variation a stable case ID and a concrete expected outcome derived from the dossier or an explicit product decision, not from the implementation's output.
2. Write one independently collected logical test per variation. Parameter rows are separate cases with readable IDs. Several assertions may establish one outcome and its invariants; do not split one outcome into a test per assertion.
3. For new or corrected behavior, define the expected contract before implementing it. A failing regression is useful evidence when correcting a defect. Implement the smallest coherent solution and rerun the cases. Actual red-green baby steps and deliberately naive intermediate implementations are not required; do not manufacture failures when adding coverage for existing correct behavior.
4. Refactor only for a concrete benefit: clearer rules, less duplication, easier isolation, or an observed defect. AI does not make a test/code pair automatically correct. Both can share a mistaken assumption; compare expected results with the source and retain cross-cutting invariants.
5. Run affected checks during development, then the applicable local verification level before pushing. Keep the full CI checkpoint on every push and PR. Add the new IDs to the reviewed case catalog and inspect its diff. Summarize behavior changes and actual verification.

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

## Local verification levels

The owner's next proportional-map revision is Presentation work: templates, CSS,
shared context navigation and localized copy, with no simulation or persistence
change. New bilingual contracts cover focused action folios, native 680:500 map
frames, conquest labels/icons, square list art, rectangular detail art, and arrow-free
UI. Existing comparison expectations change only at the translated HTTP boundary;
core message identities retain their previous expectations. Browser checks verify
unchanged map dimensions between contexts, full-screen mobile forms with direct
return, native controls, enlarged text and paired cost/duration values. Recruitment
journeys additionally cover shared pre-game templates after arrow removal.

The latest October 27 mobile-planning revision adds eighteen bilingual presentation
variations for expandable frames, native army totals, envelope alerts, convoy fields
and compact city/owner headings, plus free local means after reservations. Resource-label expectations follow the owner's
new icon/value header with accessible captions. The browser journey checks normal
text separately from 200% reflow, integrated troop controls, preserved counts through
expansion, an unobscured external summary, native form-associated submission and
consistent convoy fields. Two stale map assertions now check only public marker
coordinates in inline styles and house emblems in the existing map guide, instead
of requiring the older in-map legend. No privacy expectation is relaxed. Full local
verification is selected after discovering those baseline test mismatches.
The final component review removes the city meter and repeated capabilities,
replaces stock/troop cards with one ledger row, and removes troop sliders.
Native number controls, accounts, warnings and per-work effects retain their
contracts; browser checks exercise the actual controls.

The light redesign adds independent bilingual contracts for news/date/account order,
visible resource captions with retained icons, immutable report reading order, native
optional map explanations, individually named work quotes, and direct batch selection.
The existing navigation variations now require the parent destination on secondary
folios; their changed expectation is reflected in the reviewed case catalog. The shared
browser journey retains the full existing play flow and adds 200% text reflow checks,
native legend operation and restrained report proportions. This is Presentation work;
simulation rules, authorization and stored data remain unchanged.

The October 23 presentation fixes add independent bilingual alert-destination cases for defense, reserves, each repair family and sealed/active tracking. Completion artwork cases cover each current building level, repaired families, original vocabulary and legacy equipment in Council and full letters; unknown and unstructured archives retain neutral scenes. Stored report content remains unchanged. The shared bilingual browser journey checks native defense/granary fragments above the fold below the sticky header on desktop, 320px/390px, enlarged text and without JavaScript, plus a decoded granary image from an actual completed work.

The owner's 2026-10-19 follow-up replaces the blanket full-local-suite requirement with risk-based local verification. Choose by affected behavior, not line count or perceived coding difficulty. State the chosen level and the tests run in the delivery summary. Mixed changes use the highest applicable level; unclear impact, unexpected failures or a broad refactor escalate to the full checkpoint. Fix failures before pushing.

| Level | Applies to | Local checks before pushing |
| --- | --- | --- |
| Presentation | Templates, CSS, display-only navigation, translations and documentation; no game rules, authorization or persistence behavior changes | Lint/format, full case-catalog collection, affected HTTP/presentation cases on real PostgreSQL. Compile catalogs for copy changes. Run the browser smoke for layout, navigation, forms or JavaScript changes. Documentation-only edits need relevant consistency checks rather than invented behavior tests. |
| Behavior | Native game rules, projections, narration or application behavior with bounded impact, without a high-risk boundary below | Presentation checks where relevant, the complete database-free core suite with 100% statement/branch coverage, and affected integration/journey cases on real PostgreSQL. Run browser smoke when player flows change. |
| Full | Schema/migrations, transaction boundaries, locking/concurrency, authorization/privacy, calendar/scheduler behavior, dependencies, runtime/deployment or CI/check infrastructure; changes with unclear reach | The complete local checkpoint below, including the real PostgreSQL suite and bilingual browser smoke. |

Existing test layers and one-case-per-variation traceability stay unchanged. Add independent regression cases for changed behavior; presentation work needs no invented simulation cases. Pure-core iteration still uses `uv run pytest -q -m logic`. A small display fix does not require rerunning unaffected simulation coverage locally.

All code levels run these inexpensive checks:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest --collect-only -q --check-case-catalog
```

Then run the explicitly selected cases. For example, the bottom-menu display fix uses:

```bash
# DATABASE_URL points to a disposable real PostgreSQL database.
uv run pytest -q tests/test_mobile_folios.py -k navigation --require-postgresql --fail-on-skip
# With the local application running:
uv run python scripts/browser_smoke.py
```

Check the full catalog in its separate full-collection command: passing a test file together with `--check-case-catalog` correctly reports all uncollected files as missing. Use `--fail-on-skip` for selected executions. Do not treat unexecuted tests as passes. Review case-catalog changes whenever variations change.

The existing browser smoke runs the complete bilingual game journey. The recruitment smoke uses the same Playwright framework and adds guest persistence, operator management, three independent seat contexts, returning invitations and guest/seat handoff. Both run in CI; keep the existing game journey when changing shared layout, navigation, forms or JavaScript.

For browser verification, start the local server with `python manage.py runserver 127.0.0.1:8000 --noreload --nothreading`. Django's default development request threads otherwise accumulate persistent PostgreSQL connections during multi-context polling. Production uses the bounded Gunicorn worker/thread pool in `scripts/start.sh`.

For the behavior level, add the independent core coverage gate from the preceding section, then explicitly select affected application and journey tests. No automatic file-to-test inference is used: inspect shared callers, rejection paths and boundaries to choose cases, escalating when coverage of the impact is uncertain.

## Full local checkpoint and every CI push

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
uv run python scripts/recruitment_browser_smoke.py
```

CI runs all layers on pushes and PRs against PostgreSQL 17 and 18, and uploads the case report even on failure. Required runs reject SQLite, skipped cases and expected failures. Never report a skipped PostgreSQL check as passed. Record the database versions actually verified locally; CI results are separate evidence.

The full checkpoint is mandatory locally for the Full level and in CI on every push and PR. Presentation and Behavior changes may push after their applicable local checks; report CI results separately from local evidence. CI executes every layer and both browser journeys on PostgreSQL 17 and 18.

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

## Review remarks

Raid cash-report cases separately specify military success with provisional deficit, equality and gain, defeat without reimbursement, saved pooled versus local funding, bilingual replay, and final retained cash after normal deposits, overflow, one or all origins changing owner, and annihilation. Recipient checks allow the initiating house's known historical payments while withholding them from other owners' local return letters. HTTP and browser cases require exact payer shares and both provisional/final balances; Council previews must expose the balance before truncation. Forge cases pin ordinary/reinforced/superior mixed strengths and prove that local and legacy realm equipment never stack. This change uses the Full local checkpoint because return recipients and report disclosure are affected.

Independent Moon-news cases cover complete last-Moon news (including 105 events and full archive anchors), quiet Moons, initial letters, bilingual running/final Moon numbers, local accrued levies and each report icon. Native cases cover a three-origin return, current-owner recipient separation, distinct simultaneous expeditions and an empty origin, with deposits, survivors, translated city accounts and retry safety preserved. Existing annihilation and overflow cases retain their independent contracts. The shared bilingual browser journey checks the three compact header values and crescent across its normal, narrow, enlarged-text and no-JavaScript paths. This revision uses the Full local checkpoint to verify recipient-scoped return aggregation.

Independent cases reproduce empty-granary 30-person raid allocation and exact affordability, every twelve-road border adjacency, both territory tilings, failed preparation/confirmation and signed-draft reopening, retained native form costs, prologue action order, report return links, and five/ten-minute calendar boundaries including exact marks, fractional seconds, hour rollover and pause/resume. The bilingual browser journey checks Council link gaps, live Hamilton shares and shortfalls, failed capture recovery, report return links and the explicit aligned start. Core coverage and the full PostgreSQL checkpoint remain required in CI and for the Full local level.

## Seasonal playability revision

The October 20 change uses the Full checkpoint. Existing scenarios explicitly pin their historical economy rather than silently changing their expected balances. New default-economy cases independently cover every catalogue quote/completion, crop yield, local batch rejection, watch mobilization, sheltered/empty crops, annual raid accounting, arrival-based respite, frozen mixed transport/siege, fortification coefficients, supply equality and shortage, repair opportunity costs, and bot own-state constraints/privacy. Updated HTTP and browser scenarios follow family pages and native radio controls; signed review, atomic sealing, cancellation, narrow/enlarged layouts, no-JavaScript forms and both languages remain covered. The backlog and current gameplay reference distinguish implemented rules from deferred designs. Historical ratio claims do not substitute for arithmetic tests.


## Strategic preparation revision — October 22

This change uses the Full checkpoint. Independent strategy cases specify new/legacy initial reserves and tariffs, exact raid force boundaries, protection and survival caps, witness bands, bounded noncombat losses (including absent relief), exterior damage without retroactivity, rational wall integrity, strict 500-Measure siege sufficiency, threatened-city relief exclusion, repairs and the configured reign horizon. Convoy and contingent cases cover local reservations, overflow, one-time diversion, loss of a refuge during travel, mixed arrival dates and allegiance/population conservation. Privacy cases mutate hidden enemy accounts and verify unchanged public projections; HTTP cases read only recipient-scoped stored observations. Older economy cases explicitly pin their historical rules.

The bilingual browser journey uses the current affordable prices, validates an undersized capture's form recovery, checks the native help disclosure by keyboard, and retains its multi-city, no-JavaScript, 320px and enlarged-text paths. `scripts/evaluate_strategy.py` separately records observable outcomes over complete simulated reigns; those bot observations are not proof of human strategic balance.

Human-opening cases separately specify same-army siege repetition, alternating army waves, preemptive versus late convoys, border counterattacks cutting routes, and early versus pre-harvest raids. They use ordinary commands and fixed plans independent of the bot policy. Native convoy review/seal/cancellation and ledger-note keyboard operation run without JavaScript in both browser languages.

Local evidence for this increment: 1,123 tests passed on disposable PostgreSQL 17.11, including 624 database-free logic cases with 100% core statement and branch coverage. The case catalog adds 146 independent variations without removing existing IDs. The final bilingual browser journey passes, including native convoys, keyboard disclosures, 320px layouts, enlarged text and no-JavaScript forms. Catalog compilation, lint/format, migration dry-run and the frozen production dependency comparison pass. CI still runs every layer on PostgreSQL 17 and 18; local PostgreSQL 17 evidence is not a claim about CI or Railway.

## Compact preparation and desktop folios — October 22

Presentation regressions cover collapsed origin details with visible funding/warnings, native mixed-transport ceilings, selected-city connections from each saved road network, and city-labelled ongoing works before the catalogue. Existing bilingual letters now assert the approved foray/pillage terminology. The browser journey verifies adjacent desktop map/preparation, the retained stacked mobile flow, upright legends, keyboard and no-JavaScript origin disclosures, 320px/390px layouts, enlarged text, live capacity changes and capture hiding loot information. This is a Presentation change; simulation, transactions and saved data are unchanged.

## Incoming threats and crew availability — October 22

Bilingual presentation cases cover quiet/confirmed/active/paused/cancelled/resolved/finished/outgoing expedition states on Council, Expeditions and Works, with unchanged saves and warnings limited to existing owned-city engagement flags. Crew cases cover free, sealed, active, completed and cancelled construction in city-account headings and work-selection lists. The shared browser journey checks translated crew labels with JavaScript and native forms; an additional real-server browser reproduction verifies enemy-warning links, desktop/320px/390px layouts, enlarged text and keyboard operation in both languages with and without JavaScript. Presentation verification applies; there is no new disclosure or game rule.

## Named crew assignments — October 22

Twelve independent bilingual HTTP variations specify sealed and active irrigation, arsenal and initial-defence repair commitments. Council, city details and work-selection lists must show the same specific work, phase, completion Moon and correct register link; city details also show the start Moon. Existing cancellation/completion cases require the stale assignment to disappear. The unchanged-save assertion protects read-only rendering. The shared bilingual browser journey checks named reserved crews across all three surfaces, narrow/enlarged layouts and native no-JavaScript forms. This remains Presentation work; core projections and simulation behavior are unchanged.

## Persistent alert centre — October 22

Twenty-eight bilingual HTTP cases specify walls/watch/shelter damage, repair-needed/sealed/active/cancelled/completed states, empty and combined alerts, pause and completion, hidden rival damage and legacy walls. They verify counts, ordered issue kinds, direct repair links, damage markers, repair tracking and read-only saves. The existing incoming-threat lifecycle cases now exercise the centralized markup. The shared browser journey checks the header link's native disclosure behavior in both languages, including JavaScript disabled; the additional real-server journey completes a repair from its alert and checks damage clearing, four simultaneous issues, 320px/390px/desktop layouts and enlarged text. This is presentation work using already authorized city facts.

## Retroactive compact archive

Ten independent compact-export cases cover player/all scopes, unchanged stored history,
missing accounts, city and order transitions, final-only cancelled orders, completion,
outsider/member access and authentication. The bilingual browser journey downloads both
JSON formats and compares their letters. The existing polling fixture now supplies the
empty authorized alert collections expected by the current manuscript. The creation
assertion excludes the random hidden CSRF input when checking for forbidden visible
V0/V1 labels, avoiding token-dependent false failures.

## Guest recruitment, shared reigns and quiet oasis presentation — October 24

This release uses the Full checkpoint. Ninety-eight new collected variations cover guest creation, retention, account attachment and cleanup; private invitation entry, revocation and concurrency; three-house scheduling and per-player revisions; bilingual first-order guidance; and private-link redaction in deployment logs. Existing case IDs are retained. The anonymous JavaScript-catalog regression also protects the middleware's database-free anonymous path.

The original browser journey retains the complete game flow and now checks the approved paper palette, readable contrast and optional book exports. The additional recruitment journey uses independent browser contexts for all three players, verifies live admin readiness and automatic lobby-to-Council navigation, preserves the playing operator's account, and restores an original guest solo after shared-seat entry. It also exercises saved guest progress, returning links, actual clipboard contents, French/English, native forms without JavaScript, narrow screens and enlarged text. Neither automated journey establishes human enjoyment or multiplayer balance.

Local release evidence: 1,552 tests passed without skips on disposable PostgreSQL 17, including 678 database-free logic cases and 100% native-core statement/branch coverage. Both bilingual browser journeys passed, with the final recruitment run using the CI server configuration above. Catalog compilation, lint/format, migration consistency, static collection and the frozen production dependency export comparison passed. These results do not attest a Railway deployment or a production scheduler configuration.

## October 26 map workspace

`docs/map-workspace.md` records the variations before implementation. New independent
HTTP contracts cover local quotes, review context, precise schedule links, overflow,
commissioned repairs, rejected mailbox sections, read-only phases, conquered cities
and private enemy origins. A native
logic contract covers own route metadata without widening opponent disclosures.
The default entry is tested in both languages. Existing Council/report tests now
request the retained Reign view explicitly; navigation and road emphasis expectations
follow the newly approved contract. No old financial, command or privacy assertion
is removed. `scripts/map_browser_smoke.py` supplements the existing full browser
journey and runs from it, covering bilingual desktop/mobile, 200% text, native forms,
local seal/cancel, a multi-origin raid, schedule links and browser-local read state.

Local evidence: 1,663 cases passed without skips on disposable PostgreSQL 17,
including 24 added variations. The 679 database-free logic cases retain 100%
native-core statement and branch coverage. Final focused map/projection/polling
checks passed 27 cases after the last presentation adjustments. Catalog compilation,
lint/format, migration consistency, static collection and the frozen production
dependency comparison pass. These checks do not establish a Railway deployment.
Both complete browser journeys pass in French and English, including recruitment,
legacy batch actions, native forms and the new map journey. The map checks also
verify a retained canvas, Escape/Back navigation, calendar refresh, and mail panels
bounded by the available board at 200% text size.

## October 27 mockup-led working sheets

The furnished mockup is the UX baseline while the prior recommendations and
current palette/mechanics remain binding. Thirteen independent presentation
variations cover house/harvest identity, direct local work access, poor/busy/paused
availability, direct reachable-enemy preparation, unreachable privacy, and all
three mailbox sections. Existing local-quote cases also assert the selected city
and work family, protecting contextual-navigation continuity.

The map browser journey verifies optional slider/number/step/maximum synchronization,
native forms without JavaScript, retained map identity, fixed close controls,
independent sheet scrolling and 200% text. Shared browser selectors distinguish
submit buttons from the new optional contingent controls. Complete game and
recruitment journeys are retained. The previous workspace CSS and obsolete local
branches in the batch/expedition form are removed, not left behind as overrides.

Full verification is selected for the shared-template refactor. Local evidence:
1,676 cases on disposable PostgreSQL 17; 679 database-free logic cases with 100%
native-core statement and branch coverage; bilingual game, map and recruitment
browser journeys. Translation compilation, lint/format, migration consistency,
static collection and the frozen dependency comparison pass. The new workspace
stylesheet's class selectors all have template or JavaScript references. A direct
browser reproduction also checks city-row preview/seal and non-overlapping status
messages after returning to the map. This is local evidence, not Railway health.

## October 27 — Organic map, illustrated cities and continuous sheets

The owner's follow-ups replace the bottom menu, geometric city sprites and circle
bases. Independent presentation cases cover header destinations, fixed activity
tabs, seven current/legacy fortification drawings, reversible shared boundaries,
three saved networks and selected-city roads. The new geometry remains a
presentation concern; PostgreSQL snapshots, movement rules and the core projection
contract are unchanged. Test selectors follow the shared header and new map key,
while preserving resource, Moon, ownership and engagement assertions.

Browser regressions check retained sheet/art nodes, Construire at scroll zero,
reduced motion, hidden default roads, and native order/recruitment flows. At 200%
text on narrow screens, city/mail sheets can cover the header and must retain a
usable scroll body and visible tabs/close controls. Fragment navigation waits for
font reflow and measures the actual header. Geometry assertions wait for entry
animations to settle instead of inspecting an intermediate frame.

Local database evidence: 1,699 cases passed against disposable PostgreSQL 17.
The unchanged native core also passed all 679 logic cases with 100% statement and
branch coverage. Map journeys passed in French and English, with and without
JavaScript; recruitment journeys passed in both languages. Translation compilation,
lint/format, reviewed case collection, migration consistency and static collection
passed. These local checks do not establish Railway deployment health.
The complete bilingual game browser journey also passed, including the retained
batch/expedition flows and the updated map journey. Thirty-six repeated native
fragment/reflow checks additionally verified same-document navigation after
header and text-size changes.

## City action menu and news — October 27

The city menu, persistent available resources, full-sheet actions, mailbox order,
alert destinations and owned/rival territory presentation use the presentation
checkpoint. The reviewed catalog remains unchanged. The complete suite passed
1,750 cases against disposable PostgreSQL 17 with no skips; bilingual browser
and map journeys passed with and without JavaScript. The map journey covers
phone widths, enlarged text and reduced motion. Catalog compilation, lint and
format checks, and migration consistency also passed. These results do not
establish Railway deployment health.

## City panel refinement — October 27

The presentation checkpoint covers the stacked city actions, return-only city
navigation, compact resource row, direct alert links to accounts, opaque sheet
content and reload on a changed asset set. The affected PostgreSQL 17 checks
passed 161 cases; all 1,750 catalog entries collected. The bilingual browser
journey and map journey passed, including no-JavaScript, reduced motion,
large text and narrow screens. Translations, lint, format and diff checks
passed. Railway status remains separate from local verification.

## Local city briefing — October 27

Presentation verification passed 93 PostgreSQL 17 cases, including sixteen new
bilingual variations for free/sealed/active teams and sealed/active local
expeditions and convoys. The catalog contains 1,766 collected variations. The
complete bilingual browser and map journeys passed with native and JavaScript
navigation, narrow screens and enlarged text. Rules and archived reports are
unchanged; no native-core documentation change is required. A mobile inspection
also verified the occupied team's assignment, dates and unboxed command rows.

## Compact city panel — October 27

Presentation verification passed 72 PostgreSQL 17 cases, the case catalog, and
bilingual browser and map journeys. The map journey checks that a sealed-order
notice does not cover the map; a mobile inspection covered the occupied team,
finish date, population and defenses. Translation compilation, lint and format
checks passed. Game rules and archived reports are unchanged.

## City work wording and compact resources — October 27

The presentation checkpoint covers the compact resource row, total and available
stock, assigned-work name and finish date, suppression of repeated work dates and
the closure notice, and translated improvement and repair actions. The affected
PostgreSQL 17 checks passed 159 cases; the two new repair-label variations were
reviewed in the case catalog. French and English browser journeys cover narrow
screens, enlarged text, keyboard and native navigation. A 320px reserved-stock
inspection verified the resource row and aligned team name. No game rules or
archived reports changed.

## City description copy — October 27

The convoy label and removal of visible fortification labels passed 201 affected
PostgreSQL 17 cases and the bilingual browser and map journeys. A focused
sixteen-case rerun checks the convoy label within the city action menu and the
briefing text. The reviewed case catalog remains unchanged. Accessible map
labels and damage warnings remain available; game rules are unchanged.
