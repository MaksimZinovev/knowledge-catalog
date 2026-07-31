from __future__ import annotations

import fnmatch
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from reference_agent.bundle.document import (
    OKFDocument,
    OKFDocumentError,
    is_stale,
    normalize_verified,
    trust_tier,
)

_INDEX_NAME = "index.md"
_QUESTION_H2_RE = re.compile(r"^##\s+(.+\?)\s*$", re.MULTILINE)
_LINK_RE = re.compile(r"\]\(([^)\s]+\.md)(?:#[A-Za-z0-9_\-]*)?\)")
_TYPE_PALETTE = {
    "BigQuery Dataset": "#8b5cf6",
    "BigQuery Table": "#3b82f6",
    "Reference": "#10b981",
}
_DEFAULT_NODE_COLOR = "#94a3b8"


@dataclass
class Concept:
    id: str
    type: str
    title: str
    description: str
    resource: str
    tags: list[str]
    body: str
    status: str = "stable"
    generated: dict[str, Any] = field(default_factory=dict)
    verified: list[dict[str, Any]] = field(default_factory=list)
    stale_after: str = ""
    sources: list[dict[str, Any]] = field(default_factory=list)
    trust_tier: str = "unverified"
    stale: bool = False
    links_to: list[str] = field(default_factory=list)

    def to_node(self) -> dict[str, Any]:
        color = _TYPE_PALETTE.get(self.type, _DEFAULT_NODE_COLOR)
        return {
            "data": {
                "id": self.id,
                "label": self.title or self.id,
                "type": self.type,
                "description": self.description,
                "resource": self.resource,
                "tags": self.tags,
                "status": self.status,
                "generated": self.generated,
                "verified": self.verified,
                "stale_after": self.stale_after,
                "sources": self.sources,
                "trust_tier": self.trust_tier,
                "stale": self.stale,
                "color": color,
                "size": 30 + min(60, len(self.body) // 200),
            }
        }


def _extract_links(body: str, doc_dir: Path, bundle_root: Path) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    bundle_root_resolved = bundle_root.resolve()
    for m in _LINK_RE.finditer(body):
        target = m.group(1)
        if "://" in target or target.startswith("/"):
            continue
        try:
            resolved = (doc_dir / target).resolve().relative_to(bundle_root_resolved)
        except ValueError:
            continue
        rel = resolved.as_posix()
        rel = rel.removesuffix(".md")
        if rel and rel not in seen:
            seen.add(rel)
            out.append(rel)
    return out


_SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".next",
    "dist",
    "build",
    "out",
}

_CONFIG_NAME = "viz.config.json"


def _load_config(root: Path) -> dict[str, Any]:
    """Load viz.config.json from the bundle root. Returns {} if absent."""
    config_path = root / _CONFIG_NAME
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _load_ignore_patterns(root: Path) -> list[str]:
    """Load ignore patterns from .gitignore in the bundle root."""
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return []
    patterns = []
    for line in gitignore.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("!"):
            patterns.append(line)
    return patterns


def _is_ignored(rel_path: str, patterns: list[str]) -> bool:
    """Check if a relative path matches any gitignore pattern."""
    parts = rel_path.split("/")
    name = parts[-1]
    for pattern in patterns:
        p = pattern.rstrip("/")
        if not p:
            continue
        p = p.removeprefix("**/")
        if p in parts[:-1]:
            return True
        if rel_path.startswith(p + "/"):
            return True
        if fnmatch.fnmatch(name, p) or fnmatch.fnmatch(name, pattern):
            return True
    return False


def _walk_concepts(bundle_root: Path) -> tuple[list[Concept], list[dict[str, Any]]]:
    config = _load_config(bundle_root)
    use_gitignore = config.get("useGitignore", True)
    extra_excludes = config.get("exclude", [])
    ignore_patterns = _load_ignore_patterns(bundle_root) if use_gitignore else []
    ignore_patterns += extra_excludes
    concepts: list[Concept] = []
    questions: list[dict[str, Any]] = []
    for md_path in sorted(bundle_root.rglob("*.md")):
        rel = md_path.relative_to(bundle_root).as_posix()
        if any(p in _SKIP_DIRS for p in md_path.parts):
            continue
        if _is_ignored(rel, ignore_patterns):
            continue
        if md_path.name == _INDEX_NAME:
            continue
        rel = md_path.relative_to(bundle_root).with_suffix("")
        concept_id = "/".join(rel.parts)
        try:
            doc = OKFDocument.parse(md_path.read_text(encoding="utf-8"))
        except OKFDocumentError:
            continue
        fm = doc.frontmatter or {}
        tags = fm.get("tags") or []
        if not isinstance(tags, list):
            tags = [str(tags)]
        generated = fm.get("generated") if isinstance(fm.get("generated"), dict) else {}
        sources = fm.get("sources")
        if isinstance(sources, dict):
            sources = [sources]
        elif not isinstance(sources, list):
            sources = []
        questions.extend(_extract_questions(fm, doc.body or "", concept_id))
        concept = Concept(
            id=concept_id,
            type=str(fm.get("type") or "Unknown"),
            title=str(fm.get("title") or concept_id),
            description=str(fm.get("description") or ""),
            resource=str(fm.get("resource") or ""),
            tags=[str(t) for t in tags],
            body=doc.body or "",
            status=str(fm.get("status") or "stable"),
            generated=generated or {},
            verified=normalize_verified(fm),
            stale_after=str(fm.get("stale_after") or ""),
            sources=[s for s in sources if isinstance(s, dict)],
            trust_tier=trust_tier(fm),
            stale=is_stale(fm),
            links_to=_extract_links(doc.body or "", md_path.parent, bundle_root),
        )
        concepts.append(concept)
    return concepts, questions


