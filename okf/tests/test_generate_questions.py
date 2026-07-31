from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from reference_agent.cli import (
    _merge_questions,
    _normalize_question,
    _purge_generated,
    main,
)


def _note(tmp_path: Path, fm: str, body: str = "A note.\n") -> Path:
    p = tmp_path / "note.md"
    p.write_text(f"---\n{fm}\n---\n{body}", encoding="utf-8")
    return p


def test_normalize_question_collapses_punctuation_and_case():
    assert _normalize_question("Why does Chat  fail?") == "why does chat fail"
    assert _normalize_question("why-does chat fail") == "why does chat fail"


def test_merge_dedupes_against_manual_entries():
    fm = {"questions": ["Why does the chat fail?"]}
    added = _merge_questions(
        fm, ["why does THE chat fail", "What do retries mean?"], "deepseek-v4-flash"
    )
    assert added == 1  # near-duplicate of the manual entry dropped
    assert fm["questions"][0] == "Why does the chat fail?"  # manual untouched
    assert fm["questions"][1] == {
        "q": "What do retries mean?",
        "generated": {"by": "cloud:deepseek-v4-flash"},
    }


def test_purge_generated_strips_only_generated(tmp_path: Path):
    fm = {
        "questions": [
            "Manual stays.",
            {"q": "Generated goes.", "generated": {"by": "cloud:x"}},
        ]
    }
    assert _purge_generated(fm) == 1
    assert fm["questions"] == ["Manual stays."]


def test_purge_generated_removes_empty_key():
    fm = {"questions": [{"q": "Only gen.", "generated": {"by": "cloud:x"}}]}
    assert _purge_generated(fm) == 1
    assert "questions" not in fm


def test_provider_opt_out_exits_zero_and_writes_nothing(tmp_path: Path, monkeypatch):
    note = _note(tmp_path, "type: Reference\ntitle: T\n")
    before = note.read_bytes()
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    rc = main(["generate-questions", "--file", str(note)])
    assert rc == 0
    assert note.read_bytes() == before  # zero byte changes


def test_provider_opt_out_required_fails(tmp_path: Path, monkeypatch):
    import pytest

    note = _note(tmp_path, "type: Reference\ntitle: T\n")
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        main(["generate-questions", "--file", str(note), "--require"])


def test_serialized_round_trip_keeps_other_frontmatter_fields(tmp_path: Path):
    from reference_agent.bundle.document import OKFDocument

    fm_block = dedent(
        """\
        type: Reference
        title: My note
        tags: [a, b]
        verified:
          - {by: 'human:x', at: '2026-01-01T00:00:00+00:00'}
        """
    )
    doc = OKFDocument.parse(f"---\n{fm_block}---\nBody.\n")
    _merge_questions(doc.frontmatter, ["What is this?"], "deepseek-v4-flash")
    round_tripped = OKFDocument.parse(doc.serialize())
    assert round_tripped.frontmatter["type"] == "Reference"
    assert round_tripped.frontmatter["tags"] == ["a", "b"]
    assert round_tripped.frontmatter["verified"][0]["by"] == "human:x"
    qs = round_tripped.frontmatter["questions"]
    assert isinstance(qs, list) and qs[0]["q"] == "What is this?"
    assert qs[0]["generated"]["by"] == "cloud:deepseek-v4-flash"
