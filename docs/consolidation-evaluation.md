# Consolidation evaluation — 1 November 2026

These 1,800 simulations do **not** consistently improve the patient policy's
results across decision cadences. They establish observations, not human balance.
No human playtest was performed.

## Method and reproduction

[The evaluator](../scripts/evaluate_consolidation.py) pairs 100 deterministic seeds
and three cyclic role rotations, giving each policy every starting position.
Each cadence has 300 matches per scenario, ending at conquest or Moon 120:
strategy 2; strategy 3; strategy 3 plus offline `experimental_active_walls`.
The experiment adds one percentage point of held-siege attacker losses per wall
level to the normal 2%. It is absent from normal new games.

Policies use validated commands, at most one accepted per decision, and own
resources, public geography/walls and recipient reports. Early expansion captures
from Moon 1; patient counterexpansion from 25, retaining larger reserves and
attempting report-driven supply; seasonal raiding departs at 5/8/11 and captures
from 49. Otherwise they fund works. Every house receives the same cadence;
three-Moon decisions anticipate seasonal windows, sometimes departing earlier.

From the repository root, the exact evaluation commands were:

```sh
UV_CACHE_DIR=/tmp/yaara-uv-cache uv run python scripts/evaluate_consolidation.py --seeds 100 --output artifacts/consolidation-comparison.json > artifacts/consolidation-comparison-summary.json
UV_CACHE_DIR=/tmp/yaara-uv-cache uv run python scripts/evaluate_consolidation.py --seeds 100 --decision-every 3 --output artifacts/consolidation-comparison-every-three.json > artifacts/consolidation-comparison-every-three-summary.json
```

Both runs passed engine invariants. Eight evaluator logic cases, focused lint and
format checks passed. Raw JSON remains in ignored local `artifacts/`.

## Results

Fractional win shares sum to 300 per row. These aggregates happen to be integers.

| Decision every | Scenario | Early wins /300 | Patient wins /300 | Raider wins /300 |
| --- | --- | ---: | ---: | ---: |
| 1 Moon | Baseline | 191 | 101 | 8 |
| 1 Moon | Consolidation | 197 | 89 | 14 |
| 1 Moon | Active-wall experiment | 183 | 101 | 16 |
| 3 Moons | Baseline | 252 | 48 | 0 |
| 3 Moons | Consolidation | 222 | 76 | 2 |
| 3 Moons | Active-wall experiment | 221 | 77 | 2 |

Recovery means regaining a pre-loss city count at a later closed Moon. Raid net is
mean settled loot minus expedition costs and levy forgone during absence;
unreturned loot and casualty valuation are excluded. Blocking counts rejected
validation **attempts**, including repeats, classified by the pending mission kind.

| Cadence / scenario | Recovered / losing houses | Mean raid net | Blocked by raid / capture |
| --- | ---: | ---: | ---: |
| 1 / baseline | 585 / 874 | +146,128 | 0 / 0 |
| 1 / consolidation | 606 / 868 | +239,675 | 98 / 1,430 |
| 1 / active walls | 611 / 867 | +222,945 | 90 / 1,418 |
| 3 / baseline | 485 / 835 | −372,008 | 0 / 0 |
| 3 / consolidation | 606 / 885 | −527,561 | 153 / 226 |
| 3 / active walls | 606 / 885 | −528,148 | 151 / 226 |

Patient accepted orders averaged 38.94→43.98 and 22.92→28.92, baseline→consolidation
at frequent/infrequent cadence. Revised games lasted longer; totals do not measure
attention burden. Frequent-cadence full-conquest endings fell from 285/300 to 237/300.

Active walls caused 9,703 additional attacker deaths in frequent-decision games,
2,470 otherwise. This establishes application, not a desirable human outcome.

## Provenance and limits

Both artifacts record the same source SHA-256 values, verified against the files
after completion, on the candidate based on `fd6890b`:

| Source | SHA-256 |
| --- | --- |
| Evaluator | `429f6a8a2e931c7ef576abf350f146b4c7defc9b97461155040bb8cc7fe1a24c` |
| Engine | `243e6ad8a340afe261b5439b7b023c84254afd7cd11d839f3a9246e744b9da5a` |
| Rules | `3ada147b4ead8962cc978a7b7c196527473966ee788f781b26af7a6b02c2ad4f` |
| Tactics | `40c07f167df382747bf2694431307107fd960b4435708cc5f796c6d68d3904d8` |

Artifact SHA-256: standard
`0c544c53faf0454f4312222c376f79a70ae8ff62ad8fe77535243233810b3f8d`;
three-Moon
`541519443758841e7de3d601d04f3846766b3dbce8b5f587819cfb918087937b`.

Fixed heuristics are not optimized players; correlated rotations and paired seeds
establish no significance claim. Revised effects combine occupation, frozen
funding and exclusivity. Recovery excludes ownership changes reversed within one
closure. Foregone levy may otherwise have overflowed. Seasonal totals do not
isolate late-only raids. Shared infrequent decisions do not model one absent human
against continuously active rivals, or establish login requirements or historical
coefficients.
