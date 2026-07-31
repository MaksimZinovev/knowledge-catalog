---
id: PLAN-001
type: plan
status: draft
owner: human
depends_on: [docs/superpowers/specs/2026-08-01-questions-board-design.md]
spec_checksum: 060d664a
last_validated: 2026-07-31T19:24:16+00:00
---

# Plan: Questions Board for OKF Visualizer

```spec
scope: document
type: plan
required_sections: [Context, Tools & Skills, Approach, Out of Scope, Steps, Files to Modify, Reuse, Evidence Pack, Verification, Bottom Line]
max_chars: 10000
banned_words: [TODO, TBD, placeholder]
placeholders: ["```df-todo", "[REPLACE]"]
match:
  has_checklist: '^- \[( |x)\]'
  has_source: 'Source:'
  has_file_marker: '(CREATED|UPDATED|DELETED)'
  has_test: '# Test \d'
  has_out_of_scope: '^## Out of Scope'
  has_tools_and_skills: '^## Tools & Skills'
  has_ynp_format: '^- .+: (Yes|No|Possibly)\b'
```

## Context

```spec
type: plan
max_chars: 10000
banned_words: [might be, could be, seems like, I think, possibly, perhaps]
match:
  has_problem: '(problem|issue|bug|break|fail|cannot|does.not|unable)'
```

The visualizer has one graph ("map of things"): files without authored questions cannot appear in any FAQ-style view, so the feature would fail on a mostly-frontmatter-less corpus. User feedback: metadata-derived indexes have "not much value", manual authoring "will accumulate and become expensive". Approved fix (spec): frontmatter as single source of truth; three feeders (Ollama Cloud CLI, pre-commit stub hook, git mining phase 2); viewer rule 1 unchanged. Source: docs/superpowers/specs/2026-08-01-questions-board-design.md; model picks deepseek-v4-flash / nemotron-3-nano / gpt-oss — "not minimax-3 (expensive)".

## Tools & Skills

```spec
type: plan
max_chars: 10000
banned_words: [N/A, n/a, grep sufficient, small codebase, simple enough, overkill for]
match:
  min_3_ynp: '^- .+: (Yes|No|Possibly)\b'
  has_gh: '\bgh\b.*\(CLI\).*: Yes\b'
  has_deepwiki: 'deepwiki.*\(MCP\).*: Yes\b'
```

Enumerated from `ls -1 ~/.pi/agent/skills/`, skill symlinks, MCP, and session CLIs (gh, git, graphjin, docfence):

- ponytail (Skills): Yes — enforced: shortest diff, reuse rungs, ponytail ceiling comments
- verification-before-completion (Skills): Yes — runnable check per non-trivial logic (extractor, dedupe, degraded mode)
- brainstorming (Skills): No — design phase completed, spec approved
- grilling (Skills): No — clarification rounds done; user phrasing recorded verbatim per docfence H3
- docfence (CLI): Yes — scaffold + validate this plan; stamp only with user permission
- gh (CLI): Yes — commit spec/plan and later PR flows on knowledge-catalog
- deepwiki (MCP): Yes — confirm cytoscape multi-element-set idioms before writing the view swap
- graphjin (CLI): Possibly — only if further star-mining for viewer idioms is requested

## Approach

```spec
type: plan
max_chars: 1400
banned_words: [TODO, TBD, placeholder]
match:
  has_preamble: 'The content of the plan is aligned with the following guiding questions.'
  has_alternative: '(alternative|instead of|rather than|compared to|over:|vs[.])'
  has_what_guiding_question: 'Q\d+\(what\)'
  has_how_guiding_question: 'Q\d+\(how\)'
  has_context_guiding_question: 'Q\d+\(context\).*key context'
  has_intent_guiding_question: 'Q\d+\(intent\).*key intent'
  has_out_of_scope_guiding_question: 'Q\d+\(out of scope\)'
  has_constraint_guiding_question: 'Q\d+\(key constraint\).*key constraint'
  has_evidence_guiding_question: 'Q\d+\(key evidence\).*key evidence'
  has_verification_guiding_question: 'Q\d+\(verification\).*key verification from user perspective'
