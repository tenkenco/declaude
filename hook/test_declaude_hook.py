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


def _md_payload(delta, *, final, message_id="m1"):
    return {
        "hook_event_name": "MessageDisplay",
        "session_id": "s1",
        "message_id": message_id,
        "final": final,
        "delta": delta,
    }


def test_message_display_buffers_intermediate_chunks_silently(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(dh.tempfile, "gettempdir", lambda: str(tmp_path))
    assert dh.handle_message_display(_md_payload("first chunk ", final=False), "tok") == 0
    assert capsys.readouterr().out == ""
    assert (tmp_path / "declaude-md-s1-m1").read_text() == "first chunk "


def test_message_display_translates_full_message_on_final(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(dh.tempfile, "gettempdir", lambda: str(tmp_path))
    seen = {}

    def fake_translate(text, *, token, base_url, timeout):
        seen["text"] = text
        return "plain version"

    monkeypatch.setattr(dh, "translate", fake_translate)
    long_a = "a" * 30 + " "
    long_b = "b" * 30
    dh.handle_message_display(_md_payload(long_a, final=False), "tok")
    assert dh.handle_message_display(_md_payload(long_b, final=True), "tok") == 0
    assert seen["text"] == long_a + long_b
    out = json.loads(capsys.readouterr().out)
    dc = out["hookSpecificOutput"]["displayContent"]
    assert out["hookSpecificOutput"]["hookEventName"] == "MessageDisplay"
    assert dc.startswith(long_b)  # final chunk's own text is preserved
    assert "plain version" in dc
    assert not (tmp_path / "declaude-md-s1-m1").exists()  # buffer cleaned up


def test_message_display_short_message_is_skipped(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(dh.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(dh, "translate", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not call")))
    assert dh.handle_message_display(_md_payload("short", final=True), "tok") == 0
    assert capsys.readouterr().out == ""


def test_message_display_fails_open_when_service_down(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(dh.tempfile, "gettempdir", lambda: str(tmp_path))

    def boom(*a, **k):
        raise OSError("connection refused")

    monkeypatch.setattr(dh, "translate", boom)
    assert dh.handle_message_display(_md_payload("x" * 80, final=True), "tok") == 0
    assert capsys.readouterr().out == ""
