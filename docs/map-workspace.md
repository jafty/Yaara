# Map workspace — October 26, 2026

The owner's approval supersedes earlier Council-first and compulsory batch-work
presentation decisions. No saved rules or reports change. New artwork is deferred.

## Interaction contract

- Entry opens all nine cities and every saved road. No map zoom; browser zoom stays enabled.
- Selecting an owned city opens stocks, troops, capabilities and local work quotes
  together. A reachable enemy opens preparation directly. Convoys and detailed
  accounts remain deliberate activities in the same workspace. The map
  fills the available play area. Context panels overlay the board on the
  right on desktop and rise from the bottom on mobile; no reserved side column.
  Progressive context navigation retains the map canvas and supports browser Back.
- Local works show only that city's next quote and use a hidden city field, never
  a compulsory checklist. Switching cities preserves the work family, not a draft.
  The realm catalogue remains a secondary batch convenience.
- Preview is read-only, in the map workspace. Seal reserves; closure spends.
  Existing services revalidate authorization, deadlines, funding and reachability.
- Own sealed, outbound and returning expeditions have separate map states. Draft
  routes use the public friendly graph and automatic frontier rule. Enemy warnings
  identify only the threatened city and intelligence already projected to its owner.
- Courrier has À traiter, Échéances and Chronique. Actionable items retain short
  scribe prose and existing artwork. Idle teams are not warnings. Repairs already
  commissioned move to the schedule. Forecast overflow is a warning with its date.
- Each event links to its precise work, expedition, order or account. Reading
  recipient reports clears only local unread state, never an unresolved warning.
- French and English, native forms without JavaScript, keyboard focus, enlarged
  text, 320px mobile and late-game ownership remain supported.

## Independent variations, specified before implementation

`map-workspace-entry`: default board and all twelve current roads, both languages.
`map-local-work`: local quote submits exactly one city without a checkbox.
`map-switch-family`: another owned city retains the family but no manpower draft.
`map-preview-context`: quote retains map and city, with no state mutation.
`map-mail-route`: schedule links to an existing mission rather than a new attack.
`map-attention-overflow`: forecast loss is dated and opens stocks.
`map-attention-repair`: commissioned repair moves out of action-required items.
`map-public-intelligence`: unknown enemy origin never becomes a map arrow.
`map-own-route-projection`: own mission route and identity survive departure.
`map-mail-invalid`: unknown mailbox section rejected.
`map-readonly-actions`: paused, finished and eliminated houses cannot submit local
work, convoy or expedition forms.
`map-conquered-city`: a conquered city exposes its new owner's local work choices
and the inherited contingent's departure restriction.
Browser: local work review/seal/cancel; multi-origin raid; precise mail jump;
keyboard/native forms; narrow and enlarged text; persistent warning after reading;
calendar refresh on contextual navigation; legacy batch and recruitment journeys.

Full local checkpoint selected because shared flows and disclosure are affected.

## October 27 — Furnished mockup as the UX baseline

The owner rejected the first implementation's distance from the supplied HTML.
Use its house/resource header, top house legend, city working sheets, direct
raid/capture preparation and separate Courrier window. Retain the existing stone,
mineral-green, terracotta and house colors. `workspace.css` owns this layout; the
previous workspace rules are removed from `manuscript.css`, which retains shared
map drawing, forms and secondary folios. One sheet heading/body structure serves
cities, mail and review.

Each local work row can request the existing server preview directly. Its family
link retains the full quote and illustration. Stock occupancy, reservations and
forecast harvest stay distinct. Crew assignments link to their existing orders or
works; active work is never falsely offered a cancellation the engine cannot make.
Native troop numbers remain usable without JavaScript; optional sliders and step
buttons synchronize those inputs and the existing funding calculation.

Earlier recommendations still apply: no unnecessary map zoom, no idle-team alert,
no enemy route disclosure or numerical combativity, precise mail links, separate
action-required/schedule/archive, and review before sealing. The mockup's invented
prices, territories, instant commands and hidden intelligence are not imported.
Native forms, browser zoom, selection and keyboard navigation remain available.

Independent variations: `mockup-house-hud` (both languages),
`mockup-city-direct-work` (both languages), `mockup-city-work-availability`
(poor/busy/paused), `mockup-enemy-direct-preparation` (both languages),
`mockup-enemy-unreachable`, and `mockup-mail-frame` (all three sections).
The browser journey additionally checks the range/number/step/max controls, native
forms, scrolling sheet bodies with an accessible close control, and 200% text.
Full verification applies to this broad shared-template refactor.
