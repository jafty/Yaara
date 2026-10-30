# Map workspace — October 26, 2026

## October 30: agriculture and illustrated army preparation

The construction family formerly labelled “Aménager les canaux” is displayed as
“Développer l’agriculture” in French and “Develop agriculture” in English. Saved
action keys, level names, report message identities, costs and effects remain
unchanged. The physical canal upgrades remain part of agricultural development.

Army preparation includes one modest panoramic scene before its native form,
shared by the focused map sheet and the legacy expedition page. Its equipment
follows the owner's soldier drawing, with varied outfits and weapons. The image
does not replace mission choices, quantities, costs or warnings. An unselected
expedition page retains its map without an army illustration.

The [folio art direction](illustrations.md) records the supplied 3:1 drawings,
complete scene frames and shared construction-start news artwork. This changes
presentation and copy only; the gameplay reference remains accurate.

## October 29: compact works and nearby military refuge

Work-list rows show one next/current building title, a 56px square illustration,
an adjacent action, and compact effect/cost/duration details. Maximum-level
buildings retain their effect and their disabled upgrade action. Detailed quotes
retain the current-to-next transition and all existing checks. Both languages,
320/390px layouts, 200% text and native no-JavaScript forms remain supported.

For economy-four military returns, a diverted route starts at the attacked city
and follows one saved road to its friendly neighbouring refuge. It does not show
a journey from the captured home across the realm. This reflects the owner's
October 29 rule correction recorded in decisions.md; ordinary returns and
convoys keep their existing route contracts.

The owner's approval supersedes earlier Council-first and compulsory batch-work
presentation decisions. No saved rules or reports change. The October 27 follow-up below authorizes map artwork.

## Interaction contract

- Entry opens all nine cities; selecting one reveals its saved roads. Subtle green
  and red territory overlays distinguish owned and rival cities. No map zoom;
  browser zoom stays enabled.
- Selecting an owned city shows granary stock and capacity, the free stock when
  reservations exist, and available Fidèles above a compact
  briefing with present population, team availability, assigned
  work and relevant local commitments, followed by unboxed command rows for
  construction and convoys. The shared harvest date remains in the header. Notices
  occupy their own space above the map rather than covering it.
  Each command opens a full sheet; return
  restores the city menu, or the works list when leaving a work detail. City
  accounts remain reachable from precise alert and report links. Resources remain
  visible in action sheets; city descriptions leave fortification levels to the
  map artwork, while accessible map names and damage warnings retain that information.
  The city panel has no tab bar or route list.
  A reachable enemy opens preparation directly. The map and city menu share the
  workspace until an action is opened. The closure notice is omitted; the Council
  retains the Moon closure control. Context navigation retains the map canvas,
  supports browser Back and respects reduced-motion preferences.
- Local works show only that city's next quote and use a hidden city field, never
  a compulsory checklist. Switching cities preserves the work family, not a draft.
  The realm catalogue remains a secondary batch convenience.
- Preview is read-only, in the map workspace. Seal reserves; closure spends.
  Existing services revalidate authorization, deadlines, funding and reachability.
- Own sealed, outbound and returning expeditions have separate map states. Draft
  routes use the public friendly graph and automatic frontier rule. Enemy warnings
  identify only the threatened city and intelligence already projected to its owner.
- Nouvelles opens recent Moon reports, followed by Alertes, Échéances and the full
  Chronique. Actionable items retain short
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

## October 27 — Map art and fluid context navigation

The owner clarified that “clipping” meant choppy panel animation. Retain the
sheet shell between views of the same type, with a brief content fade; opening
and closing use short transform/opacity transitions. Honor reduced motion.
Keep decoded city artwork and the canvas mounted while the game revision is
unchanged; refresh the authorized drawing when the revision changes. Abort stale
requests before they can replace a newer view. City tabs sit outside the scrolling
body; their URLs open at the top. Precise incoming mail fragments still scroll the
body to their target. Escape, history and native URLs remain supported.

The shared header replaces the bottom menu throughout the game. The Yaara mark
returns to the map, the named house opens Reign, and Courrier keeps its warning
count. Secondary folios retain settings, language and home controls in their footer.
Old header/menu markup, owning styles and bottom padding are removed together.