def _extract_questions(
    fm: dict[str, Any], body: str, concept_id: str
) -> list[dict[str, Any]]:
    """Rule 1: frontmatter `questions:` (string + object forms).
    Rule 2: `?` H2 headings -> source "inferred"."""
    out: list[dict[str, Any]] = []
    fm_questions = fm.get("questions")
    if isinstance(fm_questions, list):
        for entry in fm_questions:
            if isinstance(entry, str):
                out.append(_make_question(entry, "explicit", concept_id))
            elif isinstance(entry, dict) and entry.get("q"):
                if entry.get("generated"):
                    source = "generated"
                elif entry.get("todo"):
                    source = "stub"
                else:
                    source = "explicit"
                out.append(_make_question(str(entry["q"]), source, concept_id))
    for m in _QUESTION_H2_RE.finditer(body):
        out.append(_make_question(m.group(1).strip(), "inferred", concept_id))
    return out


def _make_question(text: str, source: str, concept_id: str) -> dict[str, Any]:
    return {"text": text, "source": source, "answeredBy": [concept_id]}


def _build_graph(
    concepts: list[Concept], questions: list[dict[str, Any]]
) -> dict[str, Any]:
    concept_ids = {c.id for c in concepts}
    question_nodes: list[dict[str, Any]] = []
    question_edges: list[dict[str, Any]] = []
    for i, q in enumerate(
        [q for q in questions if any(a in concept_ids for a in q["answeredBy"])]
    ):
        qid = f"q:{q['answeredBy'][0]}:{i}"
        question_nodes.append(
            {
                "data": {
                    "id": qid,
                    "label": q["text"],
                    "kind": "question",
                    "source": q["source"],
                    "answeredBy": q["answeredBy"],
                }
            }
        )
        for answered_by in q["answeredBy"]:
            if answered_by in concept_ids:
                question_edges.append(
                    {
                        "data": {
                            "id": f"{answered_by}__{qid}",
                            "source": answered_by,
                            "target": qid,
                        }
                    }
                )
    ids = concept_ids
    nodes = [c.to_node() for c in concepts]
    edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str]] = set()
    for c in concepts:
        for target in c.links_to:
            if target == c.id or target not in ids:
                continue
            key = (c.id, target)
            if key in seen_edges:
                continue
            seen_edges.add(key)
            edges.append(
                {
                    "data": {
                        "id": f"{c.id}__{target}",
                        "source": c.id,
                        "target": target,
                    }
                }
            )
    bodies = {c.id: c.body for c in concepts}
    types = sorted({c.type for c in concepts})
    return {
        "nodes": nodes,
        "edges": edges,
        "bodies": bodies,
        "types": types,
        "palette": _TYPE_PALETTE,
        "questions": {"nodes": question_nodes, "edges": question_edges},
    }


def _load_template() -> str:
    template_path = Path(__file__).parent / "templates" / "viz.html"
    return template_path.read_text(encoding="utf-8")


def _load_asset(name: str) -> str:
    asset_path = Path(__file__).parent / "static" / name
    return asset_path.read_text(encoding="utf-8")


def generate_visualization(
    bundle_root: Path,
    out_path: Path,
    *,
    bundle_name: str | None = None,
) -> dict[str, int]:
    """Walk a bundle and write a single self-contained HTML visualization.

    Returns counts: {'concepts': N, 'edges': M, 'bytes': K}.
    """
    bundle_root = Path(bundle_root)
    out_path = Path(out_path)
    if not bundle_root.is_dir():
        raise FileNotFoundError(f"Bundle directory not found: {bundle_root}")

    concepts, questions = _walk_concepts(bundle_root)
    graph = _build_graph(concepts, questions)
    template = _load_template()
    css = _load_asset("viz.css")
    js = _load_asset("viz.js")
    name = bundle_name or bundle_root.resolve().name

    html = (
        template.replace("/*__VIZ_CSS__*/", css)
        .replace("/*__VIZ_JS__*/", js)
        .replace("__BUNDLE_NAME__", json.dumps(name))
        .replace(
            "__BUNDLE_DATA__", json.dumps(graph, default=str).replace("</", "<\\/")
        )
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    return {
        "concepts": len(concepts),
        "edges": len(graph["edges"]),
        "questions": len(graph["questions"]["nodes"]),
        "bytes": len(html.encode("utf-8")),
    }
