from __future__ import annotations

import argparse
import logging
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from reference_agent.agent import DEFAULT_MODEL
from reference_agent.bundle.document import OKFDocument, OKFDocumentError
from reference_agent.bundle.paths import parse_concept_id
from reference_agent.runner import ReferenceRunner
from reference_agent.sources.bigquery import BigQuerySource

_SOURCES = ("bq",)
GQ_DEFAULT_MODEL = "deepseek-v4-flash"  # alternatives: nemotron-3-nano, gpt-oss
_OLLAMA_CLOUD_HOST = "https://ollama.com"


def _build_source(name: str, args: argparse.Namespace):
    if name == "bq":
        if not args.dataset:
            raise SystemExit("--dataset is required for --source bq")
        return BigQuerySource(
            dataset=args.dataset, billing_project=args.billing_project
        )
    raise SystemExit(f"Unknown source: {name}")


def _parse_seed_file(path: Path) -> list[str]:
    urls: list[str] = []
    text = path.read_text(encoding="utf-8")
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            urls.append(line)
    return urls


def _collect_seeds(args: argparse.Namespace) -> list[str]:
    if args.no_web:
        return []
    seeds: list[str] = []
    if args.web_seed:
        seeds.extend(args.web_seed)
    if args.web_seed_file:
        for p in args.web_seed_file:
            seeds.extend(_parse_seed_file(Path(p)))
    return _dedup_preserve_order(seeds)


