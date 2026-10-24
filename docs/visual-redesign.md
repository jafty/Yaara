# White manuscript: maquette audit and first implementation

The October 24 references (`1000062811.jpg`, `1000062810.jpg`, and
`1000062809.jpg`) support an evolution of Yaara's literary interface: a white
reading surface, a clear type hierarchy, and visible contextual illustrations.
They should guide the visual composition, not supply game facts or new flows.
The implementation starts from deployment commit `defde11`.

## Art direction

Keep the manuscript, scribe, self-hosted Alegreya, Egyptian pylon icon and
existing contextual illustrations. Use near-white `#fdfcf9` for the page, header
and navigation, charcoal `#302c26` for text, terracotta `#954a35` for actions,
mineral blue `#285c69` for reading links, and muted brown rules. The beige is
carried by the illustrations and map, rather than a tint over the entire game.

The owner rejected the first screenshot pass: repeated parchment rectangles
felt blocky, reduced text contrast, and duplicated the texture already baked
into the small illustrations. The revised direction keeps reading text on a
clean surface and uses open editorial rows with fine rules. Only the map and
existing artwork carry worn parchment; callouts use a quiet, solid tint.

Building illustrations are substantially larger in the catalogue and city
folios. Catalogue titles span the full row above the illustration and facts;
they are no longer squeezed beside tiny thumbnails. Selected work-family art
also has more room. Keep default body text at 17px and avoid synthetic torn
edges, stains, decorative gradients and additional ornamental borders.

## What to retain and adapt

| Reference | Decision and reason |
| --- | --- |
| Large literary headings and thin dividers | Adopt. Give the hierarchy more room without replacing the scribe's voice. |
| Light three-destination bottom menu | Adopt. Keep the current destinations, labels, icons and active state. |
| Short landscape illustrations | Adopt a 2:1 frame for noncompact scenes, cropping a centered 3:2 composition. Thumbnails retain 3:2. Existing atlas cells keep their proportions and cannot bleed into neighboring scenes. |
| Parchment everywhere | Keep it in the artwork and map. The rejected first pass showed that textured text panels compete with the existing parchment-backed illustrations. |
| One city dropdown for works | Do not copy. Yaara deliberately supports choosing several cities and reviewing/sealing one atomic order. Improve the existing checklist's grouping and selected state. |
| Expand a building within the catalogue | Keep the existing family page and native return link. Moving the form into an accordion would be a flow change. |
| Direct “validate” button on preparation | Keep preparation → review → seal → Moon closure. A visual redesign must not make an unsealed order look committed. |
| Illustrated Council story | Keep the existing contextual scenes and immutable report excerpts. Do not invent work progress, completion dates or an unread count to match the reference. |
| Numerical examples | Use the current authorized projection throughout. The maquettes' stocks, capacities, durations and unknown defenses are not requirements. |

## Map feasibility

An illustrated map is feasible without a GIS library, new API or expanded player
projection. The current SVG already has public settlement coordinates, territory
polygons, ownership, reachability, selected-city state and authorized road links.
Native SVG links provide keyboard operation and work without JavaScript.

Retain that interactive layer and place decorative artwork below it. City labels,
house marks, selection and road links must stay live elements, never lettering
baked into an image. Decorative buildings must not imply a rival's hidden
building level, wealth or army size. A river can be scenery, but cannot imply a
movement barrier or navigable route that the rules do not implement.

The first implementation reuses the existing terrain, reduces territorial tint,
uses dashed boundaries, distinguishes houses with terracotta, blue and olive,
and emphasizes the selected marker and boundary. It preserves all nine cities,
all current hit areas and the saved map variants. It does **not** claim to
reproduce the reference's painted river and settlement panorama.

A subsequent art pass can add a label-free landscape and neutral settlement
vignettes beneath this layer. It needs composition checks for both current and
legacy coordinates. The maquette's six-city, wide composition cannot replace the
actual nine-city sheet unchanged. Compressing the SVG to that aspect ratio would
also distort markers and make the closest cities harder to select on mobile.

## Implementation boundaries

- Shared palette and font declarations live once in `common.css`; layout rules
  stay in the existing manuscript and pre-game stylesheets.
- Existing shared templates and CSS owners are edited directly. Obsolete
  selectors and the unused seal styling class are removed with their callers.
- Account, guest and operator screens use the same palette and font family.
- No game rules, projection fields, endpoints, stored reports, authorization,
  form names, action URLs or translations change.
- Narrow screens, 125%/200% text, visible resource captions, touch targets,
  keyboard focus, native disclosures and no-JavaScript submission remain
  verification requirements.

This is the Presentation verification level in `docs/testing.md`. The existing
browser checks now distinguish the landscape frame from the undistorted source
composition, require the white page and decode the existing map parchment. Existing
HTTP contracts protect information, navigation and batch workflows. The current
gameplay reference remains accurate; no rule documentation update is required.

## Local verification

- Ruff lint and format checks passed; all 1,552 case IDs collected unchanged.
- 536 affected presentation, map, work, alert and illustration cases passed on
  disposable PostgreSQL 17, with no skipped cases.
- The complete French/English game browser journey passed, including 320px and
  390px layouts, 125%/200% text, keyboard access, native no-JavaScript forms,
  batch preparation/sealing/cancellation and expedition/report flows.
- The recruitment journey passed in both languages: guest play/account saving,
  operator management, three invitation seats, waiting-room entry, identity
  handoffs and the no-JavaScript fallback.
- Desktop and mobile screenshots were inspected. The 320px header initially
  exceeded its height budget; reducing the title's flex basis fixed it without
  truncation or hiding resource labels.

These are local Presentation checks, not a claim that the entire simulation
suite ran locally. CI still owns the full PostgreSQL 17/18 checkpoint. GitHub's
CI-status API returned Forbidden in this environment; Railway deployment has
not been verified here.
