# Idea 5 (medium redesign, tail sampling) — "Questions board": edges from frontmatter questions, not just links (p < 0.10)

Scan frontmatter for a `questions:` list (or synthesize: any H2 ending in `?`) and render a second, toggleable layer where nodes are *questions* and edges mean "this concept answers this question." Two interchangeable graph views of the same bundle: Concepts / Questions (`Ctrl+2` swaps).

Why it's tail-of-distribution: most wiki viewers treat content as documents and links; treating *interrogatives* as first-class graph entities is deliberately weird. But it breaks knowledge into small digestible units (a question is the smallest unit) and gives search-first people something better to search: "what don't I understand yet" instead of "what files exist."
