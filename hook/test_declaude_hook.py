"""Tests for the client hook (run: python3 -m pytest hook/ or uv run --with pytest pytest)."""
import json

import declaude_hook as dh


def test_last_assistant_text_extracts_final_message(tmp_path):
    p = tmp_path / "t.jsonl"
    lines = [
        {"message": {"role": "user", "content": [{"type": "text", "text": "hi"}]}},
        {"message": {"role": "assistant", "content": [{"type": "text", "text": "Great question!"}]}},
        {"message": {"role": "assistant", "content": [{"type": "text", "text": "You're absolutely right!"}]}},
    ]
    p.write_text("\n".join(json.dumps(x) for x in lines))
    assert dh.last_assistant_text(str(p)) == "You're absolutely right!"


def test_last_assistant_text_handles_garbage(tmp_path):
    p = tmp_path / "t.jsonl"
    p.write_text("not json\n{}\n")
    assert dh.last_assistant_text(str(p)) is None


def test_missing_file_returns_none():
    assert dh.last_assistant_text("/nonexistent/x.jsonl") is None


def test_main_without_token_is_noop(monkeypatch, capsys):
    monkeypatch.delenv("DECLAUDE_TOKEN", raising=False)
    assert dh.main() == 0
    assert capsys.readouterr().out == ""


def test_main_never_raises_on_bad_stdin(monkeypatch):
    import io
    import sys
    monkeypatch.setenv("DECLAUDE_TOKEN", "x")
    monkeypatch.setattr(sys, "stdin", io.StringIO("><"))
    assert dh.main() == 0
