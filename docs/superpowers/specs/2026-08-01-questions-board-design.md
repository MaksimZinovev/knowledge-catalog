# Questions Board — Design Spec

**Date:** 2026-08-01
**Status:** Approved for implementation planning
**Repo:** knowledge-catalog/okf (viewer) + the consumed wiki bundle (pre-commit hook lives in the bundle repo)

## Overview

The OKF visualizer gains a second, interchangeable graph layer: the **Questions Board**. Where the Concepts view renders files and wikilinks, the Questions view renders natural-language *questions* as first-class nodes, with edges meaning "this note answers this question". Three independent extraction mechanisms feed a single frontmatter canonical form; no cloud or LLM cost is ever incurred inside the visualize/build path unless the user explicitly runs the generation CLI.

Design goals: zero mandatory authoring effort, single-`viz.html` output preserved, no new runtime JS dependencies, graceful degradation at every layer.

## Components

1. **Core viewer (idea 5)** — Questions graph layer with `Ctrl+1`/`Ctrl+2` swap
2. **D — question-generation CLI** — Ollama Cloud (cheap models), writes into frontmatter
3. **E — pre-commit stub hook** — inserts TODO stubs at commit time (bundle repo)
4. **F — git-history mining (phase 2)** — conventional-commit subjects → retroactive question nodes

## Architecture

Single source of truth: each markdown file's frontmatter `questions:` field. All generation mechanisms (D, E, F is read-only at build time, see below) ultimately respect this; the viewer's extraction rule #1 (frontmatter `questions:`) is the canonical path.

```
markdown files ──(visualize build)──► window.BUNDLE.questions[] ──► cytoscape Questions layer
      ▲
      │ writes (frontmatter only)
D: generate-questions CLI (Ollama Cloud)     E: pre-commit stub hook
F: git log mining ──(build time, read-only)──► BUNDLE.questions[]
```

The visualize build stays **fast and offline**: D is a separate command, F degrades to zero nodes when no `.git/` is present.

## 1. Core viewer (idea 5)

### Extraction (Python, build time — existing `reference_agent visualize` step)

Sources, in priority order:

1. **Frontmatter `questions:` list** — canonical. Entries are either plain strings (manual) or objects `{q: <text>, generated: {by: <model-id>}, todo: true}` (machine/stub forms, see D/E).
2. **Synthesized**: H2 headings (`## …?`) ending in `?` → `source: "inferred"`.

Each question gets: `id`, `text`, `source` (`explicit | inferred | stub | generated | git`), `answeredBy: [concept-id]` (always a list).

### Views

- Two datasets share one cytoscape instance, swapped — never overlaid.
- **Concepts** (current view, unchanged): `Ctrl+1`.
- **Questions**: `Ctrl+2` or a header two-state toggle. Question nodes: amber diamond. Edges `note → question` = "answers".
- Clicking a question opens the detail pane of its answering note(s), question text pinned at top.
- Toggle state persists in localStorage.

### Styles by source (visual honesty)

| source                   | style                                      |
| ------------------------ | ------------------------------------------ |
| explicit (manual string) | solid diamond                              |
| inferred (`?` H2)        | dashed border                              |
| generated (LLM)          | dashed border, small dot                   |
| stub (TODO from hook)    | thin outline                               |
| git (phase 2)            | solid, with provenance line in detail pane |

### Error handling

- Bundle with zero questions → toggle disabled, tooltip: "No questions found (add `questions:` to frontmatter or end an H2 with `?`)". Never a blank graph.
- `</` escaping (per VIZ-FILTERING.md) continues to protect `window.BUNDLE`.
- Build output line gains `K question(s)`.

## 2. D — `generate-questions` CLI (Ollama Cloud)

Separate command, NOT part of visualize: `python -m reference_agent generate-questions [--bundle <root>] [--file <md>] [--model <tag>] [--confirm] [--require] [--purge-generated]`

### Provider

- **Ollama Cloud as remote host**: `https://ollama.com/api/chat`, `Authorization: Bearer $OLLAMA_API_KEY`, using the official `ollama` Python package (single new, minimal dependency).
- **Cheap models**: default `deepseek-v4-flash`; documented alternatives `nemotron-3-nano`, `gpt-oss`. NOT minimax-m3 (expensive). Model overridable via `--model` and `viz.config.json`.
- Auth: `OLLAMA_API_KEY` env var (ollama.com/settings/keys).

