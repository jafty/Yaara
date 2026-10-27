# Implementation decisions

## 2026-10-27 · Proportional map and focused actions

The owner rejected the compressed map. Preserve 680:500 geometry and overlay
action folios on mobile, with a text Retour control; expansion never resizes the
map. Use torch/flag-over-fort mission icons and Conquérir. Works retain square
list art and 3:2 detail art, compact preparation controls and icon/value metadata.
Remove arrows from navigation, route heads and comparisons. Existing command
identifiers, prices, quotes, seals, rules and report records remain unchanged.
See the final section of `docs/map-workspace.md`. This is presentation verification.

## 2026-10-27 · Denser header and mobile army planning

The owner requested more useful decision space and then removed repeated header
labels and secondary prose. Keep icon/exact-value resources with accessible names,
an inline harvest link and envelope/Alertes count. Put the owner beside the compact
city title. Mobile decisions take most of the screen; explicit expansion and a
large-text fallback provide a full-screen sheet. Army review totals sit outside
the scrolling form; local funding and warnings stay visible, while equipment and
explanations use native disclosures. Uniform native fields preserve all existing
review/seal flows. See `docs/map-workspace.md`. This is presentation work; no native
core or saved-rule change requires a gameplay-reference update.
The owner's component review replaces cards/gauges with one local-means ledger
row, removes duplicated capabilities and troop sliders, and presents mission
choices, dates, crew status and totals as restrained manuscript controls. Details
belong in their accounts, work items or native disclosures.

## 2026-10-27 · Schematic map and continuous contextual sheets

The owner authorized map/city artwork and removed the need for the three-item
bottom menu. The shared header now carries map, named house/Reign and Courrier.
Keep fixed city tabs, retained sheet shells and decoded map art between contextual
views; only transform/opacity animate, respecting reduced motion. Plain schematic
fortifications have no arrow slits; muted green palms and faint dunes are decorative.
Public wall levels select current or legacy artwork. Existing house emblems appear
on green owned/red enemy flags. Organic presentation positions and curved boundaries retain every saved road
connection and leave game rules unchanged. See `docs/map-workspace.md` for contracts and verification.
Native core rules and the gameplay reference remain accurate without changes.

## 2026-10-26 · Paris deadlines and final-Moon verification

The owner reported a five-minute multiplayer reign waiting at Moon 119 and a
UTC clock while France uses winter time. Display all player and operator closure
times in `Europe/Paris`, labelled in both interface languages. The IANA zone
handles winter/summer transitions; stored UTC instants, countdowns and scheduler
authorization keep their existing meaning. Reuse one native `time` template so
the clock also works without JavaScript.

Independent PostgreSQL cases exercise Moons 119 and 120 for both saved calendar
versions, on-time and two-minute-late cron processing, with tied, population and
territorial standings. A tie still ends the reign at closure 120, exactly once.
These cases verify existing rules; no end-condition or scheduler change is
justified by the supplied screenshot. At 09:24 Paris in winter, an 08:22 UTC
deadline is two minutes overdue, within a five-minute cron's polling interval.
The running game's scheduler state requires live operational evidence.

## 2026-10-24 · Self-selected houses, automatic recruitment and optional email

The owner's follow-up replaces assigned seats for new rooms with a common
recruitment link, available starting territories, player-chosen house names and
live occupied/remaining counts. The existing map has three human houses; a room
starts atomically at 3/3 with a complete first interval. Do not invent variable
world sizes or convert existing operator-start rooms. Keep their saved behavior,
private return invitations, operator controls and guest-solo restoration.

Admission locks the game and rechecks availability, cancellation and invitation
rotation. Session-bound claim keys prevent duplicate identities. A common link
does not authenticate existing seats; names are unique and editable only before
start. Both languages retain native forms and refresh links.

Optional per-participant email needs no account, broker or notification vendor.
Use Django SMTP or local sendmail, explicit address confirmation, separate event
preferences and unsubscribe. Raid mail defaults off and groups into a digest at
most once per 24 real hours. Only recipient letter titles enter messages. Queue
rows commit atomically with reports; workers claim a short delivery lease and
send outside game/database locks, with retry after transport failure or an
expired lease. An SMTP acceptance followed by a process crash can duplicate an
email; do not claim exactly-once external delivery. Unsubscription cancels queued
mail; it cannot recall a message already handed to transport. Confirmation lasts
48 hours, can be requested again after an hour, and address changes while
unconfirmed have a five-minute cooldown. Mail remains disabled until configured.

This is Full verification work. The independent variations and operations are
recorded in `docs/recruitment-notifications.md`; existing rules, numerical balance,
saved-state versions and immutable reports remain unchanged. The current gameplay
reference is updated for the new admission/calendar consequences.

## 2026-10-24 · White manuscript and landscape scenes

The owner's maquettes and subsequent screenshot reviews supersede the earlier
uniform papyrus page, tiny heading illustrations and repeated parchment panels.
Use clean reading surfaces, full-column scenes below story and work-family
titles, and compact city summaries. The latest catalogue review restores
illustrations above titles in two unboxed columns, with one-column fallback
for narrow screens and enlarged text. Keep every named upgrade's price and
duration visible with grain and moon pictograms; move explanatory purpose to
the existing family page. Council and
expedition headings have no decorative thumbnail. Keep the original scene files;
a generated alpha mask supplies subtle worn edges without blurring the drawings.
The owner rejected the generated panoramic variants as yellowish and less
schematic. Use the complete original 3:2 standalone compositions; keep the 2:1
frame for atlas excerpts and catalogue tiles. The owner accepts cropping in
the catalogue, pending a possible future artwork pass. The active menu marker meets the green band's
top edge directly.
The latest review prioritizes game density over editorial scale: smaller page
and section headings, tighter rows and gaps, while keeping 17px body text and
44px interactive targets.
Native fragment scrolling reserves space above the fixed bottom menu.

Trial a pale stone header and a deep mineral-green bottom menu with cream labels
and light terracotta selection. Mission controls reuse the existing pictograms
and light papyrus texture. Preserve realm-wide city checklists, report content,
and the separate review/seal/closure stages. The owner approved the reviewed design
and requested its push to the deployment branch on October 24. Deployment
verification is reported separately from the push.

The current SVG map can support painted scenery without a data-contract change.
This first pass refines its existing parchment, boundaries, house colors and
selection; it does not add the maquette's river or replace the saved nine-city
geography. See [the visual audit](visual-redesign.md) for the adaptation decisions
and remaining map-art work. Palette and fonts are shared across game and entry
screens. This is Presentation work, with existing bilingual browser journeys and
affected PostgreSQL contracts; core rules and projections remain unchanged.

## 2026-10-24 · Material manuscript and restrained illustrations

The owner rejected both the ornate earlier mockup and the pale blog/admin-panel
compromise. Their clarification explicitly keeps illustrations small: no prominent
Council scene. Retain the contextual frescoes and existing reading/action order.
Use a locally stored, low-contrast papyrus/plaster texture, self-hosted Alegreya
with 17px default body text, earthen headings and muted mineral-blue reading links.
Replace the striped header, left-edge callouts and desktop sidebar with simple
rules and a continuous dark umber bottom navigation in all viewport sizes. The
Council icon depicts an Egyptian pylon rather than a columned pediment. Keep
visible labels, touch targets, focus states and the three existing destinations.

Rename the optional map explanation to “Comprendre la carte” / “Understanding
the map”, including its accessible label. Native disclosures, forms, exact costs,
reports and saved rules retain their behavior. The gameplay reference remains
accurate and needs no rule update. This is Presentation work; validate both
languages, small contextual art, material decoding, default/enlarged text,
keyboard and no-JavaScript flows using the existing PostgreSQL and browser checks.

## 2026-10-24 · Recruitment entrance and invitation-based shared reigns

The owner approved implementation after the three parallel plans, with a fluid
operator → waiting room → game flow. Shared players open their own secret seat
link, join through a CSRF-protected POST and wait for the operator's start; there
is no mandatory signup or readiness acknowledgement. Each invitation authenticates
only a separate low-privilege seat identity. A registered account can be linked for
normal login, and an operator accepting their own seat retains their management
session. A secret link never authenticates its linked registered account.

Use the existing nine-city current-rule world, three human houses, no replacement
bots, and existing server ticks. The operator permission is distinct from ownership
or player membership. Provide a dedicated management page and `grant_operator`
bootstrap command; do not depend on the absent Django admin application. Start
requires all three occupied seats and active invitations. Waiting pages poll only
public seat/calendar facts and enter Council after start. Shared first Moons get a
full advertised interval; existing solo alignment and saved rules remain intact.
Common session windows and whole-game pauses acknowledge the twenty-hour active
calendar span of a standard ten-minute/120-Moon reign.

