# White manuscript: maquette audit and first implementation

The October 24 references (`1000062811.jpg`, `1000062810.jpg`, and
`1000062809.jpg`) support an evolution of Yaara's literary interface: a white
reading surface, a clear type hierarchy, and visible contextual illustrations.
They should guide the visual composition, not supply game facts or new flows.
The implementation starts from deployment commit `defde11`.

## Art direction

Keep the manuscript, scribe, self-hosted Alegreya, Egyptian pylon icon and
existing contextual illustrations. Use near-white `#fdfcf9` for the reading area,
pale stone `#f0eee9` for the header, deep mineral green `#263f40` for the bottom
menu, charcoal `#302c26` for text, and terracotta `#954a35` for actions. Use
mineral blue `#285c69` for reading links, and muted brown rules. The beige is
carried by the illustrations and map, rather than a tint over the entire game.

The owner rejected the first screenshot pass: repeated parchment rectangles
felt blocky, reduced text contrast, and duplicated the texture already baked
into the small illustrations. The revised direction keeps reading text on a
clean surface and uses open editorial rows with fine rules. The map and
existing artwork carry worn parchment; callouts use a quiet, solid tint. The
mission buttons also use the existing light papyrus asset, with small pictograms
and a terracotta selected state.

The subsequent review rejects illustrations squeezed alongside headings. Council
and expedition headings are now text-only. The building register and city
summaries remain text-only. The latest Works review restores visual scanning
with a two-column, unboxed illustrated catalogue, falling back to one column
on narrow screens or with enlarged text. Each tile keeps every named upgrade's
grain/cost and moon/duration visible. Its explanatory purpose appears on the
existing family page. Opening a work family or a city folio reveals its larger
landscape illustration. Council stories and full
reports place their scene below the title, spanning the reading column.

The original scene files remain unchanged. A generated alpha-mask image gives
landscape frames a restrained irregular paper edge without blurring the artwork.
The owner rejected the experimental widened images as too yellow and less
schematic. Those generated variants are not shipped or referenced. Standalone
originals retain their complete 3:2 composition, so roofs and figures are not
clipped to force a shallow frame in detailed views. Catalogue images and atlas
excerpts use a wider 2:1 frame. The owner accepts catalogue cropping for this
layout review, with a future artwork pass if needed.
The active navigation marker meets the top edge of the green band, with no
padding or border separating them.
Native scrolling reserves space for the fixed bottom menu as well as the header.
The latest review also rejects the oversized, blog-like heading scale and section
gaps. Page titles now range from 23.2px to 28px, section titles are 20px and
subheadings 19px. Section and catalogue spacing is tighter; body text stays
17px and interactive controls retain 44px targets. The earlier thumbnail styles
and the unused compact illustration parameter are removed.

## What to retain and adapt

| Reference | Decision and reason |
| --- | --- |
| Literary headings and thin dividers | Keep the typeface and rules, with compact game-oriented sizes and spacing rather than the maquettes' oversized editorial hierarchy. |
| Three-destination bottom menu | Keep destinations, labels and icons. The latest review trials a deep mineral-green background, cream text and a light terracotta active state to distinguish it from the page. |
| Short landscape illustrations | Use 2:1 catalogue images above titles, with complete 3:2 standalone originals on detailed views and 2:1 atlas excerpts. No tiny side thumbnails or generated panoramic replacements. Existing atlas cells keep their proportions and cannot bleed into neighboring scenes. |
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

- Ruff lint and format checks passed; all 1,552 cases collected. The six city-summary variants have reviewed replacement IDs for the text-only contract.
- 536 affected presentation, map, work, alert and illustration cases passed on
  disposable PostgreSQL 17, with no skipped cases.
- The final illustrated catalogue passed 91 focused presentation/work cases;
  49 catalogue and work cases were rerun after the final caption changes.
- The complete French/English game browser journey passed, including 320px and
  390px layouts, 125%/200% text, keyboard access, native no-JavaScript forms,
  batch preparation/sealing/cancellation and expedition/report flows.
- The recruitment journey passed in both languages: guest play/account saving,
  operator management, three invitation seats, waiting-room entry, identity
  handoffs and the no-JavaScript fallback.
- Desktop and mobile screenshots were inspected. The 320px header initially
  exceeded its height budget; reducing the title's flex basis fixed it without
  truncation or hiding resource labels.
- The tighter layout exposed a native anchor landing behind the bottom menu;
  reserving bottom scroll padding fixed it, including the no-JavaScript journey.

These are local Presentation checks, not a claim that the entire simulation
suite ran locally. CI still owns the full PostgreSQL 17/18 checkpoint. GitHub's
CI-status API returned Forbidden in this environment; Railway deployment has
not been verified here.