def _dedup_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="reference-agent")
    sub = p.add_subparsers(dest="command", required=True)

    enrich = sub.add_parser(
        "enrich", help="Enrich concepts from a source into an OKF bundle."
    )
    enrich.add_argument("--source", choices=_SOURCES, required=True)
    enrich.add_argument(
        "--dataset",
        help="Source-specific identifier (for --source bq: 'project.dataset').",
    )
    enrich.add_argument(
        "--billing-project",
        help="Google Cloud project to bill for queries; "
        "defaults to ADC default.",
    )
    enrich.add_argument(
        "--out", required=True, type=Path, help="Bundle root directory."
    )
    enrich.add_argument(
        "--concept",
        action="append",
        default=None,
        help="Enrich only this concept id (e.g. 'tables/events_'). "
        "Repeatable.",
    )
    enrich.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Gemini model id (default: {DEFAULT_MODEL}).",
    )
    enrich.add_argument(
        "--web-seed",
        action="append",
        default=None,
        help="Seed URL for the web pass. Repeatable.",
    )
    enrich.add_argument(
        "--web-seed-file",
        action="append",
        default=None,
        help="Path to a file with one seed URL per line (# comments allowed). "
        "Repeatable.",
    )
    enrich.add_argument(
        "--web-max-pages",
        type=int,
        default=100,
        help="Hard cap on pages the web agent may fetch in one run (default 100).",
    )
    enrich.add_argument(
        "--web-allowed-host",
        action="append",
        default=None,
        help="Extra hostname the web agent may fetch beyond seed hostnames. "
        "Repeatable. Default: only seed hosts.",
    )
    enrich.add_argument(
        "--web-allowed-path-prefix",
        action="append",
        default=None,
        help="Only fetch URLs whose path starts with one of these prefixes "
        "(e.g. '/docs/'). Repeatable. Default: no path restriction.",
    )
    enrich.add_argument(
        "--web-denied-path-substring",
        action="append",
        default=None,
        help="Reject URLs whose path contains any of these substrings "
        "(e.g. '/login', '/pricing'). Repeatable.",
    )
    enrich.add_argument(
        "--web-max-depth",
        type=int,
        default=2,
        help="Hard cap on hop distance from any seed URL (default 2). "
        "Seeds are depth 0; their outbound links are depth 1; etc.",
    )
    enrich.add_argument(
        "--no-web",
        action="store_true",
        help="Skip the web pass entirely.",
    )
    enrich.add_argument("-v", "--verbose", action="store_true")

    viz = sub.add_parser(
        "visualize",
        help="Generate a self-contained HTML graph view of an OKF bundle.",
    )
    viz.add_argument(
        "--bundle", required=True, type=Path,
        help="Path to the bundle root directory.",
    )
    viz.add_argument(
        "--out", type=Path, default=None,
        help="Output HTML path (default: <bundle>/viz.html).",
    )
    viz.add_argument(
        "--name", default=None,
        help="Display name for the bundle (default: bundle directory name).",
    )

    gq = sub.add_parser(
        "generate-questions",
        help="Suggest questions a note answers (Ollama Cloud) and write them "
        "into the note's frontmatter `questions:` block.",
    )
    gq.add_argument("--bundle", type=Path, default=Path("."), help="Bundle root (for git discovery).")
    gq.add_argument("--file", type=Path, default=None, help="Target a single markdown file.")
    gq.add_argument("--since", default=None, help="Git ref: target .md files changed since this ref.")
    gq.add_argument("--model", default=GQ_DEFAULT_MODEL)
    gq.add_argument("--confirm", action="store_true", help="Ask y/n before each write.")
    gq.add_argument("--require", action="store_true", help="Hard-fail when provider unavailable (CI).")
    gq.add_argument("--purge-generated", action="store_true", help="Strip all generated entries from targets.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )
    if getattr(args, "verbose", False):
        logging.getLogger("reference_agent").setLevel(logging.DEBUG)
    # Quiet chatty third-party loggers regardless of mode.
    for noisy in ("google", "google_genai", "google_adk", "urllib3", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    if args.command == "visualize":
        from reference_agent.viewer import generate_visualization
        out = args.out or (args.bundle / "viz.html")
        stats = generate_visualization(args.bundle, out, bundle_name=args.name)
        print(
            f"Wrote {stats['concepts']} concept(s), "
            f"{stats['edges']} edge(s), "
            f"{stats['questions']} question(s), "
            f"{stats['bytes']} bytes → {out}",
            file=sys.stderr,
        )
        return 0

    if args.command == "generate-questions":
        return _generate_questions(args)

    if args.command == "enrich":
        source = _build_source(args.source, args)
        seeds = _collect_seeds(args)
        allowed_hosts: set[str] | None = None
        if seeds:
            allowed_hosts = {urlparse(s).netloc for s in seeds if urlparse(s).netloc}
            if args.web_allowed_host:
                allowed_hosts |= set(args.web_allowed_host)
        runner = ReferenceRunner(
            source=source,
            bundle_root=args.out,
            model=args.model,
            web_seeds=seeds or None,
            web_max_pages=args.web_max_pages,
            web_allowed_hosts=allowed_hosts,
            web_allowed_path_prefixes=args.web_allowed_path_prefix,
            web_denied_path_substrings=args.web_denied_path_substring,
            web_max_depth=args.web_max_depth,
            verbose=args.verbose,
        )
        only = (
            [parse_concept_id(c) for c in args.concept] if args.concept else None
        )
        n = runner.enrich_all(only=only)
        web_note = f"; web pass used {len(seeds)} seed(s)" if seeds else "; web pass skipped"
        print(f"Enriched {n} concept(s) into {args.out}{web_note}", file=sys.stderr)
        return 0
    return 1


def _normalize_question(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _gq_target_files(args: argparse.Namespace) -> list[Path]:
    if args.file:
        return [args.file]
    bundle = args.bundle.resolve()
    if args.since:
        out = subprocess.run(
            ["git", "diff", "--name-only", args.since, "--", "*.md"],
            cwd=bundle, capture_output=True, text=True,
        ).stdout
        return [bundle / line for line in out.splitlines() if line.strip()]
    out = subprocess.run(
        ["git", "status", "--porcelain", "--", "*.md"],
        cwd=bundle, capture_output=True, text=True,
    ).stdout
    files = []
    for line in out.splitlines():
        path = line[3:].strip().split(" -> ")[-1].strip('"')
        if path:
            files.append(bundle / path)
    return files


def _merge_questions(fm: dict, new_texts: list[str], model: str) -> int:
    """Merge new generated questions into fm['questions'], deduping against
    manual (authoritative) text. Mutates fm. Returns count added."""
    questions = fm.get("questions")
    if not isinstance(questions, list):
        questions = []
    seen = {
        _normalize_question(e if isinstance(e, str) else str(e.get("q", "")))
        for e in questions
    }
    added = 0
    for text in new_texts:
        norm = _normalize_question(text)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        questions.append({"q": text, "generated": {"by": f"cloud:{model}"}})
        added += 1
    if questions:
        fm["questions"] = questions
    return added


def _purge_generated(fm: dict) -> int:
    questions = fm.get("questions")
    if not isinstance(questions, list):
        return 0
    kept = [e for e in questions if not (isinstance(e, dict) and e.get("generated"))]
    removed = len(questions) - len(kept)
    if kept:
        fm["questions"] = kept
    else:
        fm.pop("questions", None)
    return removed


def _generate_questions(args: argparse.Namespace) -> int:
    files = [p for p in _gq_target_files(args) if p.suffix == ".md" and p.exists()]
    if not files:
        print("generate-questions: no target markdown files", file=sys.stderr)
        return 0

    docs: list[tuple[Path, OKFDocument]] = []
    for path in files:
        try:
            docs.append((path, OKFDocument.parse(path.read_text(encoding="utf-8"))))
        except (OKFDocumentError, OSError) as e:
            print(f"generate-questions: skipping {path} ({e})", file=sys.stderr)

    if args.purge_generated:
        for path, doc in docs:
            if _purge_generated(doc.frontmatter):
                path.write_text(doc.serialize(), encoding="utf-8")
                print(f"generate-questions: purged generated in {path}", file=sys.stderr)
        return 0

    import os
    if not os.environ.get("OLLAMA_API_KEY"):
        msg = "generate-questions: OLLAMA_API_KEY unset; provider unavailable (opt-out)"
        if args.require:
            raise SystemExit(msg)
        print(msg, file=sys.stderr)
        return 0

    from ollama import Client
    client = Client(
        host=_OLLAMA_CLOUD_HOST,
        headers={"Authorization": f"Bearer {os.environ['OLLAMA_API_KEY']}"},
    )
    try:
        client.chat(
            model=args.model,
            messages=[{"role": "user", "content": "ping"}],
            options={"num_predict": 1},
        )
    except Exception as e:
        msg = f"generate-questions: provider unavailable ({e})"
        if args.require:
            raise SystemExit(msg) from e
        print(msg, file=sys.stderr)
        return 0

    total = 0
    for path, doc in docs:
        if not doc.frontmatter.get("generate_questions", True):
            continue
        existing = doc.frontmatter.get("questions") or []
        lines = [
            e if isinstance(e, str) else str(e.get("q", ""))
            for e in existing if isinstance(e, (str, dict))
        ]
        prompt = (
            "Suggest up to 3 questions this document directly answers, phrased as "
            "a reader would ask. Only add NON-duplicates of the existing questions "
            "listed. Reply with a JSON array of strings only.\n\n"
            f"Existing questions: {lines}\n\nDocument:\n{doc.body[:8000]}"
        )
        try:
            resp = client.chat(
                model=args.model, messages=[{"role": "user", "content": prompt}]
            )
            import json as _json
            candidates = _json.loads(
                resp.message.content.strip().removeprefix("```json").removesuffix("```").strip()
            )
            if not isinstance(candidates, list):
                continue
        except Exception as e:
            print(f"generate-questions: failed for {path} ({e})", file=sys.stderr)
            continue
        new_texts = [str(x) for x in candidates]
        if args.confirm:
            new_texts = [t for t in new_texts if input(f"Add to {path}? {t!r} [y/N] ").lower() == "y"]
        added = _merge_questions(doc.frontmatter, new_texts, args.model)
        if added:
            path.write_text(doc.serialize(), encoding="utf-8")
            total += added
            print(f"generate-questions: +{added} question(s) in {path}", file=sys.stderr)
    print(f"generate-questions: wrote {total} question(s) across {len(docs)} file(s)", file=sys.stderr)
    return 0
