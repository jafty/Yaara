# Material and illustration assets

Original narrative images and sprite atlases are unchanged. Report illustrations
span the reading column; standalone scenes keep their complete 3:2 composition
and narrative atlas excerpts use centered 2:1 frames. Building details use modest
3:2 rectangles, while catalogue tiles and local work rows use square crops. Atlas
cells remain isolated and all source art keeps its native proportions. The owner
accepts cropping in lists. City summaries have no decorative heading thumbnails.
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

The map frame now preserves its native 680:500 ratio; action sheets cover it rather than squeezing its geography. No source artwork is repainted.