Keep Game.revision internal in shared games. Participant-visible revisions change
for their own orders and shared clock/tick events, never for hidden rival seals or
cancellations. Signed previews and state polling use this same own-view version.
Game locks cover seat/session-grant validation before command mutation. Revoked or
rotated bearer links invalidate old seat sessions; independently authenticated linked
accounts retain their membership. Player books remain personal, with technical
exports in secondary controls; shared all-house exports require operator permission
and completion, without seeds, raw audit or numerical combativity.

Guest solo starts immediately with a private manual preset. Account saving preserves
the existing reign. Entering a shared seat retains only a server-side entitlement
to resume the original guest solo; it does not move ownership onto a seat identity
or upgrade a secret seat into a full registered account. Temporary cleanup is
restricted to explicit unclaimed private solo identities.

The approved visual compromise keeps quiet warm paper, small contextual frescoes,
restrained dividers, visible resource captions, precise post-seal closure links and
the existing three destinations. Correct setup facts from current rules rather than
repeating historical starting stock or capture restrictions. These schema, privacy,
authorization and calendar changes require the Full local checkpoint and the new
real-browser recruitment journey, in addition to existing CI layers.

## 2026-10-24 · Paid intelligence, integration and reciprocal frontier encounters

The owner approved this package after reviewing a complete 120-Moon archive. New economy-four games save `strategy_version=2`; missing markers and explicit version one preserve old admission, target exclusivity, visibility and military behavior. No snapshot backfill or silent conversion. Keep the current economy, raid tariffs, respite, supplies and N/N+1/N+2 travel unchanged.

Inherited local Faithful defend for the three Moons following capture but cannot join offensives or relief until N+4. Track the inherited local pool separately from returning friendly contingents and new recruits. Local deaths reduce restricted/free pools proportionally; absent deaths do not consume the restricted local pool. No tax/score penalty.

Enemy seals and enemy respite dates no longer leak through maps or validation. Admit duplicate target orders and leave invalid-objective/respite-at-arrival consequences unchanged, including no refund. Effective surveillance I learns target/date only after actual departure; II additionally learns mission kind and a coarse troop band. Persist dated recipient-specific warnings, retaining learned information after damage and not transferring intelligence to a new owner.

Automatically select a directly adjacent friendly frontier departure city reachable by every contributor: largest local contribution, then stable city ID. Revalidate at departure and freeze the selected road. Reject disconnected assembly without reservation or expenditure. No manual route selector or enemy-state-dependent route optimization.

Resolve opposite marching forces from the same departure Moon on each road in one aggregated field encounter, regardless of raid/capture combination. Equipped strength determines whether both return (<1.25), a clear victor continues (1.25–<2), or an overwhelming victor continues (>=2). Loss rates on the smaller engaged count are respectively 6%/6%, 2%/12% and 0/4%, half-up rounded and proportionally allocated. Retain original return dates; a field victor continues city combat using survivors even below the initial launch minimum. No walls, city relief, shelter or siege bonuses in the field, no seal-time initiative. Player reports expose exact own losses and qualitative enemy losses; private audit values stay outside projections.

Documented variations and expectations precede implementation in `docs/frontier-contract.md` and independent native/HTTP cases. The privacy change selects the Full local checkpoint, including real PostgreSQL, 100% native statement/branch coverage, both translation catalogs and the bilingual browser journey. Windows startup fixtures now use native PATH separators, POSIX-compatible event paths and explicit LF stubs; the success/failure assertions remain unchanged. The browser journey exposed a 320px header wrapping just beyond its existing height limit; reduce the owning status component's vertical padding while preserving 16px body text and 44px alert targets.

## 2026-10-23 · Light literary layout refinement

- The owner approved compact but visible artwork, in-game scope, and Council news followed by upcoming events before city accounts. Preserve the paper, serif manuscript, local fresco assets, three destinations, exact figures and scribe narration. Contextual headings use complete 3:2 illustrations beside the title; report artwork follows its dated title and is restrained to twelve rem. Council excerpts remain thirty-five words, with full-letter and city links after the prose.
- Council has native jumps to upcoming dates and accounts. Desktop retains adjacent news/dates and city ledgers. Works starts with ongoing commitments and the illustrated catalogue, without an additional introductory fresco. Every named upgrade is paired with its own quoted price and duration. Family selection remains a direct realm-wide checklist and one atomic preview/seal.
- Resource icons stay visible, with small translated captions and exact numbers. Their groups wrap independently at narrow widths and enlarged text. Secondary folios and signed reviews highlight their existing parent destination using the already-provided navigation context. Help and closure controls remain below the reading area.
- Expeditions retains the public map and visible house identities. Symbol explanations and illustrative-border advice move into an initially closed native disclosure; a short selection instruction stays visible. Selected-city status, saved routes, dated intelligence, costs, local contributions and warnings remain outside it. Preparation uses compact heading artwork and the existing native forms. A summary of the action, cost and execution Moon precedes the detailed unsealed decree.
- Fragment links retain conservative relative clearance for the wrapping sticky header; remove the earlier negative map-panel margin. No JavaScript dependency is added to navigation, and no report facts are extracted from prose or inferred from today's city state. Report anchors and their links explicitly avoid localized thousands separators, including when numeric identifiers exceed a thousand. No API, save, rule, privacy or persistence change is required. The current gameplay reference remains accurate without a revision.
- Use Presentation verification: independent bilingual layout/read-only cases, affected PostgreSQL presentation regressions, compiled catalogs, lint/format, reviewed complete case collection, and the shared bilingual browser journey with keyboard, native forms, 320px/390px/desktop and enlarged-text checks. Keep comparable before/after screenshots as local artifacts.

## 2026-10-23 · Precise alert destinations and completed-building artwork

- Defense alerts link to the city's recorded fortifications and immediately following manpower accounts, reserve alerts to its granary accounts, and repair-needed alerts to the repair selection below the illustration. Keep the existing active-work/sealed-order tracking anchors. Native fragments and focusable destinations work without JavaScript and clear the sticky header.
- Completed-work letters select the actual building family from their immutable structured completion phrase, including older vocabulary, current upgrades, repairs and legacy realm equipment. Council thumbnails and full letters reuse the building artwork already shown in Works. Unstructured or unidentified archives keep neutral artwork; current city levels never determine a historical image. No report rewrite, new asset, rule, translation or disclosure is required.
- Retain the existing basic committed-target warnings after reviewing the owner's balance concern. They expose the same target engagement already available on the map, without identifying an origin, force size, mission type or arrival time. Removing just the warning would reward repeated map inspection; hiding engagements also requires resolving the information exposed by exclusive-target rejection. Surveillance already affects raid mobilization/interception and does not currently provide reconnaissance.
- Retain crossed expeditions: departures remove troops from their origins before combat, so counterattacking an exposed origin is a strategic cost of attacking. The engine does not model positions along roads; sharing a combat Moon alone does not establish that two armies meet. There is no post-departure cancellation: current cancellable orders can be withdrawn only while sealed. A delayed recall with costs and an explicit interception/field-battle rule remain proposals in the backlog, requiring separate balance evidence and versioned rules rather than a silent change to running games.
- Use Presentation verification: independent bilingual HTTP destination and completion-family cases on PostgreSQL, existing presentation regressions, lint/format, reviewed full case collection and the bilingual browser journey. No core rules or disclosed facts change; the gameplay reference remains accurate without a revision.

## 2026-10-22 · Persistent alert centre and visible building damage

- The owner asked whether centralizing alerts would make damage easier to notice. Use one persistent in-game alert centre and a counted header link across folios. Its count measures current unresolved issues: incoming enemy engagements, each damaged owned building, and each city's siege-reserve shortfall. Order threats first, then damage, then reserves. Ordinary crew activity and routine letters remain in their existing registers.
- Council opens nonempty alerts; an incoming threat opens them on other folios too. Other pages keep a compact disclosure with the issue count and damage total. Header links target the list inside native details, which opens through fragment navigation with keyboard and without JavaScript. Empty centres state that no current alerts exist. Paused games retain their issues; completed reigns have no actionable alerts.
- Damage entries name the city and exact building and link to its existing repair family, preselecting the city. Existing team commitments identify a sealed or active repair and expected completion, linking to the corresponding register. Damage stays visible during repair and disappears when the saved damage flag clears. Legacy damaged walls remain supported through their existing city projection.
- City accounts and work-selection rows use a labelled damage pictogram. Damaged building details receive the same label, a restrained tinted outline and a direct repair link. Resolve damage through the ordinary read-only quote and seal workflow; alert navigation never starts work or reserves resources.
- A presentation template tag formats only the existing authorized player projection. No storage, dismissal state, simulation, resource calculation, disclosure rule or scheduler changes. This remains the Presentation checkpoint: 28 bilingual HTTP variations, affected PostgreSQL cases, compiled catalogs, lint/format, full case collection and the bilingual browser journey. A real-server browser reproduction additionally exercises simultaneous damage/threat alerts, direct repair preselection, sealed/active/completed repair states, keyboard navigation, no JavaScript and enlarged narrow layouts. The gameplay reference remains accurate without a rule change.

