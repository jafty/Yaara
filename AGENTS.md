# Working on Yaara

## Baseline and delivery

- The development baseline is `origin/codex/yaara-deployment`, not `main`. Inspect branch, HEAD and working-tree status; fetch the deployment branch and read its guidance before editing. A local branch name is immaterial if its ancestry is correct.
- If fetching fails, report the requested ref, error and actual revision. Use an authorized read alternative or continue bounded work from the identified revision. Never claim synchronization or production verification. Retry before integration or push.
- Preserve all existing changes. Do not reset, clean, stash, overwrite, stage unrelated files or force-push. If changes overlap or their ownership is unclear, resolve scope with the owner. Work in the existing checkout; create a worktree only when requested.
- Tiny, isolated, reversible work may use a local checkout of the deployment branch when there is no concurrent writer. Use a short-lived branch for multi-step work, experiments, uncertainty or concurrent conversations. Use a PR for migrations, authorization/privacy, scheduling, broad shared-flow changes, or a deliberate review point. No PR is needed for every small fix.
- Commit, push and deployment are distinct actions. Follow the owner's delivery scope; a request for advice or a draft does not authorize release. Before an authorized deployment-branch push, pass the applicable checks in `docs/testing.md`, fetch again, inspect incoming changes, integrate without overwriting work and recheck the combined result. Push normally; on rejection, fetch and reassess. Never force-push the deployment branch.
- Railway previews and per-branch deployments are optional, never prerequisites. By default only `codex/yaara-deployment` is connected to Railway; use local automated and browser verification for other branches, then let the owner playtest the released version. Do not create preview services or databases unless requested.
- A push may automatically deploy Railway. If waiting for successful CI is not verified, treat that push as a production release and require the full local checkpoint first. If CI gating is verified, focused local checks may precede the push; production must wait for full CI on the resulting SHA. Report push, CI and actual web/scheduler deployment evidence separately.

## Product and architecture

- Read `docs/gameplay-review-prompt.fr.md` for implemented gameplay, `docs/decisions.md` for compatibility choices and `docs/design-source.fr.md` for historical intent. Verify the applicable saved-rule version in code; never silently rebalance existing games.
- Update the gameplay reference with behavior changes, including derived examples and revision provenance. For an internal refactor, verify it remains accurate and report that finding.
- Keep the native simulation independent of Django, persistence, HTTP and clocks. Services own authorization, transactions, idempotency and persistence.
- Never expose hidden opponent state or numerical combativity. Reports remain immutable recipient-specific projections. Preserve saved economies, roads and calendars.
- Conversation, identifiers, tests and comments are English. Player copy supports French and English through the checked-in catalogs. Preserve user names and archived reports. For copy changes update both catalogs and run `uv run python scripts/compile_translations.py`.
- Current UI is the compact illustrated map workspace, shared header and focused city/action folios; consult `docs/map-workspace.md` for current contracts, with later explicit revisions superseding earlier ones. Keep decorative geography separate from saved roads/rules. Preserve exact costs, consequences, native forms, keyboard access, browser zoom and reduced motion.
- Edit owning templates/components and styles; remove obsolete markup/selectors together. Avoid duplicate CSS and appended override patches.

## Skills, agents and context

- Use a skill when explicitly invoked or when its workflow materially helps the task. Read it first; do not invoke skills merely because a keyword matches. Task-specific skills do not become permanent project policy.
- Keep one primary coordinator. The owner authorizes proactive delegation: choose useful parallel work without asking the owner to organize it or repeat that permission, subject to available tools and higher-priority instructions. Delegate independent bounded investigations, non-overlapping implementation or independent review when the expected benefit exceeds briefing, integration and review costs. Use a smaller model for straightforward tasks when supported and appropriate; do not assume model selection is available. Avoid delegation for tiny edits or tightly coupled work.
- The primary agent owns scope, contract decisions, integration, conflict resolution, final diff review, test selection, evidence and delivery. Delegated success is evidence to inspect, not a release decision.
- Accept mixed post-playtest feedback in one conversation; organize it into acceptance criteria and work packages. One conversation and branch may coordinate the batch, with coherent commits for distinct changes. Split branches when work should ship independently or an uncertain feature would delay ready fixes; use another conversation when an independent objective benefits from its own context. Hand off goal, branch/SHA, dirty files, decisions, checks, failures and next step. Parallel agents/conversations need explicit file ownership and one integration owner; do not assign overlapping edits concurrently.
- Keep durable invariants here, testing policy in `docs/testing.md`, product contracts in their owning documents, and temporary progress/evidence in a PR, issue or task handoff. Replace superseded instructions rather than appending dated exceptions.

## Verification

- Follow `docs/testing.md`: specify behavior before implementation, test actual logic systematically, and select presentation checks by impact. Select checks per work package during iteration; a combined release satisfies the highest applicable level. Escalate unclear impact.
- Existing case metadata, catalog checks, logic scenarios and 100% native-core statement/branch coverage remain enforced. Do not weaken assertions, add metric-only tests or hide failures to pass a gate.
- Finish with behavior changed, actual revision, checks run/not run and why, failures and delivery status.
