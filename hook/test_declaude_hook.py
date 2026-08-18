"""Tests for the client hook (run: python3 -m pytest hook/ or uv run --with pytest pytest)."""

import io
import json
import os
import stat
import sys
import time

import pytest

import declaude_hook as dh

POSIX = hasattr(os, "getuid")


@pytest.fixture
def buffer_home(monkeypatch, tmp_path):
    """Point the hook's buffer directory under tmp_path and return it."""
    monkeypatch.setattr(dh.tempfile, "gettempdir", lambda: str(tmp_path))
    return tmp_path / ("declaude-" + dh._user_key())


def _chunk_file(buffer_home, index, key="s1-m1"):
    return buffer_home / f"{key}.{index}"


def _capturing_translate(seen, result="plain version"):
    def fake_translate(text, *, token="", base_url="", timeout=0):
        seen["text"] = text
        seen["timeout"] = timeout
        return result

    return fake_translate


def test_last_assistant_text_extracts_final_message(tmp_path):
    p = tmp_path / "t.jsonl"
    lines = [
        {"message": {"role": "user", "content": [{"type": "text", "text": "hi"}]}},
        {
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "Great question!"}],
            }
        },
        {
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "You're absolutely right!"}],
            }
        },
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
    monkeypatch.setenv("DECLAUDE_TOKEN", "x")
    monkeypatch.setattr(sys, "stdin", io.StringIO("><"))
    assert dh.main() == 0


def test_plugin_invocation_is_inert_for_legacy_token_users(monkeypatch, capsys):
    """An automatic plugin update must not activate a second paid hook for users
    who still have the old manual registration."""
    monkeypatch.setenv("DECLAUDE_TOKEN", "x")
    monkeypatch.delenv("CLAUDE_PLUGIN_OPTION_HOOK_ENABLED", raising=False)
    monkeypatch.setattr(sys, "argv", ["declaude_hook.py", "--plugin"])
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(json.dumps(_md_payload("x" * 80, index=0, final=True))),
    )
    monkeypatch.setattr(
        dh,
        "handle_message_display",
        lambda *args: pytest.fail("plugin hook must stay inert before opt-in"),
    )

    assert dh.main() == 0
    assert capsys.readouterr().out == ""


def test_plugin_invocation_runs_by_default(monkeypatch):
    """A fresh install rewrites replies without any configuration step."""
    monkeypatch.delenv("DECLAUDE_TOKEN", raising=False)
    monkeypatch.delenv("CLAUDE_PLUGIN_OPTION_HOOK_ENABLED", raising=False)
    monkeypatch.setenv("CLAUDE_PLUGIN_OPTION_API_KEY", "x")
    monkeypatch.setattr(sys, "argv", ["declaude_hook.py", "--plugin"])
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(json.dumps(_md_payload("x" * 80, index=0, final=True))),
    )
    seen = {}

    def handle(payload, token):
        seen["token"] = token
        return 0

    monkeypatch.setattr(dh, "handle_message_display", handle)

    assert dh.main() == 0
    assert seen["token"] == "x"


@pytest.mark.parametrize("value", ["false", "False", "0", "no", "off", " false "])
def test_plugin_invocation_stops_on_explicit_false(monkeypatch, capsys, value):
    monkeypatch.delenv("DECLAUDE_TOKEN", raising=False)
    monkeypatch.setenv("CLAUDE_PLUGIN_OPTION_HOOK_ENABLED", value)
    monkeypatch.setenv("CLAUDE_PLUGIN_OPTION_API_KEY", "x")
    monkeypatch.setattr(sys, "argv", ["declaude_hook.py", "--plugin"])
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(json.dumps(_md_payload("x" * 80, index=0, final=True))),
    )
    monkeypatch.setattr(
        dh,
        "handle_message_display",
        lambda *args: pytest.fail("an explicit false must keep the hook inert"),
    )

    assert dh.main() == 0
    assert capsys.readouterr().out == ""


