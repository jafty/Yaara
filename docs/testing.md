# Established pseudo-TDD policy

The project owner's test-first policy is a standing requirement, not a new optional recommendation. The design dossier's section 26 explains native stubs, direct pure-function inputs, integration tests and invariants. The owner's clarification explicitly requires one logical test per use-case variation.

## Logical use cases

1. Identify the use case and name each specified variation, including relevant rejection and boundary cases.
2. Write an independent logical test for each variation before implementing or changing its behavior. Verify that the test fails for the intended missing or incorrect behavior, rather than an unrelated setup error.
3. Implement the smallest coherent behavior that satisfies those cases, then refactor while keeping them green.
4. Keep the variation-to-test relationship explicit in names or parameter IDs. Each pytest parameter row is an independent collected case. Several assertions may establish one outcome and its invariants; they do not require several artificial tests.
5. Keep broader journey and integration checks as additional coverage. They do not replace individually identifiable logical variation tests.

Use fixed inputs directly for pure functions. When a use case depends on an external collaborator, use a small native Python stub returning the specified data. A stub does not implement an in-memory database or invent the collaborator's production behavior. Reuse fixed fixtures/stubs across tests where useful. Do not introduce a separate stub framework merely to satisfy this policy.

Use real PostgreSQL connections to establish locking, rollback, concurrent confirmations and database constraints. Failure injection in integration tests may substitute a failing boundary; it does not prove a database property on its own.

## Every push

Run the full existing pytest suite against PostgreSQL and the browser smoke, with the application running against the intended development database. CI runs these checks on both pushes and PRs, currently against PostgreSQL 17 and 18. Preserve all layers; do not silently reduce frequency or treat a skipped database check as passed. Record what actually ran and which database versions were verified locally.

Formatting or presentation-only changes need no invented game-logic tests, but existing regression checks still run at the push checkpoint.

## Current suite and traceability

The initial suite contains parameterized boundary tests and broader tests that group multiple logical variations, such as allocation examples, siege outcomes and confirmation/cancellation/idempotency. Passing that suite establishes the checks it contains; it does not establish strict one-to-one compliance or prove that all tests were historically written first.

Existing grouped logical cases need an explicit traceability/refactoring pass before the whole suite can be described as strictly one-to-one. Retain their assertions and integration coverage during that pass. Do not claim that a dedicated native-stub system has already been implemented: the current pure core primarily receives explicit inputs and deterministic fixture states.
