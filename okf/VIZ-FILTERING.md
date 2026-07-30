# Visualizer Bundle Filtering

## Problem

`visualize` walked **every** `.md` in the bundle root with `rglob("*.md")`, so:

1. **Broken HTML** — docs containing `<script>` (HTML examples in markdown bodies) truncated the embedded `window.BUNDLE` JSON at the first `</script>` → `Uncaught SyntaxError`, blank graph.
2. **Noise pollution** — `node_modules/**/*.md` shipped hundreds of extraneous README/CHANGELOG nodes (445 concepts instead of 17 real ones).
3. **No control** — only a hardcoded skip set; no way to honor the project's own `.gitignore`.

## Fix

- JSON embedded into `<script>` escapes `</` → `<\/` (HTML-parser-safe, always on).
- Hardcoded `_SKIP_DIRS` for universal noise: `.git`, `node_modules`, `__pycache__`, `.venv`, `venv`, `.next`, `dist`, `build`, `out`.
- Optional `viz.config.json` in the bundle root layers **your** rules on top:

```json
{
  "useGitignore": true,       // honor the bundle's .gitignore (default true)
  "exclude": ["drafts/", "tmp/**"]   // extra patterns, same matching as gitignore
}
```

Directory patterns (`foo/`) match any path prefix; glob patterns (`*.pyc`) match filenames; `**/name` matches at any depth.

## Usage (end-to-end, Windows)

```bash
# clone + venv
git clone https://github.com/GoogleCloudPlatform/knowledge-catalog
cd knowledge-catalog/okf
py -3.13 -m venv .venv && .venv\Scripts\activate
pip install -e .

# point at any OKF-ish bundle
python -m reference_agent visualize --bundle C:\path\to\bundle --name "My Wiki"
# → <bundle>\viz.html  ("Wrote 17 concept(s), 18 edge(s)")
```

Open `viz.html` in a browser — verify nodes count matches your real content (no node_modules nodes).

## Examples

Filter only gitignored files:

```json
{ "useGitignore": true }
```

Keep everything except a drafts folder:

```json
{ "useGitignore": false, "exclude": ["drafts/"] }
```

No config file → gitignore honored, hardcoded skips only.