```

The content of the plan is aligned with the following guiding questions.

Q1(what): what is the smallest vertical slice that proves the board? Core viewer + D CLI; hook (E) and mining (F) deferred but spec'd.
Q2(how): how do we avoid a new dependency stack? Official `ollama` python client instead of raw httpx (docs.ollama.com/cloud: Bearer auth at <https://ollama.com/api/chat>); frontmatter as the persistence layer rather than a sidecar JSON (user's counter-grill: "Is it overcomplicating?").
Q3(context): key context = single `viz.html` output and zero runtime JS deps (user constraint, verbatim).
Q4(intent): key intent = no forced authoring; "avoid or mitigate manual effort of adding questions" (user phrasing, kept verbatim per H3).
Q5(out of scope): should F mining overlap D's merge path? No — F is read-only at build time.
Q6(key constraint): key constraint = provider unavailable must exit 0 and touch zero bytes (user: "Handle the case when provider is not available (opt-out)").
Q7(key evidence): key evidence = real fixtures from the wiki repo (one note with a `?` H2, real commits 90f2710 etc.), not memory.
Q8(verification): key verification from user perspective = open viz.html, toggle Ctrl+1/2, see styled question nodes; run CLI with and without OLLAMA_API_KEY.

## Out of Scope

```spec
type: plan
max_chars: 10000
banned_words: [Nothing., None., N/A, n/a, Not applicable]
match:
  has_justification: '^- .+:'
  min_2_exclusions: '^- .+:'
```

- E hook + F mining implementation: spec'd and decided, phase 2 per user ("F marked phase 2 / optional"); ships after core+D lands
- Search logging / "People Also Ask" idea: user rejected the earlier iteration; deferred to a later session
- Cloud generation inside the visualize build: visualize must stay fast and offline
- Unanswered-question tracking workflow: deferred (idea-6 / ghost-mode territory)
- Hybrid single-layer graph (concepts + questions overlaid): swap model chosen instead, per design Q&A

## Steps

```spec
type: plan
max_chars: 10000
banned_words: [**Step, **Task, **Phase]
match:
  has_step_evidence: '^- \[ \].*\(Source'
  min_3_steps: '^- \[( |x)\]'
```

- [ ] Extract questions in `generator.py`: rule 1 frontmatter `questions:` (string + object forms), rule 2 `?` H2s with `source: "inferred"`; emit `BUNDLE.questions` with source metadata (Source: spec §1 Extraction; existing generator.py walk)
- [ ] Viewer swap in `viz.js`/`viz.html`: two element sets, header toggle + Ctrl+1/Ctrl+2, localStorage persistence, per-source node styles, disabled-toggle tooltip on empty bundle (Source: spec §1 Views/Styles; existing cytoscape single instance)
- [ ] Add `generate-questions` CLI in `cli.py`: `ollama` Client(host="<https://ollama.com>") with `OLLAMA_API_KEY` bearer, default model `deepseek-v4-flash`, probe-then-warn-exit-0 degradation, merge+dedupe write into frontmatter, `--file`/`--since`/`--confirm`/`--purge-generated`/`--require` flags, `generate_questions: false` escape hatch (Source: spec §2; ollama cloud docs)
- [ ] Frontmatter safe-write helper: edit only the `questions:` block, YAML validation on every write (Source: spec §3 validation requirement; Evidence Pack key risk)
- [ ] Build output line: `Wrote N concept(s), M edge(s), K question(s)` (Source: spec §1 Error handling)
- [ ] Commit; docfence stamp only after explicit user approval (Source: docfence H11 iron law)

## Files to Modify

```spec
type: plan
max_chars: 10000
banned_words: [TODO, TBD, placeholder]
match:
  has_file_entry: '^- `[^`]+` — (CREATED|UPDATED|DELETED)'
```

- `okf/src/reference_agent/viewer/generator.py` — UPDATED
- `okf/src/reference_agent/viewer/static/viz.js` — UPDATED
- `okf/src/reference_agent/viewer/templates/viz.html` — UPDATED
- `okf/src/reference_agent/viewer/static/viz.css` — UPDATED
- `okf/src/reference_agent/cli.py` — UPDATED
- `okf/tests/test_viewer.py` — UPDATED — extractor + dedupe fixtures (assert-style)
- `okf/tests/test_generate_questions.py` — CREATED — CLI degraded-mode + write-path checks (ponytail: plain asserts; pytest not in repo deps)
- `okf/pyproject.toml` — UPDATED — add `ollama` (single new dependency)

## Reuse

```spec
type: plan
max_chars: 10000
banned_words: [None., N/A, Nothing to reuse, No reuse]
match:
  has_reuse_item: '^- .+:'
```

- generator.py walk: question extraction rides the existing filtered markdown walk (`_SKIP_DIRS`, gitignore, `</` escaping per VIZ-FILTERING.md)
- cytoscape instance + stylesheet machinery in viz.js: second dataset on the same instance; no second graph lib
- `ollama` python package: official client covers host/auth/stream flags; no httpx wrapper
- pyyaml (already in pyproject): frontmatter read/write; no new parser
- tests/test_viewer.py fixture style: new tests mirror existing structure
- wiki repo pre-commit hook precedent (git log 50d5cc9): phase-2 hook copies an already-proven pattern

## Evidence Pack

```spec
type: plan
max_chars: 10000
banned_words: [**Source**:, **Source:**]
match:
  has_evidence_claim: '^- Claim:'
  has_confidence: 'Confidence:'
