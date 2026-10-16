# Test-first development policy

The owner's policy is a standing requirement. Its basis is the design dossier, §26, plus the explicit requirement for one logical test per use-case variation. Conversation and test code are English; player-facing copy supports French and English, with canonical French engine messages preserved.

## Working sequence

1. Read the relevant rule. List its normal, rejection and boundary variations before editing behavior. Give each variation a stable case ID and a concrete expected outcome derived from the dossier or an explicit product decision, not from the implementation's output.
2. Write one independently collected logical test per variation. Parameter rows are separate cases with readable IDs. Several assertions may establish one outcome and its invariants; do not split one outcome into a test per assertion.
3. For new or corrected behavior, run the case first and observe the intended failure. Implement the smallest coherent solution and rerun it. Writing a good implementation on the first attempt is welcome; do not add artificial iterations.
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
