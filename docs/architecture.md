# Architecture and working method

One Python/Django application, one PostgreSQL database, and an optional calendar worker.

## Boundaries

- `simulation/rules.py`: pure integer/fraction arithmetic, rule families, capture branches, casualty rounding and proportional allocations.
- `simulation/engine.py`: JSON-compatible simulation aggregate. Cities, graph, reservations, works and expeditions. No ORM, HTTP, clocks or global randomness.
- `simulation/services.py`: authorization, deadlines, transactions, request idempotency, persistence and tick audit.
- `simulation/models.py`: canonical `Game.state` snapshot; relational memberships, receipts, target engagements, tick executions and recipient reports.
- `simulation/multiplayer.py`: locked self-selected admission, private seat credentials and shared calendar start/control. New rooms start at three claimed seats; old rooms retain operator start.
- `simulation/notifications.py`: per-participant confirmed email consent, recipient-report outbox and leased delivery through standard Django mail. Network sends happen outside game transactions and database locks.
- `simulation/projections.py`: explicit player-facing allowlist. Enemy figures and numerical combativity never leave the server. Ranking reveals rank, not enemy population.
- Django templates, translation catalogs, local CSS and progressive JavaScript: French and English UI. `common.css` holds shared primitives; the conventional pre-game layout and manuscript layout each load only their own stylesheet. Partial templates share optional folios, inline batch-work checklists and dedicated action forms, correspondence, closing controls and the footer language switch. JavaScript estimates costs from public rule prices; the server independently validates every request.
- `simulation/calendar.py`: pure compatibility helpers for original elapsed-month snapshots and the version-two open-Moon calendar. The application, scheduler and presentation use the same closure target.
- `simulation/messages.py`: pure, serializable narration expression trees. The raw French title/body remain stored alongside structured report content; `presentation.py` renders the already-authorized projection in the request language. Names and observed values remain literal parameters. Reading or changing languages never rewrites a report.

## Mutation protocol

Every mutation locks `Game` with `select_for_update()` inside `transaction.atomic()`. Authorization and deadlines are checked after obtaining the lock. A single snapshot read gives a coherent game consultation. Reports are immutable records filtered by recipient, not by current city ownership.

Confirmation saves the financing plan, manpower, building slot and target engagement atomically. A `(game, actor, request_id)` receipt makes repeated delivery harmless, including after cancellation. Preview is read-only and signs only the submitted specification, membership, month, revision and request ID. A stale revision requires a fresh preview.

The unique `(game, city_id)` engagement is maintained with the snapshot. It lasts through approach and is released at resolution, invalidation or cancellation. Confirmed orders contain reservations; a realm's stock is always the sum of its city stocks.

Ticks have unique `(game, month)` records. They accrue the previous interval, pay annual tax and demographics, depart orders, finish works, freeze/allocate relief, resolve shuffled combats, return forces, then record eliminations/results. Any failure rolls back the entire month. Retrying a committed month returns that execution. Seeds, accepted orders, rule versions and significant draws are private and retained for diagnosis.

Production requires PostgreSQL. SQLite is a local solo fallback with immediate transactions; it does not demonstrate PostgreSQL locking. Concurrency tests use independent real connections, including a verified database lock wait before deadline rechecking.

## Development method

Follow the standing [pseudo-TDD policy](testing.md): identify use-case variations, write one independent logical test per variation first, use native stubs or direct pure-function inputs, then implement and refactor. PostgreSQL and browser checks supplement those logical tests and run with the full suite on every push. Preserve existing rules for in-progress games. Use new rule versions for incompatible changes.

`AGENTS.md` contains stable commands and constraints. An ordinary focused coding conversation is enough; additional agent orchestration is unnecessary. Keep each change playable and report assumptions, deviations and evidence.

The aggregate suits nine-city, 120-month prototypes. Measure snapshot size and write contention before splitting it into more tables. Human multiplayer uses the existing lobby, separate seat principals, whole-game pauses and recipient-specific letters; no distributed framework is needed.

## Map presentation boundary

`simulation/cartography.py` consumes only the already authorized player projection.
It builds local work choices, own route markers and dated courrier links; it never
reads aggregate opponent state or executes a command. `work_details.html` shares
quote facts between single-city and optional batch preparation. Map, courrier and
review use the same `realm_map.html`; native URLs/forms are the baseline, with
JavaScript adds contextual navigation while retaining the map canvas, indicative
routes, existing cost estimates and local read preferences. The server rechecks
the actual command through existing services.
