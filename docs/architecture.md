# Architecture and working method

One Python/Django application, one PostgreSQL database, and an optional calendar worker.

## Boundaries

- `simulation/rules.py`: pure integer/fraction arithmetic, rule families, capture branches, casualty rounding and proportional allocations.
- `simulation/engine.py`: JSON-compatible simulation aggregate. Cities, graph, reservations, works and expeditions. No ORM, HTTP, clocks or global randomness.
- `simulation/services.py`: authorization, deadlines, transactions, request idempotency, persistence and tick audit.
- `simulation/models.py`: canonical `Game.state` snapshot; relational memberships, receipts, target engagements, tick executions and recipient reports.
- `simulation/projections.py`: explicit player-facing allowlist. Enemy figures and numerical combativity never leave the server. Ranking reveals rank, not enemy population.
- Django templates, local CSS and progressive JavaScript: French/English UI with gettext. The pure core emits canonical French messages with serializable presentation descriptions; only the application boundary chooses the display language. See [localization](localization.md). JavaScript estimates costs; the server independently validates every request.

## Mutation protocol

Every mutation locks `Game` with `select_for_update()` inside `transaction.atomic()`. Authorization and deadlines are checked after obtaining the lock. A single snapshot read gives a coherent game consultation. Reports are immutable records filtered by recipient, not by current city ownership.

Confirmation saves the financing plan, manpower, building slot and target engagement atomically. A `(game, actor, request_id)` receipt makes repeated delivery harmless, including after cancellation. Preview is read-only and signs only the submitted specification, membership, month, revision and request ID. A stale revision requires a fresh preview.

The unique `(game, city_id)` engagement is maintained with the snapshot. It lasts through approach and is released at resolution, invalidation or cancellation. Confirmed orders contain reservations; a realm's stock is always the sum of its city stocks.

Ticks have unique `(game, month)` records. They accrue the previous interval, pay annual tax and demographics, depart orders, finish works, freeze/allocate relief, resolve shuffled combats, return forces, then record eliminations/results. Any failure rolls back the entire month. Retrying a committed month returns that execution. Seeds, accepted orders, rule versions and significant draws are private and retained for diagnosis.

Production requires PostgreSQL. SQLite is a local solo fallback with immediate transactions; it does not demonstrate PostgreSQL locking. Concurrency tests use independent real connections, including a verified database lock wait before deadline rechecking.

## Development method

Follow the standing [pseudo-TDD policy](testing.md): identify use-case variations, write one independent logical test per variation first, use native stubs or direct pure-function inputs, then implement and refactor. PostgreSQL and browser checks supplement those logical tests and run with the full suite on every push. Preserve existing rules for in-progress games. Use new rule versions for incompatible changes.

`AGENTS.md` contains stable commands and constraints. An ordinary focused coding conversation is enough; additional agent orchestration is unnecessary. Keep each change playable and report assumptions, deviations and evidence.

The aggregate suits nine-city, 120-month prototypes. Measure snapshot size and write contention before splitting it into more tables. Human multiplayer still needs a lobby/membership workflow and coordinated pause/readiness rules; this delivery creates private, unranked solo games.
