# Shared reign contract

Approved implementation scope: invitation-based three-human reigns on the existing
nine-city map and current saved rules. New rooms expose a common secret recruitment
link. Guests select an available three-city territory and a unique house name;
the visible count decreases from three remaining spots to zero. No signup or
separate readiness gate is required. A common link cannot restore an occupied
house: the player's separate secret seat link provides returning access.

Each seat owns a separate low-privilege persisted user. Its signed invitation is
a secret access credential, supports returning access, and can be rotated or
revoked. GET never claims a seat; the landing submits a CSRF-protected POST, with
a native join button when JavaScript is unavailable. A registered account may be
linked to the seat for ordinary login, but a secret seat link never authenticates
that registered account. An existing guest solo remains owned by its original
identity; a server-side session entitlement allows explicitly restoring that
guest after visiting a shared seat. No posted identity identifier grants access.

Only an explicit multiplayer operator creates rooms, manages invitations and
pauses/resumes/cancels the common calendar. Ownership alone is not this
permission. A nonplaying operator receives no invented participant or live player
projection. The dedicated operator page uses the same transactional services;
the Django admin application is not required.

New rooms start automatically, inside the third admission transaction, once all
three seats are claimed and their invitations are active. Existing rooms retain
their explicit operator start; no saved clock is converted. There is no extra
ready acknowledgement. Waiting players automatically enter Council after start,
with native refresh available. Waiting/cancelled rooms reject gameplay and never
tick. New shared starts grant a complete advertised first interval. Pauses
preserve remaining time and apply to all houses; missing orders create no new
orders or replacement bot. The advertised session windows acknowledge that
120 Moons at ten minutes span twenty hours of advancing calendar time.

Participant commands, views, home cards and letters derive the actor from actual
membership, including an authenticated account's linked seat. Private rival
seals/cancellations never change another player's poll/preview revision. Global
Game.revision remains private. Own changes invalidate own quotes; shared public
clock changes and tick closure update all participant-visible versions. Receipt
replay stays idempotent. Existing solo saves retain their clocks, rules and archive
policy.

Players retain their own completed book and exports. Shared all-house analysis
requires the operator permission and completion. It contains recipient-safe
chronicles rather than private seeds, combativity or raw tick audit.

Each logical variation is independently collected in tests/test_multiplayer.py;
the full repository checkpoint is required because this work changes schema,
authorization, privacy, scheduling and concurrency.

`tests/test_recruitment.py` adds independent common-link, house-name, remaining
spot, concurrent admission and automatic-start cases. Session-bound claim keys
make duplicate submissions idempotent; rotating a seat link also invalidates
the old claim's ability to reopen it. Names may be edited by their player only
before start. Operator rotation of the recruitment link does not rotate private
return credentials. Optional guest-compatible email is described in
[the recruitment and notification contract](recruitment-notifications.md).
