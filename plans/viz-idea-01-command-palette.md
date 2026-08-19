# Idea 1 (quick win) — Command-palette search (keyboard-first)

Replace the header search input with a `Ctrl+K` / `/` command palette: fuzzy search over all node labels, ranked results with type chips and tags, arrow keys to navigate, Enter to focus the node on the graph *and* load it in the detail pane, Esc to dismiss. One extra small JS module, no library needed.

Rationale: directly matches "search-first, keyboard" preference; removes the two awkward interactions today (clicking tiny graph nodes, typing blind into a filter box).
