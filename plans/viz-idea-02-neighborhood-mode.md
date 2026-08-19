# Idea 2 (medium redesign) — Progressive disclosure graph ("neighborhood mode")

Instead of rendering the full graph and trusting zoom, default the view to a focused neighborhood: show one node (from search) plus its direct neighbors, with depth controls (`[ / ]` keys or `1/2` to expand/collapse hop distance) and a small breadcrumb trail of your path. Buttons: "expand this node" on click. The full-graph view stays available as an explicit toggle (`Ctrl+G`).

Rationale: visual learners don't benefit from a hairball — they benefit from small, legible subgraphs. Matches "breaking information into smaller digestible parts."
