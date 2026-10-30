# Material and illustration assets

The October 30 narrative artwork follows the owner's naive drawings; see
[the art direction](../../../../docs/illustrations.md) for palette and provenance.
The forge remains unchanged. Report and city illustrations preserve complete
3:2 atlas scenes; the supplied agriculture, granary, fortifications and siege
drawings retain their native 3:1 frames. Army preparation also uses a complete
3:1 panorama. Catalogue tiles and local work rows use
square crops. Atlas cells remain isolated. Owned-city overviews show their existing complete cityscape below the
compact controls, without decorative heading thumbnails. Construction-start news reuses one generic work scene.
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

`map/settlements.svg`: self-contained 1536×1024 atlas, six 512×512 cells,
embedding the owner's October 30 JPEGs byte-for-byte. Top row: open settlement
(`1000063148`), timber palisade (`1000063158`), reinforced palace (`1000063154`).
Bottom row: stone walls (`1000063156`), legacy earth wall (`1000063152`), legacy
great enclosure (`1000063150`). The SVG preserves image proportions, aligns the
city bases, and masks the black JPEG backdrop at display time with an sRGB alpha
filter; it leaves RGB colors unchanged. Each embedded source has a SHA-256 in
the SVG comment for provenance. There are no scripts or external resources.
Live flags retain ownership colors; the previous saturation adjustment is removed
so the drawings retain their supplied colors. Public wall-level mappings remain
unchanged, including older saved games.
The drawings use a compact 74-unit square within each marker (previously 84),
with a light ink-colored drop shadow inside the cached atlas for contrast.
Names, flags and hit areas retain their existing sizes.

`map/yaara-background.jpg` is an unchanged copy of the owner's reworked
`1000063159.jpg`, displayed in full beneath the existing territory, road and city
layers. The earlier photograph (`1000063138.jpg`) is not used. Its coast and
terrain are decorative and do not change movement rules. Three presentation
positions move to clear the northern coastline/river and southern mountain chain;
saved positions, territory polygons and road connections are preserved.

The map frame now preserves its native 680:500 ratio; action sheets cover it rather than squeezing its geography. No source artwork is repainted.