def test_plugin_invocation_runs_after_explicit_opt_in(monkeypatch):
    monkeypatch.delenv("DECLAUDE_TOKEN", raising=False)
    monkeypatch.setenv("CLAUDE_PLUGIN_OPTION_HOOK_ENABLED", "true")
    monkeypatch.setenv("CLAUDE_PLUGIN_OPTION_API_KEY", "x")
    monkeypatch.setattr(sys, "argv", ["declaude_hook.py", "--plugin"])
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(json.dumps(_md_payload("x" * 80, index=0, final=True))),
    )
    seen = {}

    def handle(payload, token):
        seen["payload"] = payload
        seen["token"] = token
        return 0

    monkeypatch.setattr(dh, "handle_message_display", handle)

    assert dh.main() == 0
    assert seen["token"] == "x"
    assert seen["payload"]["hook_event_name"] == "MessageDisplay"


def test_manual_invocation_keeps_working_without_plugin_opt_in(monkeypatch):
    monkeypatch.setenv("DECLAUDE_TOKEN", "x")
    monkeypatch.delenv("CLAUDE_PLUGIN_OPTION_HOOK_ENABLED", raising=False)
    monkeypatch.setattr(sys, "argv", ["declaude_hook.py"])
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(json.dumps(_md_payload("x" * 80, index=0, final=True))),
    )
    seen = {}

    def handle(payload, token):
        seen["payload"] = payload
        seen["token"] = token
        return 0

    monkeypatch.setattr(dh, "handle_message_display", handle)

    assert dh.main() == 0
    assert seen["token"] == "x"
    assert seen["payload"]["hook_event_name"] == "MessageDisplay"


def _md_payload(delta, *, index, final, message_id="m1", session_id="s1"):
    return {
        "hook_event_name": "MessageDisplay",
        "session_id": session_id,
        "message_id": message_id,
        "index": index,
        "final": final,
        "delta": delta,
    }


def test_message_display_buffers_intermediate_chunks_silently(buffer_home, capsys):
    assert (
        dh.handle_message_display(
            _md_payload("first chunk ", index=0, final=False), "tok"
        )
        == 0
    )
    assert capsys.readouterr().out == ""
    assert _chunk_file(buffer_home, 0).read_text(encoding="utf-8") == "first chunk "


def test_message_display_translates_full_message_on_final(
    buffer_home, capsys, monkeypatch
):
    seen = {}

    def fake_translate(text, *, token, base_url, timeout):
        seen["text"] = text
        return "plain version"

    monkeypatch.setattr(dh, "translate", fake_translate)
    long_a = "a" * 30 + " "
    long_b = "b" * 30
    dh.handle_message_display(_md_payload(long_a, index=0, final=False), "tok")
    assert (
        dh.handle_message_display(_md_payload(long_b, index=1, final=True), "tok") == 0
    )
    assert seen["text"] == long_a + long_b
    out = json.loads(capsys.readouterr().out)
    dc = out["hookSpecificOutput"]["displayContent"]
    assert out["hookSpecificOutput"]["hookEventName"] == "MessageDisplay"
    assert dc.startswith(long_b)  # final chunk's own text is preserved
    assert "plain version" in dc
    assert dh.LABEL in dc  # the rendition carries its own marker
    assert not _chunk_file(buffer_home, 0).exists()  # buffer cleaned up


def test_message_display_assembles_chunks_in_index_order(
    buffer_home, capsys, monkeypatch
):
    """Chunk invocations run concurrently; arrival order must not matter."""
    seen = {}
    monkeypatch.setattr(dh, "translate", _capturing_translate(seen))
    dh.handle_message_display(_md_payload("BBB " * 10, index=1, final=False), "tok")
    dh.handle_message_display(_md_payload("AAA " * 10, index=0, final=False), "tok")
    dh.handle_message_display(_md_payload("CCC " * 10, index=2, final=True), "tok")
    assert seen["text"] == "AAA " * 10 + "BBB " * 10 + "CCC " * 10
    assert json.loads(capsys.readouterr().out)


