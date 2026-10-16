# Implementation decisions

## 2026-10-15 — First playable release

The supplied French design dossier is retained verbatim as `design-source.fr.md`.

- Adopt its coherent proposed defaults for this prototype: 600,000 Mesures per city; pooled proportional financing even across disconnected holdings; monthly tax accrual with annual local payment; raid/capture minima 20/80; population tiebreaker. These are configurable per new game and are not claimed to have been previously approved as final balance.
- Implement both rule families. V0 has irreversible confirmation, first-level canals/walls, no growth, and no siege. V1 adds cancellation before closure, growth, siege, storage, repairs, higher upgrades and realm equipment.
- Solo games have two deterministic, modest computer opponents, or passive opponents for rule exploration. Bots submit normal validated orders and use their own resources and public geography; they do not read hidden enemy strength/stocks to choose targets. They act at closure after the human's decision window, so solo target priority favors the human. These games are unranked.
- A manual month button is the default. Optional scheduled solo games use a shared worker, a five/ten-minute cadence, and whole-game pause; excessive scheduler lateness pauses the game instead of silently consuming decision windows.
- Users can own multiple isolated solo games. Human-versus-human joining, competitive rankings, diplomacy and administrative world edits are not part of this first delivery.
- Store the small simulation aggregate as a versioned JSON snapshot in one locked PostgreSQL `Game` row. Keep account memberships, idempotency receipts, unique target engagements, tick audit records and recipient reports relational. This keeps the pure engine directly testable; split high-volume simulation entities into tables if scale justifies it.
- Match the document's strict combat comparisons, half-up casualty rounding and largest-remainder allocations. Freeze equipment with an expedition at departure and with relief at allocation; this makes a command's combat equipment stable in transit. Newly acquired residents use their current ruler's equipment for new operations.
- Siege subsistence counts residents physically present after temporary relief departures. Relief returning after all battles joins the current ruler of its origin, as do expedition survivors and their loot.
- Cancelled/retried commands retain their request receipts. A new attempt requires a new request ID; duplicate HTTP delivery never re-reserves released resources.
- No rule rebalancing is justified before playtesting. The long first-harvest wait is preserved; manual mode makes it practical to explore.

## 2026-10-16 — A plain manuscript for play

- The in-game experience is a quiet, white manuscript with a single reading column, serif typography and French scribe narration. City accounts, letters and decree choices unfold as accessible native disclosures. No images, parchment texture, illustrated map, dashboard cards or application sidebar are used in play.
- Pre-game account and reign-selection pages retain their existing layout. A separate manuscript template and stylesheet keep the two experiences independent.
- Decree previews read as dictated instructions while preserving exact prices, funding shares, troop origins, departure/combat/return dates and cancellation consequences. The month closes only through the existing explicit action.
- New reports use the scribe's voice and French number grouping. Existing stored reports remain intact; presentation changes do not rewrite archives or reveal new opponent information. No simulation parameters or outcomes change.

## 2026-10-16 — Language choice and readable logic cases

- Support French and English with Django language selection and gettext catalogs. French remains the canonical simulation narration; browser language does not affect game logic or existing French assertions. Player-supplied and stored names are not translated.
- Store new report message descriptions alongside original French prose, using only the same recipient-visible facts. Render on read in the chosen language; leave older archives verbatim. This extends the report schema without changing simulation state or rules.
- Use explicit passé composé phrases for completed works and separate phrases for work begun. A proposed action remains in the infinitive.
- Document every logic method with strict English Given/When/Then docstrings, enforced at collection and expanded per parameter row in the existing JSON case report. Keep pytest, stable IDs and the pseudo-TDD workflow; no second scenario runner is needed.