Generated art uses a transparent six-cell atlas: open settlement, timber palisade,
reinforced palace, stone walls, legacy earth wall and legacy great enclosure.
Walls are plain, with no arrow slits. Existing public wall levels choose the cell;
no new opponent information is projected. Green/red banners express relation to
the viewer; the existing emblems and territory colors distinguish all three houses.
Keep reachability and engagement through underlined/muted names and dashed banners; remove the white circle bases and update the legend. Terrain is decorative worn parchment
with very light dunes and sparse muted-green palms, including near the center.
No zoom/pan or terrain mechanics are added. Shared borders use reversible irregular curves. A fixed presentation layout spreads
the cities organically; saved road connections and game rules remain unchanged.

Independent variations, written before implementation: `map-header-navigation`
(map/mail/Reign), `map-fixed-activity-tabs` (works/accounts/convoy),
`map-public-fortification-art` (four current and three legacy levels), and
`map-curved-public-geography` (three saved geographies). The browser journey checks
retained sheet/art nodes, Construire starting at scroll zero, no repeated entry
animation, reduced motion and existing native/local-order flows. The full local
checkpoint is selected for the broad shared header/navigation change.

The owner's subsequent art direction uses the existing fortifications, granary,
forge and works atlas as direct references: frontal compositions, thin irregular
ink contours, weathered plaster and painted mineral/terracotta bands. City artwork
is smaller, without a pedestal. Palms and terrain remain decorative. Seven further
variations cover `map-organic-layout` across three saved networks and
`map-selected-roads` for the unselected board and three city degrees. Browser
checks additionally verify roads start transparent and circle bases are absent.
The preview uses the same prepared view as every other map, preventing a return
to the old drawing when reviewing an order.

At enlarged text sizes, mobile sheets may cover the resource header so their fixed
tabs and scrollable decision content remain usable. The close control stays in the
viewport. Secondary native folio fragments use the measured header height and
settle after font reflow and same-document fragment changes; no game data is involved in either behavior.

The latest artwork pass simplifies the six city silhouettes and uses faded pigments
and worn parchment texture. Their transparent 512-pixel cells, fortification mapping,
plain walls and separately drawn banners remain unchanged.

## City sheet and papyrus revision

The workspace permanently divides into equal map and decision areas, including
entry, city selection, mail and review. Entry and the Reign link share a single
house overview template. Onboarding uses the same shell; its finish and skip links
enter the map. The former Council layout wrappers/styles, mail overlay wrapper,
conditional city split rules and panel entry animation are removed. Secondary
batch-work, help and archival folios remain supported features.

Presentation verification: native forms, responsive layout, enlarged text,
keyboard, selected roads and existing order journeys. Independent
`map-permanent-overview` cases cover map, Reign and onboarding entry. No game
rules or persisted data change.

## Mobile readability and map orientation

The default Map pane explains selection, public reachability, flag states and
roads, followed by house emblems and links to their cities. The Reign destination
retains accounts and calendar management; reports and deadlines remain in
Nouvelles (formerly Courrier). No reference disclosure floats over the board.
Guest account controls live in the pane content rather than covering map or text.

Territory SVGs fill the frame without letterboxing or padded margins. Each city
has a separate, proportioned SVG marker in the same native anchor, so artwork
and names stay readable while territory geography adapts to the pane. Roads use
the same public coordinate system. Native links, keyboard focus and saved game
rules are unchanged. Compact headings and guide copy leave more decision space.

Presentation checks include bilingual PostgreSQL rendering and native browser
journeys. The map journey explicitly checks city-name bounds and edge-to-edge
territories at 1440×1000, 390×740 and 320×640, with and without JavaScript.

## October 27 — Compact header and decision-first mobile planning

The owner's latest screenshots and follow-up supersede visible resource captions,
the separate Reign subtitle and harvest row, and the permanent equal mobile split.
The header shows three icon/exact-value resources and an inline harvest-Moon link.
Names remain available to assistive technology and on hover or keyboard focus.
The house name stays a single clipped line with its full name available; there is
no repeated game title. An envelope labelled Alertes retains the unresolved count;
zero is neutral. The shared news destination still contains schedule and archives.