## 2026-10-22 · Named crew assignments in city lists and details

- The owner requested the purpose of occupied crews in both city lists and detail folios. Reuse one assignment summary beneath the availability badge in Council, work-selection lists and city details: the specific named construction or repair, sealed/awaiting-start versus active status, and expected completion Moon. The detail folio also includes the start Moon. Links open the pending-order or active-work register, as appropriate.
- Assemble this display metadata at the HTTP boundary from work and order commitments for currently owned cities; sealed orders must belong to the current actor. Use the existing localized work vocabulary and saved start/duration/finish values, rather than forecasting costs or rerunning simulation. Completed/cancelled assignments disappear under the existing status rules. Old saves retain their own vocabulary and timing.
- Replace generic crew prose in the city details and the duplicate task/date paragraph below Council city accounts. Costs, crews, reservations, scheduling, authorization and the core projection remain unchanged. Use Presentation verification: twelve bilingual named-assignment cases across irrigation, arsenals and initial-defence repairs, existing lifecycle cases, affected PostgreSQL checks, lint/format, case collection, catalog compilation and the bilingual browser journey with native forms and narrow/enlarged layouts. The current gameplay reference remains accurate without a rule change.

## 2026-10-22 · Incoming threats and visible crew availability

- The owner requested an explicit incoming-enemy warning and clearer city-team status. Keep knowledge of committed targets as basic public information, consistent with the existing map markers; no surveillance upgrade is required. Surveillance retains its existing mobilization and interception effects.
- Every in-game folio shows a compact warning naming each owned city with an existing enemy engagement, linking to its defence accounts. This includes sealed attacks before departure and active expeditions, and persists while paused. It clears with the existing target reservation after cancellation or combat and is hidden once the reign finishes. The copy says “committed”, without implying confirmed marching or revealing an attacker, force size, mission type, hidden equipment or arrival date.
- City-account names and work-selection lists share explicit “Crew available / Crew occupied” labels. Sealed work reserves a crew immediately; active work keeps it occupied, cancellation and completion free it under the existing rules. Existing task names and availability Moons remain visible in city accounts. Remove the duplicate crew figure from the account table.
- This uses the Presentation checkpoint. Only templates, styles, translations and their checks change; authorized projections, simulation, reservations and building effects remain intact. The current gameplay reference still accurately describes exposed engagements and team commitments, so no rule-reference revision is needed.

## 2026-10-22 · Compact preparation and desktop folios

- The owner authorized a presentation-only desktop redesign while retaining mobile navigation and flow. Large screens use a left navigation rail, a wider reading area, adjacent Council news/accounts, two-column work families and a sticky atlas beside expedition preparation. Narrow screens keep the bottom navigation and map above preparation. Enlarged text falls back through the same responsive rules.
- Origins retain their available men, editable contribution, local payment and warnings in view. Native per-city ledger disclosures contain labelled armament, siege and transport pictograms, carrying rates and exact reserve calculations. They work with keyboard and without JavaScript. Warnings stay outside the disclosure, including failed-form recovery.
- Preparation shows the own-army's maximum carrying capacity, updating with the contribution mix, alongside the existing reimbursement threshold. This ceiling assumes every selected man survives; actual enemy loot remains unknown. No enemy stocks, crops, equipment or numerical combativity are consulted or newly disclosed. Capture hides the loot-specific information. Prices, contributions, reservations, combat and saved rules remain unchanged.
- Selected cities show only their saved direct road connections and linked neighboring city names. This supersedes the earlier blanket prohibition on drawn road edges, without adding a full road mesh or changing topology. Namar has no direct road to Daram in the current frontier map despite illustrative territorial proximity. City labels are smaller and map legends use upright, consistently aligned cells. Work-price groups wrap as units.
- The work catalogue starts with ongoing works, their cities and completion Moons, reusing the same register on family pages. English actions use “Plunder” and narrative nouns use “foray”; French display text consistently uses “pillage”. Internal identifiers and stored original reports stay intact.
- Use the Presentation checkpoint: nine independent HTTP variations across both languages and all three saved maps, affected PostgreSQL presentation cases, catalogue compilation, lint/format, full case collection and the bilingual browser journey. The gameplay reference remains accurate: no core rules or player consequences changed.

## 2026-10-22 · End-of-reign book and analysis export

- The owner requested a complete player or all-player log for literary role-play and AI analysis. Finished reigns now link to a chronological book of every preserved recipient letter, with a player/all-houses scope and a versioned JSON download. This explicitly permits the game owner to read the other houses' preserved letters and own-account projections after completion; ordinary participants can read only their house. Active, paused and merely eliminated reigns do not unlock the book. Existing live projections remain unchanged; no raw snapshot, seed, combat draw or numerical combativity is exported.
- Each newly resolved Moon stores per-house allowlisted accounts in `TickExecution.trace.chronicle`, in the same locked transaction as the tick and reports. Retries reuse the committed record. Accounts describe the end of the closure, not initial or intermediate state. They include owned-city balances, population, casualties, works and the existing own-order/mission register. Letters from several recipients may describe one event; the export warns against counting them as distinct events.
- Older ticks are never replayed or backfilled. The book retains all existing letters and the fixed final accounts, and lists missing account Moons explicitly. New closures of an older active reign begin recording accounts without changing its saved rules. Schema version, saved rule-version markers, language, final Moon, report ordering and missing-account coverage accompany the JSON. Original unstructured French archives remain labelled; immutable reports are never rewritten.
- Use the Full local checkpoint because persistence and post-reign disclosure change. Independent cases cover both calendars and languages, owner/member/outsider access, completion and pause, invalid options and methods, complete letters beyond preview limits, old gaps, transaction rollback and retry safety. The browser journey completes a 24-Moon reign and reads/downloads both scopes, with narrow/enlarged layouts and native disclosures without JavaScript. No rules, balance or outcomes change.

## 2026-10-22 · Explicit combat outcomes and historical attacker identity

- The owner reported that received capture letters omitted the attacking house and received raids did not plainly identify success or failure. Add a bilingual outcome sentence at presentation time from the saved, allowlisted combat scene: success always means the attacker prevailed, failure means the defense held. Military success remains independent of loot and the existing provisional/final cash balance.
- Received capture letters recover the public attacking house from a unique saved capture expedition matching the report Moon and named city. Use the historical mission actor, never today's city owner or troop/stock values. Missing or ambiguous matches add no identity. Apply this to existing and future letters in Council and the full archive without writing to reports or replaying combat. Older letters without a saved scene retain their original outcome wording; no outcome is guessed from loot.
- This disclosure change uses the Full local checkpoint. Regression cases cover both languages, both recipient perspectives, raid/capture success/failure, immutable archive/state, absent/ambiguous/wrong-Moon/own-mission matches, and PostgreSQL-backed Council/archive delivery.

## 2026-10-22 · Contextual beginnings in decree news

- Replace the scribe in action-start letters with a matching beginning: marching troops for both raids and captures, first granary foundations, forge preparation, wall work, canal digging, watch-platform assembly, protected-storage excavation, cart assembly and siege-workshop preparation. Repairs share wall-work artwork; legacy equipment shares forge preparation. Keep the existing papyrus fresco style and decorative 3:2 images in Council thumbnails and full letters.
- Select scenes at the authorized presentation boundary from the existing structured action-start heading or the action embedded in older generic-heading letters. No text parsing, current-state lookup, archive rewrite or new saved metadata is needed. Sealed, cancelled, invalidated, unstructured and unrecognized decrees retain neutral artwork. Combat outcomes retain their separate recipient-specific scenes.
- Use Presentation verification: reviewed independent bilingual HTTP cases for every action on Council and full letters, older headings and neutral fallbacks; PostgreSQL 17, lint/format, full case-catalog collection and the bilingual browser journey with decoded images, narrow/enlarged layouts and no-JavaScript navigation. Game rules and disclosed facts are unchanged, so the gameplay reference needs no revision.

## 2026-10-22 · Action headings and full report images

