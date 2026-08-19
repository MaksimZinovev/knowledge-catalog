# Idea 6 (aspirational, tail sampling) — "Constellation, not graph": replace force layout with a meaning-encoding spatial layout (p < 0.10)

Force layouts are why wiki graphs become hairballs. Replace cytoscape physics with a deterministic *spatial* layout where position encodes meaning — x-axis = time (created/modified), y-axis = abstraction level (computed from fan-in: foundational concepts at the bottom, derived notes at top, computed as longest-path layering in the link DAG, cycles broken cleanly). Zooming out shows colored constellations by type/topic; zooming in shows text. A **timeline × dependency map** — closer to an xkcd chart or a star chart than a network graph. No physics, no wiggliness, fully reproducible (same bundle → same picture, screenshot-friendly).

Risk: layout quality depends on the link structure being DAG-ish; fallback is clustering cycles into super-nodes.