```

- Claim: The only `?`-H2 hit in the wiki is `## Q — What do I edit to add a new cloud model?` in notes/add-ollama-cloud-model-to-pi-acp.md, so rule-2 inference yields 1 node today and rule-1 frontmatter is the load-bearing path
  Source: grep over C:\Users\maksi\repos\wiki (`^## .*\?$`) in this session
  Confidence: 0.95
  Implication: extractor tests must not assume large inferred counts; the frontmatter path is critical
- Claim: Ollama Cloud serves chat at <https://ollama.com/api/chat> with `Authorization: Bearer $OLLAMA_API_KEY` and `Client(host="https://ollama.com", headers=...)`
  Source: docs.ollama.com/cloud (fetched this session)
  Confidence: 1.0
  Implication: no custom HTTP wrapper; degraded-mode probe is one cheap chat call; model retirements happen (docs table), so the default tag must be overridable
- Claim: The wiki contains private notes (notes/payoneer-details.md) and the user accepted send-everything with a `generate_questions: false` escape hatch
  Source: interview answer D-PRIVACY plus user confirmation message
  Confidence: 1.0
  Implication: the escape hatch ships even though broad mode is the default
- Claim: Cheap model choices are deepseek-v4-flash / nemotron-3-nano / gpt-oss; minimax-m3 excluded as expensive
  Source: user message "D - cheap model would be deepseek-v4-flash, nemotron-3-nano, gpt-oss - not minimax-3 (expensive)"
  Confidence: 1.0
  Implication: default = deepseek-v4-flash; documented alternatives list exactly these three

### Gaps

- Per-source node styling (colors/icons) not user-reviewed; Test 3 screenshot review closes this
- Phase-2 hook target repo (wiki repo vs knowledge-catalog) — confirm at phase-2 start

## Verification

```spec
type: plan
max_chars: 10000
banned_words: [TODO, TBD, placeholder]
match:
  has_verify_command: '^```bash'
  has_expected: '# Expected:'
  min_2_tests: '# Test \d'
  has_state_space: '(empty|zero|partial|intermediate|boundary|edge case|failure)'
```

State space: zero questions (empty), exactly 1 inferred (minimum), mixed explicit+generated+stub (intermediate), dedupe collision (boundary), provider unavailable (failure), end-user toggle (full path).

```bash
# Test 1: zero-question bundle -> toggle disabled (empty state)
cd okf && python tests/test_viewer.py -k empty
# Expected: fixture bundle with no questions yields BUNDLE.questions length 0; build line shows "0 question(s)"; render skips toggle
```

```bash
# Test 2: inference minimum — one `?` H2 fixture -> exactly 1 inferred node
cd okf && python tests/test_viewer.py -k inferred
# Expected: fixture with a single "## ... ?" heading yields length 1, source "inferred"
```

```bash
# Test 3: mixed intermediate styles render (end user, full path)
python -m reference_agent visualize --bundle C:\Users\maksi\repos\wiki --name "Wiki"
# Expected: build prints K question(s) >= 1; viz.html Ctrl+2 shows styled diamonds; Ctrl+1 restores concepts unchanged
```

```bash
# Test 4: failure state — provider opt-out
OLLAMA_API_KEY= python -m reference_agent generate-questions --file notes/x.md; echo $?
# Expected: one warning line, exit code 0, zero byte changes to the file
```

```bash
# Test 5: boundary — dedupe collision between manual and generated text
cd okf && python tests/test_generate_questions.py
# Expected: manual plain-string survives; near-duplicate generated entry dropped; YAML validates (questions: is a list)
```

```bash
# Test 6: docfence plan integrity
docfence validate plans/2026-08-01-questions-board-plan.md
# Expected: passes; no unfilled blocks
```

## Bottom Line

```spec
type: plan
max_chars: 10000
banned_words: [TODO, TBD, placeholder]
match:
  has_recommendation: 'Recommendation:'
```

Per-step confidence: extractor 0.9, viewer swap 0.85 (cytoscape idiom check via deepwiki pending), CLI 0.9 (API confirmed from docs), frontmatter helper 0.8 (lowest outlier — formatting-preserving YAML edits are fiddly), build output 0.95, docfence flow 1.0. Average ~0.88. Key risk: pyyaml round-trip alters other frontmatter fields the publishing pipeline depends on — mitigated by editing only the `questions:` block plus a byte-diff fixture check. Gaps: node styling review, phase-2 hook repo choice. Recommendation: proceed with core viewer + D CLI now; E hook and F mining land as phase-2 follow-up after user verification of Test 3.