def test_message_display_fails_open_when_a_chunk_never_arrives(
    buffer_home, capsys, monkeypatch
):
    """Final fires immediately; if an earlier chunk never lands, emit nothing."""
    monkeypatch.setattr(dh, "CHUNK_WAIT_SECONDS", 0.1)
    monkeypatch.setattr(
        dh, "translate", lambda *a, **k: pytest.fail("must not translate")
    )
    dh.handle_message_display(_md_payload("x" * 50, index=0, final=False), "tok")
    # index 1 is missing; final claims index 2
    assert (
        dh.handle_message_display(_md_payload("y" * 50, index=2, final=True), "tok")
        == 0
    )
    assert capsys.readouterr().out == ""
    assert not _chunk_file(buffer_home, 0).exists()  # still cleaned up


def test_message_display_waits_for_in_flight_chunk(buffer_home, capsys, monkeypatch):
    """A chunk landing during the final invocation's wait window is picked up."""
    monkeypatch.setattr(dh, "translate", lambda text, **k: "plain version")
    wrote = {}
    real_sleep = time.sleep

    def sleep_and_deliver(seconds):
        if not wrote:
            wrote["done"] = True
            dh.handle_message_display(
                _md_payload("late " * 10, index=0, final=False), "tok"
            )
        real_sleep(seconds)

    monkeypatch.setattr(dh.time, "sleep", sleep_and_deliver)
    assert (
        dh.handle_message_display(_md_payload("end " * 15, index=1, final=True), "tok")
        == 0
    )
    assert "plain version" in capsys.readouterr().out


def test_message_display_rejects_drifted_payload(buffer_home, capsys):
    """The event is undocumented; a missing/renamed field must not collapse
    every message onto one shared buffer key."""
    for bad in (
        {"message_id": None},
        {"session_id": None},
        {"index": None},
        {"index": "3"},
        {"index": -1},
        {"index": True},
        {"delta": 123},
        {"delta": ["chunks"]},
    ):
        payload = _md_payload("x" * 50, index=0, final=True)
        payload.update(bad)
        assert dh.handle_message_display(payload, "tok") == 0
    assert capsys.readouterr().out == ""
    assert not buffer_home.exists() or not any(buffer_home.iterdir())


def test_message_display_sweeps_stale_buffers(buffer_home, capsys, monkeypatch):
    """Interrupted streams never see final=true; their files must not pile up."""
    monkeypatch.setattr(dh, "translate", lambda text, **k: "plain version")
    dh.handle_message_display(
        _md_payload("orphan", index=0, final=False, message_id="dead"), "tok"
    )
    orphan = _chunk_file(buffer_home, 0, key="s1-dead")
    old = time.time() - dh.STALE_AFTER_SECONDS - 60
    os.utime(orphan, (old, old))
    dh.handle_message_display(_md_payload("z" * 50, index=0, final=True), "tok")
    assert not orphan.exists()


def test_message_display_short_message_is_skipped(buffer_home, capsys, monkeypatch):
    monkeypatch.setattr(
        dh, "translate", lambda *a, **k: pytest.fail("must not translate")
    )
    assert (
        dh.handle_message_display(_md_payload("short", index=0, final=True), "tok") == 0
    )
    assert capsys.readouterr().out == ""


def test_message_display_fails_open_when_service_down(buffer_home, capsys, monkeypatch):
    def boom(*a, **k):
        raise OSError("connection refused")

    monkeypatch.setattr(dh, "translate", boom)
    assert (
        dh.handle_message_display(_md_payload("x" * 80, index=0, final=True), "tok")
        == 0
    )
    assert capsys.readouterr().out == ""