- New departure reports use the existing bilingual action-start narration as their heading instead of the generic decree heading. Existing stored reports retain their original wording; no archive is rewritten. No new catalog entries are required because both languages already translate these phrases.
- Council previews retain their compact thumbnails. Full reports place the complete 3:2 illustration above the date, heading and letter, spanning the reading column. Shared report markup and existing artwork remain in use.
- This uses the Behavior local checkpoint because native report narration changes: complete database-free core coverage, affected PostgreSQL HTTP cases, lint/format, reviewed case catalog and the bilingual browser smoke with narrow/enlarged layouts and native navigation. The gameplay reference needs no change: rules, balance, dates and disclosed facts are unchanged.

## 2026-10-22 · Quiet parchment map and house emblems

- The owner's follow-up supersedes the painted terrain direction below: remove mountains, dunes, rocks and scrub while preserving the pale worn parchment, fibres and rubbed edges. Only tiny faded palm sketches remain in two corners; no prominent relief competes with the cities.
- Keep the local `map-terrain.png` background and public territory geometry. Replace Roman house numbers with restrained vector seals: sun for p1, lotus for p2 and palm for p3, shared by city markers and the house legend. Current ownership determines the seal; accessible city/house names and all reach/engagement markers remain intact.
- This is Presentation work: lint/format, complete case-catalog collection, affected bilingual map and illustration cases on real PostgreSQL 17, and the bilingual browser smoke with narrow/enlarged layouts and no-JavaScript navigation. Review current and legacy maps and background decoding visually. No gameplay reference update is needed because game behavior is unchanged.

## 2026-10-22 · Match the map to the existing frescoes

- Replace the yellow, finely shaded terrain background with a redraw using the actual Council and cityscape images as style references. Match Council's pale ivory fibrous papyrus, rubbed mineral pigment and softly abraded edges; simplify mountains, dunes, rocks and scrub into flat shapes with stronger brown contours. Avoid the previous golden wash, realistic crag shading and heavy cracked/burnt parchment treatment.
- Keep the existing background filename, sparse placement and complete-sheet proportions. Only the decorative raster asset changes; map controls, city labels, legend, geometry, gameplay and archived data remain unchanged. Use the same Presentation checkpoint and visual review of the current and legacy map layouts.

## 2026-10-21 · Painted terrain on worn parchment

- The owner's follow-up replaces the first vector-decoration pass with one generated raster terrain background. Use visibly worn pale papyrus, fibres, cracks, rubbed mineral pigment and weathered edges, with sparse desert mountains, dunes, rocks and scrub around open areas. Keep the original map layout, borders, city markers, Roman house marks, typography and legend.
- Serve `illustrations/map-terrain.png` locally as the map frame's background, scaled to the complete sheet without cropping. Existing SVG territories, accessible city links and marker states stay above the painting. Terrain remains decorative and independent of ownership, installed works, saved road versions and private resources; no rules, projections, archived reports or player-visible copy change. The gameplay reference remains accurate without revision.
- Use Presentation verification: lint/format, complete case-catalog collection, affected bilingual map/illustration HTTP checks on PostgreSQL 17, and the bilingual browser journey, including narrow/enlarged layouts, keyboard selection and no-JavaScript navigation. Visually inspect current and legacy maps and verify background image decoding.

## 2026-10-21 · Benin-inspired warriors and active battle scenes

- The owner's warrior sketch supersedes the earlier tunic and sparse-soldier direction. Soldiers wear separate shoulder pads over bare chests and abdomens, small layered collars, diagonal straps, decorated belts, wrapped kilts, sandals and rounded caps. Vary headwear, shoulder details, cloth trim and weapons, including spears and swords, within the shared Benin City-inspired silhouette.
- Populate army preparation with a larger assembled force. All eight battle-report images show opposing soldiers actively fighting, with supporting ranks and several distinct clashes, in one continuous landscape. Preserve the flat mineral palette, bold outlines, worn pale parchment and 3:2 compositions.
- Preserve each report's existing perspective and military outcome: blue-accented forces represent the recipient/player, red-accented forces the enemy; a successful received attack shows the enemy prevailing. Raids remain village encounters; captures center on city gates. These decorative scenes do not assert exact troop counts, resource amounts or equipment levels.
- Apply the same costume to Council and fortification guards and the atlas's returning soldiers. Include women as Council advisors, granary workers and the atlas's scribe; other civilian scenes can retain their existing characters. Preserve the atlas's nine scene positions and the cityscape atlas. Normalize generated atlas rows to the existing CSS thirds so adjacent scenes do not overlap their crops.
- Replace local image assets under their existing filenames. Report selection, archived content, game rules, templates and translations are unchanged. The current gameplay reference remains accurate and needs no revision.
- Use Presentation verification: lint/format, complete case-catalog collection, affected bilingual HTTP cases on real PostgreSQL, visual review of every revised scene and atlas cell, and the bilingual browser journey with image decoding, narrow/enlarged layouts and no-JavaScript navigation. No new logical variation is introduced by replacing decorative assets.

## 2026-10-22 · Consistent frescoes and list thumbnails

- Use the supplied Council image as the visual reference: flat mineral colours, bold brown outlines, pale worn papyrus, simple architecture and sparse small figures. Retain Council, granary, forge and fortification originals that already match it; redraw the two nine-panel atlases, army preparation and all eight battle illustrations. Review figures for aligned heads, torsos and feet, separated limbs and supported objects; correct the floating raid basket and misleading held-city banner found during review.
- City identities show only basic houses, a modest council porch, ordinary streets/market awnings and natural surroundings. Remove canals, managed fields, granaries, watchtowers and fortifications from cityscapes. Acquired buildings remain illustrated in their own work families, not asserted by a city's decorative identity. Stable city-ID mappings remain unchanged.
- City accounts and both Council news and full archived letters use decorative 3:2 thumbnails. Keep larger illustrations in city folios and work family pages. Native city/report links, report text, recipient/outcome mappings and archived data remain unchanged. Thumbnail headings reflow at narrow widths and enlarged text without JavaScript.
- Verification began at Presentation level and escalated to the full local checkpoint after CI caught missing report-type icons; retain those established icons alongside thumbnails. Check all PostgreSQL cases, core coverage, catalogue collection, lint/format, migrations and the bilingual browser journey with image decoding, narrow/enlarged layouts and no-JavaScript navigation. No core behavior changed; the gameplay reference remains accurate without revision.

## 2026-10-21 · Combat news frescoes

- Owner's follow-up: each of the eight report illustrations is one continuous landscape and one moment, without a diptych, stacked registers or inset scenes. Reuse the original `army-preparation.jpg` soldier design: rounded knobbed caps, broad collars, diagonal straps, white wrapped kilts, sandals, oval banded shields and red/blue accents. Keep the fresco palette and all existing outcome/perspective mappings. This asset-only revision uses Presentation verification; gameplay reference facts remain unchanged.
- Owner's visual revision: redraw all eight report images as schematic ancient war frescoes, with small profile figures in horizontal military registers, flat mineral pigments and worn pale plaster. Outcomes read through formations, withdrawal, gates and standards; remove oversized keys, handover ceremonies and exaggerated sorrowful figures. Keep the existing scene identifiers, 3:2 assets and report selection unchanged.
- Add eight generated 3:2 papyrus frescoes inspired by the supplied army and fortification images: offensive raids, offensive captures, received raids and received captures, each with success and failure. Incoming success means the enemy attack succeeded; incoming failure means the recipient held. The images are decorative, with no resource quantities or equipment-level claims.
- New resolved battle letters save one allowlisted scene identifier alongside their existing localized title/body. Raid victory follows the military outcome even with zero loot; capture success includes unopposed entry, surrender, assault and capitulation through shortage. Held sieges, defeats and routs use failure artwork. Attacker and defender receive different views. Public sovereignty notices and abandoned combats keep generic artwork.
- Preserve all archived report content. Older letters without a saved scene retain the prior generic illustration rather than guessing a raid result from loot or consulting today's mutable ownership. Army preparation remains unchanged. No combat rules, balance, database schema or private numerical information change.
- Verify at Behavior level: independent prescribed-outcome cases, the complete logic coverage gate, PostgreSQL report rendering/persistence checks in both languages, full catalog collection, lint/format and the bilingual browser smoke with local image decoding.

## 2026-10-21 · Distinct city folio landscapes

