# Guest solo access

Guest access adds an immediate recruitment entrance to the existing game. It does not change costs, resources, combat, the calendar or older snapshots. A guest starts a private manual 120-Moon reign against two active computer rivals using the current saved-rule defaults. The guest can finish it without registration.

## Entry and persistence

`GET /` renders a public explanation and the native `POST /play/` form. Reading or prefetching the page creates no game. A session-bound start key and transactional shared creation counters make duplicate submissions return one existing identity/reign. New guest starts go directly to Council; the prologue and guide remain available.

The temporary player is an ordinary Django user with an unusable password and an explicit `GuestIdentity`. Its existing Participant authorises all gameplay and recipient-specific reports. Temporary usernames are internal identifiers, not player-chosen house names. `is_guest` uses the explicit record and never guesses from an unusable password or name prefix. Passwordless multiplayer `SeatIdentity` principals are separate.

Guest gameplay is limited to the one linked private manual solo. Server checks prevent using the custom-game form/service to create extra or scheduled games. No artificial turn or victory cutoff is added.

The access cookie and server guest expiry use a thirty-day inactivity default. Activity renews the guest record and cookie at most hourly. Clearing cookies, using another browser or switching hostnames can lose guest access even before inactivity expiry. No game UUID or posted user ID recovers a guest identity.

## Preserving the same reign

`/save/` accepts username/password/confirmation and upgrades the same User in place. Password checks use the proposed username. The User/Game/Participant IDs, saved rules, active orders and reports remain intact. `/save/existing/` first authenticates an existing ordinary account, then atomically transfers only the guest-owned private Game and its existing Participant. The source temporary User is disabled, not cascaded away, and the target signs in. The existing thirty-owned-game cap is preserved; rejection leaves the guest usable.

The guest record is marked claimed, so expiry cleanup cannot destroy an upgraded or attached reign. Claim/attachment lock the guest identity, involved User rows in stable order, then the Game. Duplicate completed requests are idempotent. Game commands retain their existing Game locks and recheck ownership/membership after waiting. Lifecycle code never acquires GuestIdentity locks from inside a Game-locked command.

Shared invite access does not upgrade a guest into a registered account or transfer its solo to an invitation holder. Before a shared-seat login, the multiplayer view captures the current server-proven guest origin; after Django changes identity it preserves that origin in the same browser's server-side session. A native `POST /play/resume/` button restores only that exact, still-valid private solo. A posted origin ID is ignored; the entitlement is neither part of the share link nor written onto the multiplayer user. Existing-account attachment rejects SeatIdentity targets.

## Feature switches and cleanup

| Setting | Default | Effect |
| --- | --- | --- |
| `GUEST_PLAY_ENABLED` | `1` | Permit new guest starts; existing guests can still resume when disabled |
| `GUEST_RETENTION_DAYS` | `30` | Guest session and inactivity expiry period |
| `GUEST_STARTS_PER_HOUR` | `60` | New identities per observed network address/hour |
| `GUEST_GLOBAL_STARTS_PER_HOUR` | `500` | Shared new-identity budget per hour |
| `SIGNUP_ENABLED` | Existing setting | Still controls new durable account claims; existing-account authentication remains available |

Creation budgets use the database rather than per-process memory; keys are salted digests, not stored raw network addresses. The address comes from `REMOTE_ADDR`, not an arbitrary forwarded header. Hosting proxies may group many visitors under one observed address, so operators should tune the budget using actual deployment observations. Repeated resume consumes no budget. A limit response returns HTTP429 with `Retry-After`.

Schedule `python manage.py cleanup_guests` daily and retain the normal Django `clearsessions` maintenance. Cleanup locks and rechecks expiry/claim status; it deletes only an expired unclaimed private manual solo with one human membership, no other games/memberships and no multiplayer SeatIdentity. An anomalous/shared/promoted identity is skipped, never guessed safe from a username. Old creation-budget rows are also removed. Do not delete users manually to clean guest data: Game.owner has cascading deletion.

Choose the public canonical hostname before broad guest recruitment. A redirect alone does not migrate cookies from an old domain. Existing registered players can authenticate normally; guest cross-domain migration would require a separate explicit mechanism.

## Verification and observations

The changes select the Full local checkpoint because they introduce schema, authentication, transactions and cleanup. `tests/test_guest_access.py` specifies ordinary, rejection, privacy and real PostgreSQL concurrency variations. The bilingual recruitment browser journey additionally starts a guest, issues an order, advances a consequence and saves or attaches the same reign; it also checks invitation handoff and native no-JavaScript restoration.

Committed lifecycle events `guest_started`, `guest_claimed` and `guest_attached` are logged with guest-record/Game identifiers only. First seals and closures are already represented by command receipts/tick records. These are operational facts, not proof that a person understood or read a result; a visitor observation or separately specified presentation metric is needed for that stronger claim. Never log passwords, session/start secrets, invitation tokens or hidden opponent values.