City and owner share a compact heading. Body text is 14px at normal browser size,
with 16px number fields and 44px touch targets. Each selected mobile sheet receives
most of the workspace; an explicit expand button uses the whole screen and Escape
first restores the split. Short screens and enlarged text automatically give the
decision sheet the full viewport, including without JavaScript. Covered map/header
controls become inert in the enhanced flow; native close links remain available.

Army totals and their form-associated review button are siblings of the scrolling
body, so they never cover troop fields. Native number inputs share a row with
progressive decrement/increment and maximum controls. Each city shows its
available troops and exact local charge; an accessible i disclosure keeps equipment
and siege-reserve details optional, with shortfall warnings always visible. Dates,
mission choice and minimum troops remain in the main flow; explanatory formulas,
break-even guidance and rules move into a native disclosure. Convoy labels sit
above equal-width native fields. No costs, rules, authorization or stored data change.

Independent bilingual contracts: `planning-expandable-sheet` for map/city/mail/review,
`planning-native-army`, `planning-envelope-news`, `planning-convoy-fields`,
`planning-compact-city-identity`, and the revised accessible `layout-resource-labels`.
Browser journeys verify expand/restore, retained drafts, unobscured army fields and
review controls, mission switching, aligned convoy fields, native forms, narrow
screens and 200% text. Regular-size captures are separate from accessibility stress
captures. The native core and gameplay reference remain unchanged and accurate.


The owner's subsequent component review rejects dashboard cards and gauges as
an organizing model for this manuscript game. Own-city means occupy one ruled
ledger row: free grain and available Fidèles. Capacity, reservations, absences and
forecasts remain in Comptes; overflow, siege shortfalls and inherited-troop
restrictions remain visible when they affect a decision. Equipment capabilities
are not repeated above the local works that already explain them. Native mission
radios replace the paper tiles; troop sliders are removed. Dates and army totals
read as ledger lines. Number fields and step/max controls retain full touch areas.
Crew availability is plain text. Route links are an optional disclosure because
selected roads already appear on the map.

The component review applies the same criteria throughout the workspace:

| Component | Primary decision information | Secondary detail |
| --- | --- | --- |
| House header | Free means, current Moon and unresolved alerts | Resource names on focus; links to harvest and house records |
| City heading | City and current owner | Full long names without enlarging the heading |
| City ledger row | Spendable grain and available Fidèles | Balances, capacity and forecasts in Comptes |
| Local works | Next capability, effect, cost, duration and availability | Illustration and full quote on the named work page |
| Army order | Mission, dates, minimum, quantities, local charges and warnings | Equipment/reserves behind i; formulas and rules in a disclosure |
| Army review line | Gathered troops, price and return ceiling | Read-only review before any reservation |
| Convoy order | Origin, destination, cargo and arrival | Native reference notes |
| Map and letters | Public geography and recipient-specific facts | Route list and archived reports opened deliberately |

`planning-city-free-means` checks that the row shows free grain after reservations
while the accounts retain total stock and capacity. No simulation changes apply.


## October 27 — Stable map proportions and focused action folios

The owner's next review rejects the compressed map proportions. Keep the map's
native 680:500 frame at every viewport and preserve SVG aspect ratio. Selecting a
city, opening work/convoy/army preparation and expanding a sheet must retain the
same map dimensions at that viewport. Letterboxing around a proportional desktop
map is preferable to changing its geography. Remove all state-dependent 28/72,
20/80 and 8/92 map splits. Mobile action folios cover the map, with a text Retour
control that returns directly to the city or map. Native URLs, Escape, browser Back
and retained map artwork remain supported. Explicit expansion also overlays the
map, rather than reallocating its space.

Raids use a torch and conquest uses a flag over a fort, with visible Piller and
Conquérir labels. Saved command identifiers remain unchanged. French UI vocabulary
uses conquête; canonical rules and stored reports are not rewritten.

Building lists use small square illustrations. Building detail views retain a
modest 3:2 rectangle showing the complete original composition. List cost/duration
pairs show grain/moon icons and numbers together; names and units remain available
to assistive technology. Compact Préparer actions open the existing read-only
preview, followed by the existing seal. They never start construction on a GET.