- Give all nine cities a different decorative cityscape in one coherent fresco set: Qasr's square, Tamesh's hillside, Namar's canal, Sefra's market, Ishar's well, Daram's winding lane, Azal's spring, Mirha's fields and Tazir's gateway. Keep the supplied architectural vocabulary, solid walls without arrow slits or battlements, compact headwear and sparse blue tunics.
- Map the nine atlas panels to stable public city IDs, independently of house, ownership, language, saved rule version or building levels. Every house's cities differ, including after capture. These images express visual identity, not installed upgrades or private city resources. Reuse the decorative illustration component and full 3:2 responsive proportions. No simulation, save or report changes.
- Verify at Presentation level with independent bilingual city-folio cases, unchanged identity after ownership change, complete catalog collection, lint/format, PostgreSQL HTTP checks and the bilingual browser journey through all nine images, mobile/enlarged layouts and native navigation.

## 2026-10-21 · Owner-supplied fresco illustrations

- Use the owner's five landscape images for Council, granaries, forges (including legacy realm equipment), fortifications/repair, and army preparation. Raid and capture share the same preparation image; their report illustrations also share it. Expeditions opens directly on the map without a separate heading illustration.
- Replace the remaining decorative atlas with matching generated papyrus frescoes for construction, harvest, irrigation, watch, shelter, transport, siege equipment, returns and letters. All assets remain local and decorative. Preserve the full 3:2 compositions in catalogue thumbnails and restrained full-size family images; a family page has one illustration. No rule, saved game or archived report content changes.
- The owner's follow-up refines the generated atlas: solid buildings without arrow slits or battlements, mostly bare heads and small high-set rounded caps instead of long Egyptian headcloths, and restrained Tuareg-inspired blue tunics on two figures. The return scene reuses the supplied fortification's smooth walls, projecting buttresses, wooden gate, red/blue bands and thatched tower. The five supplied image files remain the owner's originals.
- Use the Presentation verification level: lint/format, complete case-catalog collection, affected HTTP cases on PostgreSQL and the bilingual browser journey, including image decoding, responsive proportions, both attack choices and native no-JavaScript preparation.

## 2026-10-20 · Playable openings, seasonal raids and illustrated family pages