def test_message_display_handles_non_ascii_chunks(buffer_home, capsys, monkeypatch):
    """Explicit utf-8 on buffer files: emoji/CJK must round-trip and never
    raise past the fail-open handler, whatever the locale encoding is."""
    seen = {}
    monkeypatch.setattr(dh, "translate", _capturing_translate(seen))
    dh.handle_message_display(
        _md_payload("絶対に正しいです🎉 " * 5, index=0, final=False), "tok"
    )
    assert (
        dh.handle_message_display(_md_payload("→ done ✅", index=1, final=True), "tok")
        == 0
    )
    assert seen["text"] == "絶対に正しいです🎉 " * 5 + "→ done ✅"


@pytest.mark.skipif(not POSIX, reason="POSIX permission bits")
def test_buffer_dir_and_chunks_are_private(buffer_home):
    dh.handle_message_display(_md_payload("secret " * 10, index=0, final=False), "tok")
    assert stat.S_IMODE(os.stat(buffer_home).st_mode) == 0o700
    assert stat.S_IMODE(os.stat(_chunk_file(buffer_home, 0)).st_mode) == 0o600


@pytest.mark.skipif(not POSIX, reason="POSIX ownership check")
def test_buffer_dir_refuses_foreign_directory(buffer_home, capsys, monkeypatch):
    """A pre-planted dir we don't own (tmp-race squatter) means don't buffer."""
    buffer_home.mkdir(mode=0o700)
    real_lstat = os.lstat

    class FakeStat:
        def __init__(self, st):
            self.st_mode = st.st_mode
            self.st_uid = st.st_uid + 1
            self.st_mtime = st.st_mtime

    monkeypatch.setattr(
        dh.os,
        "lstat",
        lambda p: FakeStat(real_lstat(p)) if p == str(buffer_home) else real_lstat(p),
    )
    assert (
        dh.handle_message_display(_md_payload("x" * 50, index=0, final=False), "tok")
        == 0
    )
    assert capsys.readouterr().out == ""
    assert not any(buffer_home.iterdir())


@pytest.mark.skipif(not POSIX, reason="POSIX permission bits")
def test_buffer_dir_tightens_loose_permissions(buffer_home):
    """A pre-existing dir with broader perms is chmodded back to 0700."""
    buffer_home.mkdir(mode=0o775)
    dh.handle_message_display(_md_payload("x" * 50, index=0, final=False), "tok")
    assert stat.S_IMODE(os.stat(buffer_home).st_mode) == 0o700
    assert _chunk_file(buffer_home, 0).exists()


def _stop_payload(tmp_path, text):
    p = tmp_path / "t.jsonl"
    p.write_text(
        json.dumps(
            {
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": text}],
                }
            }
        )
    )
    return {"hook_event_name": "Stop", "transcript_path": str(p)}


def test_stop_translates_with_long_timeout(tmp_path, capsys, monkeypatch):
    """Stop is off the display path and must keep the 120 s budget for a cold
    GPU, not the MessageDisplay path's 25 s."""
    seen = {}

    def fake_translate(text, *, token, base_url, timeout):
        seen["timeout"] = timeout
        return "plain version"

    monkeypatch.setattr(dh, "translate", fake_translate)
    assert dh.handle_stop(_stop_payload(tmp_path, "x" * 80), "tok") == 0
    assert seen["timeout"] == 120
    message = json.loads(capsys.readouterr().out)["systemMessage"]
    assert "plain version" in message
    assert message.startswith(dh.LABEL)


def test_stop_drops_identical_rewrite(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(dh, "translate", lambda text, **k: text)
    assert dh.handle_stop(_stop_payload(tmp_path, "x" * 80), "tok") == 0
    assert capsys.readouterr().out == ""


def test_empty_translation_is_dropped(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(dh, "translate", lambda text, **k: "   ")
    assert dh.handle_stop(_stop_payload(tmp_path, "x" * 80), "tok") == 0
    assert capsys.readouterr().out == ""
