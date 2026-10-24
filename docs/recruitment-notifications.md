# Self-selected shared houses and email notifications

The October 24 request replaces assigned recruitment with a common secret room
link. New rooms have three selectable starting territories on the existing map.
Players enter a nonempty, unique house name (at most 80 characters). Claimed or
suspended seats cannot be selected. A room starts atomically on its third claim,
with one full first interval; old rooms retain their explicit operator start.
The operator can still suspend invitations, rotate the recruitment link, pause
the calendar or cancel. A common room link never restores an occupied house.
Only that house's separate private link or linked account does so.

Specify and test: read-only landing; CSRF; each territory/name; invalid, duplicate,
or occupied choices; two simultaneous claims; repeated form delivery; one house
per known player; remaining spots; full-room start exactly once; cancellation;
revocation; old-room compatibility; guest-solo handoff; private return credential;
bilingual native forms, polling, narrow screens and enlarged text.

Email is optional and independent of registration. Per-participant subscriptions
require address confirmation and expose start, capture-result, annual-harvest and
raid-digest preferences. Raids default off; enabled raid letters are grouped with
at most one digest per 24 hours. The notification queue uses the same database
transaction as immutable recipient reports. It never reads rival snapshots.
No game transaction opens a mail connection. A Django management command sends
through standard SMTP or a local sendmail backend; no external notification
processor, broker or paid API is required. Mail is disabled until configured.

Specify and test: opt-in/confirmation; guest access; invalid and changed email;
expired confirmation; cancellation and unsubscribe; recipient isolation; each
event preference; quiet events; digest grouping and rate boundary; transaction
rollback; replay; worker locking; transient delivery failure and retry; disabled
transport; localized messages; revoked private return links. SMTP delivery is
at-least-once: a crash after server acceptance and before commit can duplicate a
message. Never log recipient addresses, mail bodies or credential URLs.

## Local verification

The Full checkpoint passed on disposable PostgreSQL 17.11: 1,615 cases, including
63 new independently collected admission/notification variations with no removed
case IDs. The 678 database-free logic cases retain 100% native-core statement and
branch coverage. Both bilingual browser journeys pass, including live spot loss
while entering a name, automatic start, private returns, guest-solo restoration,
notification preferences, 320px/390px layouts, enlarged text and native forms.
Screenshots of recruitment and email preferences were inspected. Lint, formatting,
catalog compilation, migration dry-run and Django system checks pass.

Two inherited catalogue assertions still prohibited the artwork restored by the
approved October 24 design. Their expectation now requires the eight illustrated
work families, matching the current template and independent named-quote tests.
No artwork or game-rule behavior was changed to satisfy those assertions.

Local evidence does not establish live email delivery, GitHub CI or Railway
deployment. Email transport remains disabled until an operator configures it.
