# Material and illustration assets

Original narrative images and sprite atlases are unchanged. Landscape frames
span the reading column below report and selected-work titles. Standalone scenes
keep their complete 3:2 composition; atlas excerpts use a centered 2:1 frame,
with isolated cells and undistorted proportions.
Catalogue tiles use 2:1 crops above their headings as visual scanning cues;
the owner accepts cropping while reviewing this layout. There are no tiny
illustrations beside headings or in city summaries.
The experimental AI-widened granary, forge and fortifications were rejected for
yellow coloration and a less schematic rendering. They are not application assets.

`deckled-edge.png` is a generated alpha mask for restrained irregular paper edges.
It does not repaint or blur the scene. It is applied once to the shared frame;
unsupported CSS masking leaves the original rectangular frame. The original
successful generation is preserved at
`/workspace/generated_images/exec-d1766189-27cf-42ed-b8a0-9c7d6c11d260.png` in this
workspace. The first experimental white-frame output was rejected because its
center was transparent; it is not used by the interface.

The October 27 map assets below replace `map-terrain.png`. Reading text uses clean surfaces.
`papyrus.webp`, generated for the earlier October 24 material revision, now
supplies the subtle map texture. Mission choices use plain ink and native radios
instead of textured tiles. The header uses solid pale stone;
mineral green remains in controls and owned flags. Fallback surface
colors remain when images are disabled.


## Schematic map assets — October 27

`map/parchment.webp`: faint dune strokes and sparse muted-green palms across worn
ivory parchment, including central details. Decorative only, with no terrain rule.
Final imagegen source: `exec-ba2fdf82-6582-4472-b957-4b9e8fcbf244.png`.

`map/settlements.webp`: lossless RGBA 1536×1024 atlas, six 512×512 cells.
Top row: open settlement, timber palisade, reinforced palace.
Bottom row: stone walls, legacy earth wall, legacy great enclosure.
Schematic frontal manuscript vignettes, regenerated from the fortifications
illustration with fibrous papyrus texture and plain walls. Flags remain live SVG,
using existing house emblems and viewer-relative green/red colors. SVG square
viewports clip each cell without stretching it or showing adjacent cells.
The map background layers the existing papyrus texture over the decorative terrain.