- The owner approved the full playability scope, then explicitly raised fortifications to favor siege. New games use `economy_version=3`; absent/older economy markers preserve all existing quotes, levels, crop yields, equipment, stocks, raids, cooldowns and archived letters. The public creation form always uses current complete rules and omits V0/V1; internal rule-family compatibility remains.
- Adopt the eight-family catalogue in `gameplay-review-prompt.fr.md`: three agriculture/storage/arsenal/wall stages and two surveillance/shelter/transport/siege stages. Arsenal prices are fixed per city. Each local team and granary fund their own work; batch admission remains atomic. Repair prices are 20% of the corresponding wall passage (40k/180k/480k), lasting 3/6/8 Moons. An assault capture can damage walls; they retain half their bonus until repaired. No new raid building damage or construction pause.
- Fortification coefficients are 1/2/4/7. Damage and siege gear multiply only the bonus above one; neither can reduce base defense. Local garrisons alone receive fortification protection. Intact level-three walls with 50% siege reduction give ×4; damaged walls with the same reduction give ×2.5. Equipment, transport and siege levels are frozen by origin at departure; siege reduction is weighted by attacking strength and transport is based on allocated surviving cohorts.
- Historical rationale: the [Egypt Exploration Society’s Buhen account](https://www.ees.ac.uk/resource/buhen--an-egyptian-fortress-in-nubia.html) documents a major Middle Kingdom fortress. It does not establish a universal seven-to-one tactical ratio. The 2/4/7 values are explicit game parameters, not a historical measurement. The existing starvation rule remains: an army exceeding field defense can force capitulation if the granary lacks 500 Measures per present resident, regardless of the walls.
- Surveillance replaces the 20/30/40% random village mobilization with a guaranteed 40% then 60%, without creating defenders. Successful seasonal raids expose a quarter of accrued tax after a 200k/400k/800k shelter threshold, carry up to 60% of that portion and destroy 20%. Existing failed-raid loss rates use the same exposed base. Debit accrued tax, not stock. No production suspension or fixed additional damage. A materially successful raid protects against raid arrival during the next two Moons, permitting the next combat at N+3; admission/departure checks consider the planned arrival. Captures remain possible.
- In current games, annual payment and renewal follow combat and precede returns. This prevents Moon-twelve tax reset from erasing the raid target and prevents duplicate payment. Monthly accrual still precedes departures and work completion; the annual payout uses remaining crop, current capacity and ownership. Siege subsistence uses already stored supplies. Older economies retain their original order. Calendar deadlines and tick idempotency are unchanged.
- Bots continue to submit normal commands using only owned resources, calendar and public geography. Current bots consider seasonal raids, the new catalogue and a 100k local construction reserve; they retain capture priority. This is a basic policy, not evidence of competitive balance.
- Family catalogue cards link to native pages listing every owned city’s actual quote and team status. No nested work advice or obligatory city-by-city workflow. Selecting a map target opens one native radio-based expedition form directly beneath it; the target is fixed by that selection, with no repeated selector. Red “Valider l’action” opens the unchanged signed, read-only preview before sealing. Existing routes, native retry drafts and no-JavaScript operation remain supported.
- Remove Council action duplicates, redundant dateline, default frontier prose, neighbor text, empty ongoing-work section and historical-order clutter. Pending orders remain cancellable; active work/missions and immutable reports retain progress/history. Full reports, section headers, work families and attack context use a generated decorative local illustration atlas. No remote runtime image service or new private information is introduced. Both language catalogs are compiled.
- Reconnaissance, public rival commitments, prolonged sieges, prestige and other speculative buildings remain deferred in `backlog.fr.md`, including targeted damage to exterior irrigation works. Conquest and population tie-break remain the victory criteria. Capture costs and initial local stocks are unchanged.


## 2026-10-19 · Council news versus sealing receipts

- Council omits `order` letters titled « Décret scellé », including existing unstructured archives. They acknowledge reservations already visible in the sealed-order register, rather than a departure or payment. The full letter archive retains every original receipt unchanged. Departure, cancellation and invalidation remain visible events; distinct orders and other event kinds are never merged by title or Moon. This is a display filter, with no change to confirmation, persistence or simulation.
- Mixed-equipment raid letters retain their existing survivor-dependent observations: enough surviving defenders can describe varied attacker equipment, but neither side receives a numerical combativity score. Equipment tiers do not create separate battle letters. This revision does not change those combat or narration rules.
## 2026-10-19 · Raid cash accounts and forge clarification

- Keep military raid outcomes unchanged. New attacker battle letters recall the paid order total and every saved city funding share, then compare the carried loot with that expense as a provisional gain, deficit or break-even result. A successful raid can therefore be visibly cash-negative. Saved funding is authoritative for both local and legacy pooled economies; never reconstruct costs from current stocks or surviving headcounts.
- At return, append a final cash account to the initiating house's one expedition letter, counting only loot actually deposited in its current granaries after overflow. An origin captured by another house keeps its ordinary local return letter without the attacker's costs. The initiator still receives its cash account if all origins have changed owner or everyone died. Keep its historical paid shares even for a lost origin. Other houses' deposits are not the initiator's income. Human losses and foregone levies remain explicitly outside this Measures-only balance; no price, combat, financing or storage rule changes.
- Retain equipment values 100 / 120 / 145: ordinary baseline, reinforced (+20% over baseline), superior (+45% total). Levels replace one another; city forges affect only their own people, and expedition equipment remains frozen at departure. Local forges and legacy realm equipment are alternative saved rule versions, never additive bonuses. The guide explains this without disclosing numerical combativity in the game interface.
- Historical weapon finds and designs justify qualitative equipment progression, not a calibrated +20/+45 or +30/+70 combat score. [UCL's weapon survey](https://www.ucl.ac.uk/museums-static/digitalegypt/tools/weapons.html) distinguishes periods and surviving evidence. [The Met's Middle Kingdom battle-ax](https://www.metmuseum.org/art/collection/search/544279) describes a more lethal blade design, but is much later than the early setting and supplies no numerical army-strength multiplier. Keep these numbers as explicit gameplay parameters pending playtesting; no running reign is rebalanced from an unsupported historical percentage.

## 2026-10-19 · Moon news and local levy accounts

- Replace the resource ribbon's harvest countdown with the current absolute Moon number and the shared crescent icon. Finished reigns show their final closed Moon. Keep the exact automatic closure banner and the harvest milestone in Council.
- Council previews every recipient-authorized report from the last closed Moon, without a count limit; before the first closure it shows Moon 1's opening letters. A quiet Moon does not repeat older news. Date the news heading and retain full-report links. The letter archive has no arbitrary hundred-letter cutoff, so every preview can reach its full letter. Report kinds carry decorative shared icons alongside their readable titles.
- New return letters group all surviving origin contingents of one expedition by their current recipient. Preserve each city's exact survivors, deposited loot and overflow in separate paragraphs. Different expeditions and different recipients keep separate letters; an origin without survivors adds no empty news, and an annihilated expedition produces one loss letter. No target identity or another recipient's accounts are added. Existing archived reports are never rewritten; troop, loot and ownership rules are unchanged.
- Council lists each city's already accrued levy beside its available funds, stock and team status. Explain the next annual payment Moon and distinguish accrued, unavailable Measures from a forecast of the final harvest. The levy still accrues at closure and is paid at Moons 12, 24, 36 and so on, subject to local capacity; no forecasting or transfer rule is introduced.

## 2026-10-19 · Verification proportional to affected behavior

- Replace the blanket full-local-suite-before-every-push rule with three local verification levels: Presentation, Behavior and Full, specified in `docs/testing.md` and referenced by `AGENTS.md`. Choose by affected behavior and risk, not diff size. Focused runs still use real PostgreSQL where relevant, independent regression cases, full catalog collection and failure-on-skip. Native-core changes retain complete logic-only 100% statement/branch coverage; high-risk boundaries and unclear impact require the full local checkpoint.
- Shared layout, navigation, forms and JavaScript changes retain browser verification. The existing bilingual browser journey remains whole for now; no focused browser runner is claimed. CI continues running all existing layers, coverage and browser checks on every push and PR with PostgreSQL 17 and 18. Report selected local scope and CI/deployment evidence separately.

## 2026-10-19 · Current destination in the bottom menu

- Highlight Council, Expeditions or Works only when its own folio is displayed. Help, onboarding, reports, city folios, Decrees and read-only decree previews keep all three navigation items neutral. Draft return paths still use their originating section; that routing does not imply an active menu destination.

## 2026-10-19 · Scannable manuscript information

- The header keeps the full, wrapping chronicle title and compact resources. Help and the Council calendar/closure-review link live below the folio, above the footer; the three persistent destinations remain. A running automatic calendar has its own small Moon banner below the header, with a decorative crescent, countdown and a persistent exact UTC deadline. Without JavaScript the exact deadline remains readable; waiting, paused and finished reigns have no running banner.
- Council shortcuts use one aligned icon-and-label row per action. The guide index is a numbered vertical list following its section order. Both keep complete link labels, native keyboard navigation and 44px targets at narrow widths and enlarged text.
- Work checklists separate each city's selection heading, building transition, benefit, labelled cost/duration/available-funds facts, shortage and team status. Council account totals reuse the same fact component. Shortages remain explicit; no money, batch-selection, eligibility or timing rules change. Individual work forms link back to all Works, including saved Decrees URLs.
- Notices, marginal scribe notes and unsealed drafts share pale yellow paper, no border and a small shadow. Literary letters and decree prose remain intact. Both translation catalogs cover the new labels. Browser checks cover aligned lists, untruncated titles, structured figures, native return navigation, note styling and the running/no-JavaScript calendar banner alongside the existing bilingual journeys.

## 2026-10-19 · Review remarks: forms, atlas and clock boundaries

- Continue/Enter Council appears above Begin reign throughout the prologue. Council action links wrap with a real gap; each complete report returns to Council. Current copy uses « Fidèles disponibles » and « Pillez pour le butin ou capturez… » in both catalogs; archived reports stay immutable.
- Failed preparation, signed-draft reopening and confirmation return to the corresponding expedition or work form with the unsealed target, mission, headcounts or city checklist in its query. They reserve nothing. The expedition form displays fixed and per-person prices, each origin’s exact Hamilton share, free funds and local shortage, with live updates and native retry rendering. The reported 30-person raid costs 95,000 Measures: equal contingents pay 31,667 / 31,667 / 31,666. Empty granaries correctly reject it; no price or financing rule changes.
- The twelve-road map uses a new fixed Voronoi layout: all saved roads join shared territory borders, each starting house forms a triangle, and the three rival bridges are short. Older map versions retain their schematic layout; all saved road networks, ownership and eligibility rules remain authoritative.
- Starting a waiting automatic reign opens Moon 1 immediately and sets its first closure to the next strict UTC five/ten-minute boundary. The first Moon may be shorter, as stated before starting. Following deadlines advance from stored boundaries; resuming rounds up after preserving the remaining time. Only calendars explicitly started with this revision carry `clock_aligned`; running legacy calendars retain their deadlines and pause behavior. The schedule is visible in the prologue, guide and Council, and the exact next UTC closure stays alongside the countdown. Cron may process it slightly later; server deadlines remain authoritative.

## 2026-10-19 · Approved audit: local economy and deliberate frontiers

- New reigns use `economy_version=2`: present-resident yields are 100 / 130 / 200 Measures per Moon. Existing prices, durations, annual receipt, growth and local capacity remain unchanged. Missing/version-one economy markers preserve 100 / 200 / 300 and proportional pooled financing, including accepted funding plans. No running game is migrated or silently rebalanced.
- New local works reserve and debit only their destination granary. Multi-city orders remain atomic: any city shortfall rejects the whole batch without reservations. Each expedition origin pays its own per-person charge and a Hamilton-allocated share of the fixed departure fee, proportional to its sent headcount; whole-Measure ties use the existing deterministic allocator. Other granaries never contribute, and no transfer feature is introduced. Cancellation frees reservations before departure; no money has been spent yet. Legacy realm-equipment orders retain pooled funding when explicitly used with old forge rules.
- New `map_version=3` roads make each starting group internally triangular, with one bridge to each rival group (twelve roads). Each house initially reaches one city of each rival. Captures can expose further targets through the unchanged friendly-component rule. All saved version-one rings, version-two meshes and unmarked road networks remain authoritative.
- Council shows recent news first, with a city-account jump link above it and open accounts below. Each excerpt links to its complete recipient-authorized report. Orders use future dates only while sealed; active/completed orders describe effective and work-finish dates, while cancellations explain released reservations. The open Moon is visibly distinguished from closed accounts. The three main destinations remain unchanged; a shared header link reaches the Council closure review.
- Target reservation remains global and exclusive. Public engagement copy distinguishes the viewer's own order from another house's reservation without exposing hidden troop counts or order identifiers. New defender raid letters name the public attacking house and put survival-dependent force/equipment observations before the loss narrative. Archived reports remain immutable.
- Introductory page one and the guide explain the Moon cycle and automatic annual collection immediately. New scheduled reigns wait for an authorized, idempotent POST start, then establish a fresh first interval; merely reading or skipping the prologue does not start the clock. Already-running scheduled saves keep their deadlines. Calendar start is independent of the simulation's rules and does not add a turn.
- Railway cron uses a separate one-shot service (`railway.cron.toml`) every five minutes and the existing locked `tick_due` service, real server time, stored UTC deadlines and excessive-lateness pause policy. Page reloads read the result; client countdowns never authorize orders or close turns. Human multiplayer and simultaneous multi-house battles remain deferred.

## 2026-10-19 · Construction transitions, benefits and type hierarchy

- Keep one Works page and its atomic multi-city decree. Each building summary carries a short purpose; expanding it shows every owned city, its current building → next building, the specific economic or qualitative military improvement, cost and duration. Completed buildings stay listed without a fictitious quote; blocked repairs and prerequisites have explicit reasons.
- Busy cities retain their prospective upgrade and benefit. Active teams show the building under construction and its finish Moon; a sealed reservation is identified separately. When all cities are busy, complete, paused or finished, use the same city-row component as a read-only list, without a misleading order form. The server's ownership, affordability, team and upgrade checks remain authoritative.
- Put longer explanations under “Le conseil des bâtisseurs”: annual receipt of accrued levies, local granary overflow, walls versus raids/relief, restoration versus enlargement, and forge scope/frozen expedition equipment. Economic before/after values remain exact. Military improvements stay qualitative and private to the owner. Earlier realm-forge saves keep their shared rule and benefit description. No balance, archived report or stored state changes.
- Use relative body sizing and a larger explicit heading scale, including plain disclosure titles. City names, transitions, benefits and status notes have distinct sizes below their section heading. Browser checks compare computed visible heading/body sizes at normal and enlarged text settings, in both languages and on narrow screens. This revision adds no illustrations or separate building pages.

## 2026-10-19 · Territories, readable atlas states and compact pages

- Each city has a fixed clipped Voronoi territory around its existing public map position. These irregular cells tile the schematic sheet and stay attached to the city on capture. Clicking anywhere in a territory opens its city panel. Borders are decorative geography: road topology alone determines reach, and the map explicitly says so. No save, travel, ownership or combat rule is changed.
- Territory washes and borders use burnt earth, ochre and olive. Each house also has a consistent I/II/III seal, repeated in its city markers, legend and selected-city panel, so ownership does not depend on colour. Shared marker markup shows a double ring for your cities, a diamond for reachable rival cities, a simple circle beyond reach, and a dashed outer ring for an engaged target. The legend and accessible link names state these meanings; committed targets keep their warning even when they belong to the viewer. Reachability is projected using the same saved-road calculation as the expedition form.
- Use a 16px reading size with a 1.5 line-height, smaller headings and tighter paragraph, section and form spacing. Compact the account, lobby and game pages together, while preserving 44px native control/navigation targets and the existing responsive reading column. Change owning style rules; remove redundant mobile overrides and obsolete hit-circle styles. Shared components handle markers, house seals and status text.
- Older realm-forge quotes now show an exact shortfall and a visible, disabled preparation button when unaffordable. At equality the action is enabled. The duplicated inline price is removed; all decree preparation buttons use the existing restrained bordered action style. The server still validates every quote, and no resources are reserved by displaying it.

## 2026-10-19 · One list of named works

- The Works title introduces one shared building list; remove the repeated “Les ouvrages de vos cités” heading. Local forges and legacy realm-equipment forges use the same choice markup and existing decree form. Remove the dedicated realm-equipment section and its obsolete partial. Legacy forge choices still send `equipment` commands with their original realm scope, quotes and availability; no saved rules or reports change.
- Replace numeric upgrade captions with shared names: Premiers canaux / Réseau de canaux, Grand grenier / Silos de réserve, Enceinte de terre crue / Grande enceinte, Forge de la cité / Forge des maîtres. Repairs identify the existing wall being restored. City checklists name each intended building so mixed upgrade batches remain clear. City forge folios use Atelier d’armes for ordinary equipment, then the same two forge names.
- Names are pure narration values localized through both catalogs. Costs, durations and effects stay explicit and unchanged; names do not expose numerical combativity or opponent infrastructure. Keep the list readable when paused or finished, while hiding command forms. Reuse the existing work-choice and decree-form components, and remove obsolete heading styles together with their markup.

## 2026-10-19 · Contextual expedition atlas and clean presentation

- Replace the fixed circular atlas with stable irregular public positions, including interior settlements. This is schematic geography shared by all reigns, not a per-game random layout. Remove road edges from the drawing; the contextual panel lists actual connected neighbours. New reigns use `map_version=2`: fifteen roads, including six interior links, instead of the nine-road ring. Rotational symmetry gives every realm five initially reachable rival cities, compared with two on the ring, and the same distribution of two- and four-road cities. Friendly connected components still determine eligible origins. The mesh is a fixed, symmetric gameplay default rather than an untested random generator. Existing snapshots keep their exact saved roads, including those without a map marker; no migration rewrites a running war. Expedition timing is unchanged.
- Expeditions opens directly on the atlas and a contextual reading panel: beside the map on wide screens, below on narrow screens. Initially the scribe explains raids and capture; selecting a city shows its owner and fortifications. Own cities link to their accounts; reachable, unengaged rival cities offer raid and capture. These links preselect the existing native expedition form, which uses the same preview/seal workflow. Paused, ended and eliminated reigns offer no commands. All links and forms work without JavaScript.
- Remove the redundant expedition CTA, visible map subheading, repeated opponent-secrecy paragraph and expanded chapter introduction. Keep a compact chapter title and date, with dedication/status available to assistive technology. The resource ribbon uses shared line icons for grain and warriors with translated accessible labels and exact numbers.
- Keep the deployed local-forge rule: a city's forge equips its people and follows the city on capture. The owner explicitly allowed a different impact from their proposed realm-wide bonus; local equipment gives city capture a concrete military consequence and preserves the deployed balance and legacy compatibility. Higher forge levels remain upgrades of the same city building through ordinary Works and its team slot.
- HTML/CSS maintenance is a standing requirement: edit component styles in their owning section, remove obsolete markup/selectors together, avoid duplicate/dead rules and override patches, and reuse shared templates. This revision reuses the icon and expedition-form partials; the accessibility utility lives in shared CSS.

## 2026-10-19 · Three destinations, public atlas, local forges

- The owner approved the usability audit with three corrections: Moon closure remains provisional, Expeditions uses crossed blades, and a simple map should preserve the role-playing atmosphere. This supersedes the earlier five-link navigation and illustrated-map prohibition for this restrained public schematic.
- Council gathers news, accounts, commitments and standings; Expeditions combines preparation, movements and public geography; Works combines construction choices and progress. Three persistent icon-and-label links fit mobile safe areas. Keep existing folio/decree URLs for saved links. Reports are secondary Council reading. Manual closure and the scheduler retain their existing behavior; closure lives in Council rather than the resource ribbon or the main action sequence.
- A keyboard-accessible SVG schematic on off-white paper draws only the actual public roads, cities, ownership and target engagement. Links open the existing authorized city folios. Own cities use a double ring, so ownership does not depend on color. The entire map fits narrow screens, with city hit areas of at least 44px at 320px viewport width. Distances are explicitly schematic and do not alter journey duration. There are no external map assets or inline CSS.
- New snapshots carry `forge_version=2`. V1 forges are local city works, use the same team slot as other construction, permit one atomic multi-city preview/seal/cancellation, and follow the city and its current ruler on capture. A completed level equips the city's defenders, new inhabitants, relief and subsequent expeditions. Equipment remains qualitative in player projections; numerical combativity is never disclosed.
- Retain the existing equipment levels and durations (8/14 Moons). Allocate the former three-city minimum proportionally: each city costs `max(600000, 600 * city_population)` for level one and `max(1400000, 1400 * city_population)` for level two. Thus improving three initial cities preserves the former total cost. This is a documented implementation default pending playtesting, with no rebalance of existing reigns.
- Expeditions freeze each origin's equipment at departure and sum exact cohort strengths at combat. Uniform relief keeps the existing head-count allocation. Mixed relief is apportioned by strength with Hamilton allocation, then rounded down to whole people per origin, never exceeding the attack-strength cap. Reports describe mixed encountered equipment qualitatively.
- Snapshots without the forge marker, or with version one, retain realm equipment, active projects, accepted quotes, departure equipment and original prices. No data migration rewrites their state or immutable report archives.
- Shared work-choice, order-register, equipment and navigation partials avoid parallel markup. Both languages cover the new interface and local-forge narration. Live work totals show remaining funds or a shortfall; the server still validates the entire batch atomically.

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

## 2026-10-16 · Folios, decree workflow and bilingual Moons

- The supplied discussions and HTML preview are design references. Preserve the actual game’s city names, costs, local capacities, work effects, population rules and cancellation rules. In particular, canals increase tax yield; they do not add a population-capacity mechanic.
- Replace unfolding city accounts with scannable prose summaries and direct links to dedicated city folios. A folio carries its city selection into a decree form. Public rival folios contain only ownership, visible walls, roads and engagement status. House accounts remain ordinary prose with headings, line breaks and bold values.
- Keep resources visible in a compact sticky header with short navigation subtitles. Decree choices show real level-dependent prices and durations, then open one form. Drafts explicitly reserve nothing; sealing reserves resources, and closing the Moon executes sealed orders. Show the sealed count beside the closing action. Do not invent unread counts without read tracking.
- Letters are chronological articles; reference rules alone use native disclosures without plus/minus styling. Shared templates and `common.css` replace repeated markup and obsolete dashboard/game styles. In-game pages remain white, quiet and image-free. No inline styles or preview-only buttons remain.
- French and English cover account forms, navigation, rule errors, JavaScript feedback, folios, previews, statuses and new report narration. The footer language switch preserves signed unsealed drafts; reopening validates membership, signature, revision and calendar without mutation. Raw report title/body and recipient authorization remain unchanged. New `Report.content` stores a pure narration expression tree, rendered at read time in the chosen language. Earlier unstructured French letters remain explicitly labelled original archives rather than guessing missing parameters or rewriting history.
- New games use `calendar_version=2`: `state.month` is the open Moon, initially 1. Tick target 1 closes Moon 1, accrues its tax, executes its orders, writes reports dated 1 and opens Moon 2. Moon 12 pays the first harvest after twelve closures. A decree sealed in Moon 1 departs at its closure, combats in Moon 2 and returns in Moon 3. A work starting in Moon 1 with duration four finishes in Moon 5. A 120-Moon reign finishes when Moon 120 closes, retaining that final date.
- Existing snapshots without the calendar marker, or explicitly using version one, keep the elapsed-month implementation and all stored deadlines, seeds, reservations and receipt/tick identifiers. `closing_moon` supplies both manual and scheduled tick targets. Projections distinguish the open Moon from the last closed Moon and hide Moon 0. Bot decision intervals, protection checks and work progress continue to use elapsed intervals, preserving simulation outcomes. API clients must use `view.open_moon` for the closure target, not blindly add one to `view.month`.
- Apply migration `0002_report_content` before running the updated web and calendar workers. No data migration shifts existing snapshots or rewrites their archives. Translation sources and compiled catalogs are checked in; after editing either language run `python scripts/compile_translations.py`. The production build recompiles them as well.

## 2026-10-16 · Restore realm-wide city actions

- The multi-city directive takes priority over city-centric navigation. Work choices on Decrees now unfold the shared city checklist in place; a single draft and seal apply to every selected city. Native disclosures retain upfront costs and effects without plus/minus styling. Optional city folios remain for inspection and preselection, and existing dedicated action URLs remain valid.
- Select-all and clear controls operate only on available teams within their own work form. Live counts and total costs are estimates from existing per-city quotes; server-side affordability, ownership, reservations and atomic batch confirmation remain authoritative. Checklists also submit normally without JavaScript.
- Railway already follows the deployment branch. Shipping consists of passing the full checkpoint, committing the complete change and pushing that branch. Do not create a second hosting project or require a Railway CLI deployment for this workflow.

## 2026-10-17 · News and upcoming events first

- The opening folio is an overview of the latest four recipient-specific reports (short excerpts linking to the full archive), followed by dated milestones for sealed decrees, active works, equipment, combat, returns and harvest. City accounts remain available below and through their folios; the opening prose no longer repeats the sticky resource totals.
- Use direct, bilingual navigation: Overview, Decrees, Constructions, Wars, Reports. Constructions tracks active work and equipment; Wars tracks the player's expeditions and public geography. Planning and sealing remain on Decrees, including the existing multi-city workflow. Existing domain, decree, city and letter URLs stay valid.
- Milestones use only the existing authorized player projection and immutable recipient reports. They describe scheduled events, not promised combat outcomes, unread counts or hidden rival activity. Finished reigns show results and reports without future milestones; paused calendars label their dates as suspended. No game rules or stored reports change.

## 2026-10-19 · First steps, rules and city accounts

- Newly created games redirect to four short, skippable manuscript pages explaining the territorial goal, resources, orders and expeditions/calendar. Native previous/next links work without JavaScript; the guide can replay them. Normal game URLs still open the Council, so existing games are unaffected. Prologue and guide reads never mutate state, reserve resources or pause the automatic calendar; scheduled games explicitly say their clock continues. No introduction flag or schema migration is needed.
- Keep the three main destinations. A compact persistent “Comment jouer” link opens an indexed reference whose victory duration, cancellation rules, forge scope and calendar reflect the current game. This replaces the old inline rules disclosure. Illustrations remain future work; the prologue uses ordinary text, with no slideshow dependency or automatic navigation.
- Council begins with a compact owned-city ledger linking inspection folios and displaying local stock/capacity, free funds and team availability. This supersedes the earlier news-first order and replaces the longer city summaries. Remove the geography disclosure; retain public standings under “Les prétendants au trône”. Rival populations, stocks and forces remain private.
- First submission is “Valider la sélection”, explicitly followed by a read-only review. The review heading is “Vérifier votre ordre”; only “Confirmer et sceller l’ordre” reserves resources. Preserve the visible reservation amount, signed preview, affordability guards and existing cancellation boundary. Reuse one form submit control for work, legacy equipment and expeditions.


## 2026-10-22 — Strategic preparation and affordable campaigns

The attached approved discussion, with the owner's subsequent corrections, defines economy version four. Existing snapshots and archived reports retain their rules and content. New reigns start with 900,000 Measures per city (owner's opening-stock follow-up); economy three and older keep 600,000.

Raid/capture tariffs become 5,000 + 1,000/person and 50,000 + 2,000/person. Raids distinguish dispersed, contested and intercepted encounters, cap crop protection at ninety percent, bound destruction by survivors, and can cause bounded noncombat losses or one exterior watch/shelter damage. Respite follows actual loss suffered by the target. Exact thresholds and rates are in the synchronized French gameplay reference.

Initial defenses are ×3, then ×4/5.5/7. The owner explicitly rejected a proposed reduction of siege supplies to 100: **one Moon is one month, and a single siege needs 500 Measures per present inhabitant**. Exact sufficiency holds; shortage capitulates immediately. No sustained siege or arbitrary grace period is introduced. Held-siege losses become 2%/1%, shortage 4%/8% without extra civilian famine deaths. Rational wall integrity prevents rounding drift; held sieges only wear walls when siege equipment is present, with a seventy-percent floor that cannot heal already worse damage. Threatened cities export no relief during the same combat phase.

Repairs share the local crew. Work that would finish beyond the configured end is rejected; a first economic effect after the end is visibly flagged. Simple resource convoys take two Moons and arrive after combat; stock and fees are reserved at sealing. Refuge routes for convoys and military contingents are fixed at departure and ownership checked again on actual arrival. Captured origins transfer only present inhabitants: travelling cohorts retain their house, then either return, find the fixed refuge or demobilize without strengthening the enemy's Faithful.

Strategic information belongs in the preparation panel, Council and own-city folios, not additional map overlays. Visible post-order reserves and siege warnings precede native optional ledger notes. The user favored contextual help provided it does not conceal essential decision information. Own equipment remains qualitative; enemy knowledge comes only from dated immutable recipient reports. New combat audits record private structured outcomes for evaluation; existing exports only select authorized chronicle projections, never those private audit details.

The all-house historical/RP narrative is deferred with the owner's agreement. A later battle-first chronicle should derive from structured events, reconcile perspectives, avoid invented facts, and become available with the existing end-of-reign permissions. It is not part of this release.

## 2026-10-23 · Retroactive compact discussion archive

- Add `format=compact` beside the complete JSON in the completed-reign book, for both existing scopes and languages. Derive it solely from the existing authorized archive; no new state, backfill, replay, private combat audit, schema migration or gameplay change.
- Compact schema one identifies itself as `yaara-condensed`. Keep all recipient letters, ranking, rule versions and explicit missing-account Moons. Economy rows have a column header and retain every recorded Moon. Per-city field changes retain balances, population, casualties, works, levels and damage while omitting map geometry, repeated prose, forecasts and UI affordances. An ownership-loss record removes the previous city observation. Order observations are emitted only when changed, including final-only records; a repeated order is never another expenditure.
- Include compact final accounts and surviving final missions. Historical mission snapshots are omitted, not claimed to be reconstructed. Explain observation gaps, quote-versus-spend semantics, accrued levy, duplicated battle perspectives and unavailable alert/roll/counterfactual evidence in the download. This is an analysis aid, not an automatic claim about raid profitability or luck. The complete original export remains available.
- Use the Full local checkpoint to verify disclosure boundaries and the new download flow. The current gameplay reference remains accurate: no rule, balance, calendar or player consequence changes.

## October 26, 2026 — Map workspace and courrier

The owner approved the map-first assessment and requested its implementation,
retaining short roleplay narration and existing illustrations for actionable
courrier. This supersedes Council-first entry, compulsory multi-city work
selection and the three Council/Expeditions/Works primary destinations. New
artwork is deferred. See `map-workspace.md` for the interaction and case contract.

Primary navigation is Map, Mail and Reign. Reign retains aggregate accounts,
standings, historical reports and calendar controls. Existing family/batch URLs
remain a secondary convenience. Local work selection uses the same quote and
confirmation services with one explicit city, and quotes remain read-only.

Own mission identities, targets, departure cities and origins are added to the
existing recipient projection for map/schedule links. Enemy intelligence is not
expanded. Map routes use saved links; browser draft routes are indicative and
server review remains authoritative. No calendar, economics, combat, persistence
schema or saved-rule migration changes. Reading receipts are optional local
browser preferences, scoped by game and actor, and never rewrite reports.

## October 27, 2026 — Mockup-led working sheets

The furnished HTML becomes the UX baseline, retaining the deployed palette and
features. Move house identity and harvest access into the compact map header,
place the house legend above the board, make local work previews immediately
available in owned-city sheets, open reachable enemies directly into expedition
preparation, and give Courrier its own framed window. Sheet headings and close
actions remain visible while content scrolls. Exact troop inputs gain optional
sliders/step controls and the review action stays beside its live totals.

This revises presentation, not rules or intelligence. Earlier recommendations
remain authoritative where the mockup differs: browser zoom stays enabled, no
map zoom is needed for nine cities, free crews are not alerts, own route identity
is preserved, actionable RP mail stays separate from dated commitments, and
preview/seal remain distinct. Existing artwork, batch workflows, historical
snapshots, convoys, private recruitment and account settings are retained.