The owner's final follow-up removes arrows throughout the interface: navigation
suffixes, directional map heads and comparison symbols. Comparisons use à/to and
convoy prose uses vers/to. Expansion uses plain frame corners. Native disclosures
use underlined text instead of triangle markers; keyboard operation remains native.
House names and original message identities are preserved.

Independent contracts: focused-action-sheet, focused-conquest-choice,
focused-illustrated-work, focused-rectangle-work-detail and focused-no-ui-arrows.
Browser journeys assert the map ratio and unchanged dimensions, focused native
forms, one-click return, square list/rectangular detail artwork, readable numeric
pairs and the existing review/seal flow in both languages and without JavaScript.

### Navigation and order review

The Yaara mark leads to the website home; Carte returns to the map. The house name opens reign controls, with Moon review first and a direct header link for authorized manual games. Scheduled start and pause controls remain in the same reign view. News shows the recent Moon and links to the complete report archive; alerts and deadlines remain separate. The existing archive URLs and report anchors continue to work.

Order review presents the cost, timing, local funding and material warnings before sealing. Confirmed orders in the deadlines view offer a direct return to the map. Army preparation labels each city's equipment disclosure explicitly. The city briefing shows total inhabitants with a people icon and distinguishes those present when residents are away; available Fidèles use a military icon. Selected saved connections are drawn as subtle curved dashed routes without changing the road graph.


## Post-playtest routes, news and city feedback

All saved public roads remain visible as dark-grey dashed curves. Authorized
military and convoy commitments follow those same curves: solid red toward an
enemy city and solid green toward an owned city. Return routes retain their
authorized destination, including diversions; settled or lost contingents have
no remaining line. Drafts and sealed departures still respect owned transit
territory. Movement rules, saved roads and opponent secrecy are unchanged.

The envelope shows unread latest-Moon news plus unresolved alerts. The News and
Alerts tabs retain separate counts, with unresolved alerts highlighted. Reading
a letter never resolves its warnings. Automatic read detection observes the
compact letter heading within the scrolling news pane; an explicit read button
remains available when observers are unavailable. Read preferences use local
storage, session storage as fallback and memory for enhanced navigation when
both are denied. Persistence through a full reload requires browser storage.

City figures have a native explanation of stock/capacity, reservations, levy,
inhabitants and available troops. Deadline dates and their destination form one
compact wrapping link per commitment. Target/rules disclosures use restrained
body-sized links. Target knowledge shows only the latest stored recipient
observation; older encounters remain in the full archive.

Rejected local orders display their reason within the action sheet while
retaining editable quantities. Incoming threats and advisory siege warnings do
not prevent otherwise valid preparation. Successful or repeated manual Moon
closure returns to the map without an extra flash notice; errors remain visible.


## Owned-city crew marker

A small tools symbol marks an owned city whose team is reserved by a sealed
construction/repair order or occupied by active work. No symbol means available.
The city link announces the busy state to assistive technology; the existing city
panel retains the assignment and finish date. Enemy crew activity remains hidden.
The marker uses the existing authorized `busy` field and does not change rules,
saved data, map geometry, or city navigation.


## October 29 — Desktop planning and focused Moon review

Desktop (900px and wider) retains the equal map/decision workspace for works,
convoys, army preparation and review. Action sheets stay in their column; the
header and map remain visible, interactive and unchanged in size. Expansion is
mobile-only and resets when entering desktop width. Existing mobile overlays,
forms and return controls remain intact.

The header's manual Moon link opens a focused read-only review within the same
sheet shell, showing the existing closure explanation and native POST control.
Reign keeps its full records; the focused review omits standings, onboarding and
footer utilities. Context navigation includes Reign and preserves Back/Escape.

Before implementation: browser variations cover desktop works/list/detail, army,
convoy, review, map interaction, mobile expansion then desktop resize, and focused
Moon review/return/Back at 1440/390/320px, both languages and native fallback.
HTTP `desktop-focused-moon-review` checks the isolated review and unchanged state.