### Behavior

- Default target set: md files with uncommitted changes or untracked (per `git status`) — git is the modification tracker, keeping with the file-as-cache principle. `--file` targets one file; `--since <ref>` targets files changed since a commit.
- Prompt: ≤3 questions the document directly answers, phrased as the reader would ask; receives the file's current `questions:` and is instructed to only ADD non-duplicates.
- **File-as-cache**: results are written into frontmatter as `{q, generated: {by: "cloud:<model>"}}` objects and committed. No separate cache file (git tracks modification state; history is the cache).
- **Merge with dedupe at write time**: plain-string (manual) entries are authoritative; near-duplicate generated entries (normalized text) are dropped. Manual + generated coexist.
- `--confirm`: interactive y/n/edit per candidate before writing.
- `--purge-generated`: strips all `generated:` entries (for a clean regeneration).
- Privacy: accepted "send everything"; per-file escape hatch `generate_questions: false` excludes a file.

### Provider-unavailable handling (hard rule)

Detection order: ① `OLLAMA_API_KEY` unset → ② 1-token probe fails (network/auth) → ③ model tag retired/absent from cloud library. In all cases: **warn one line, exit 0, touch zero bytes**. `--require` flips to hard-fail for CI.

## 3. E — pre-commit stub hook (bundle repo)

- On commit, for each staged `.md` lacking `questions:` (or with only stubs), the hook **auto-inserts TODO stubs** derived from H1 + H2s:
  `{q: "TODO: '<heading> — as a question?'", todo: true}`
- Prints a summary plus agent hint: `pi generate-questions --file <file> --confirm` (see D; `--confirm` gates writes on user approval).
- Runs frontmatter validation after every write (YAML parses; `questions:` is a list) — same guard used by D.
- **Unavailable cases**: Pi agent absent → stubs remain valid and harmless (render stub-styled); cloud unreachable at CLI time → D degradation, stubs untouched. `--no-verify` bypasses; non-interactive commits never block.

## 4. F — git-history mining (phase 2, read-only at build time)

- Scope: **conventional-commit prefixes only** (`note:`, `fix:`, `feat:`, `docs:`); Auto-saves/chores skipped.
- Commit subject → question node (e.g. `note: auto-updating progress card via pre-commit hook (reusable how-to)` → "How do I auto-update the progress card via a pre-commit hook?").
- **Multi-file commits**: one question node; `answeredBy` = ALL `.md` files in the commit (non-md ignored). Commits touching >5 md files are skipped (bulk-move guard).
- Multiple qualifying commits per file: each is its own node; dedupe by normalized text; cap 3 most recent per file.
- Renames: `git log --follow`; `answeredBy` uses current path; deleted files drop their questions on rebuild.
- Provenance: detail pane shows "first answered: <date>, <commit hash>".
- Requires `.git/` beside the bundle; absent → silently contributes zero nodes.

## Data contract

```yaml
questions:
  - Why does the Pi ACP chat fail until Ollama is running?          # manual
  - q: What do 'empty retries' mean?                                # generated
    generated: {by: "cloud:deepseek-v4-flash"}
  - q: "TODO: 'Entry fields — as a question?'"                      # stub (E hook)
    todo: true
```

BUNDLE entry:

```json
{ "id": "q:<file>:<n>", "text": "...", "source": "explicit|inferred|stub|generated|git",
  "answeredBy": ["<concept-id>"], "provenance": {"commit": "90f2710", "date": "..."} }
```

## Testing

- **Python unit tests**: extractor fixtures (frontmatter-only / H2-only / both / neither / malformed YAML / stub entries / generated entries); D dedupe logic; D unavailable-mode exits 0 with no writes; F multi-file answer mapping; F >5-file skip; F rename via --follow.
- **Hook tests**: stub insertion idempotency; frontmatter validation catches broken YAML; `--no-verify` path untouched.
- **Viewer manual checklist**: N explicit + M inferred + K stubs render with correct styles; Ctrl+1/2 round-trip; zero-question bundle → disabled toggle; question click → correct detail pane.

## Out of scope

- LLM question-answering/chat; unanswered-question tracking as a workflow; search logging ("People Also Ask" — deferred); cloud generation inside visualize build.