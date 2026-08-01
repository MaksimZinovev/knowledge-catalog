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


def test_purge_generated_strips_only_generated():
    fm = {
        "questions": [
            "Manual stays.",
            {"q": "Generated goes.", "generated": {"by": "cloud:x"}},
        ]
    }
    kept = _purge_generated(fm)
    assert kept == ["Manual stays."]
    assert fm["questions"] == ["Manual stays."]


def test_purge_generated_removes_empty_key():
    fm = {"questions": [{"q": "Only gen.", "generated": {"by": "cloud:x"}}]}
    kept = _purge_generated(fm)
    assert kept == []
    assert fm["questions"] == []


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


def test_replace_questions_block_is_minimal_diff(tmp_path: Path):
    from reference_agent.cli import _replace_questions_block

    original = dedent(
        """\
        ---
        description: Keep this exact formatting.
        tags:
          - pi
          - ollama
        title: My note
        type: note
        ---
        # Body

        Some text.
        """
    )
    entries = [{"q": "What breaks?", "generated": {"by": "cloud:x"}}]
    out = _replace_questions_block(original, entries)
    # Everything before and after the inserted block is byte-identical
    assert out.startswith(original.rstrip().rsplit("---", 1)[0])
    body = out.split("questions:", 1)
    assert body[0] == original.split("type: note", 1)[0] + "type: note\n"
    assert out.rstrip().endswith("Some text.")
    assert "\nquestions:\n" in out


def test_replace_questions_block_replaces_and_removes():
    from reference_agent.cli import _replace_questions_block

    with_q = dedent(
        """\
        ---
        title: T
        questions:
          - Old one?
          - {q: Gen, generated: {by: cloud:x}}
        type: note
        ---
        Body.
        """
    )
    new = [{"q": "New?", "generated": {"by": "cloud:y"}}]
    out = _replace_questions_block(with_q, new)
    assert "Old one?" not in out and "New?" in out
    assert "type: note\n---\nBody." in out
    removed = _replace_questions_block(with_q, None)
    assert "questions:" not in removed
    assert "type: note\n---\nBody." in removed


def test_skip_already_generated_file_without_force(tmp_path: Path, monkeypatch, capsys):
    import json as _json

    note = _note(
        tmp_path,
        "type: Reference\ntitle: T\nquestions:\n"
        '  - {q: "Old?", generated: {by: cloud:x}}\n',
    )
    before = note.read_bytes()
    monkeypatch.setenv("OLLAMA_API_KEY", "x")

    class FakeMsg:
        content = _json.dumps(["New question?"])

    class FakeClient:
        def __init__(self, **kw):
            pass

        def chat(self, **kw):
            m = type("M", (), {})()
            m.message = FakeMsg()
            return m

    monkeypatch.setattr("ollama.Client", FakeClient)
    rc = main(["generate-questions", "--file", str(note)])
    assert rc == 0
    assert note.read_bytes() == before  # skipped: second run is a no-op


def test_no_frontmatter_file_skipped_not_crashed(tmp_path: Path, monkeypatch, capsys):
    """Issue #1: a .md with no --- block should be skipped, not crash the batch."""
    p = tmp_path / "plain.md"
    p.write_bytes(b"# Just a note\nNo frontmatter here.\n")
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    rc = main(["generate-questions", "--file", str(p), "--purge-generated"])
    assert rc == 0
    assert p.read_bytes() == b"# Just a note\nNo frontmatter here.\n"
    assert "no frontmatter" in capsys.readouterr().err.lower()


def test_force_regenerates_and_byte_diff_is_minimal(tmp_path: Path, monkeypatch):
    import json as _json

    note = _note(
        tmp_path,
        """type: Reference
tags:
  - pi
  - ollama
title: T
questions:
  - {q: "Old?", generated: {by: cloud:x}}
""",
        body="# Body\n\nText.\n",
    )
    before = note.read_text(encoding="utf-8")
    monkeypatch.setenv("OLLAMA_API_KEY", "x")

    class FakeMsg:
        content = _json.dumps(["A fresh question?"])

    class FakeClient:
        def __init__(self, **kw):
            pass

        def chat(self, **kw):
            m = type("M", (), {})()
            m.message = FakeMsg()
            return m

    monkeypatch.setattr("ollama.Client", FakeClient)
    rc = main(["generate-questions", "--file", str(note), "--force"])
    assert rc == 0
    after = note.read_text(encoding="utf-8")
    assert "A fresh question?" in after and "Old?" in after
    # Byte-diff minimal: only the questions: block lines changed
    assert after.split("questions:", 1)[0] == before.split("questions:", 1)[0]
    assert after.rstrip().endswith(before.rstrip().rsplit("---", 1)[1].rstrip())
