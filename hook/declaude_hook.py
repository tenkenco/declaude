#!/usr/bin/env python3
"""Claude Code hook: rewrite the assistant's messages from Claude-English into
plain English via the hosted declaude service.

One script, two install modes; it dispatches on hook_event_name:

  MessageDisplay (recommended) - the plain rendition appears inline under each
  reply as it is displayed, and nothing enters the model's context window.

  Stop (fallback for Claude Code versions without MessageDisplay) - the plain
  rendition of the turn's final message is shown as a system message.

Install instructions live in hook/README.md (the single source; register only
ONE of the two events).

Env:
  CLAUDE_PLUGIN_OPTION_API_KEY - secure plugin-config key (plugin install)
  CLAUDE_PLUGIN_OPTION_HOOK_ENABLED - plugin opt-in (default: false)
  DECLAUDE_TOKEN - dk_ API key or session token (manual install / migration)
  DECLAUDE_URL   - service base URL (default: production)
"""

from __future__ import annotations  # runs on end-user Pythons as old as 3.7

import getpass
import json
import os
import re
import stat
import sys
import tempfile
import time
import urllib.error
import urllib.request

DEFAULT_URL = "https://speak-english.tenken.co"
# One label for both modes, so the rendition is easy to spot in a busy terminal.
LABEL = "🧼 declaude"
MIN_CHARS = 40  # don't burn a translation on one-liners

# Claude Code dispatches up to 3 chunk invocations concurrently and fires the
# final one immediately, so the final invocation may have to wait for earlier
# chunks that are still in flight.
CHUNK_WAIT_SECONDS = 3.0
# Interrupted streams (Esc, crash, hook timeout) never deliver final=true, so
# their chunk files would otherwise accumulate forever.
STALE_AFTER_SECONDS = 3600


class QuotaExhausted(str):
    """The account hit its monthly limit. Carries the notice to display.

    Quota exhaustion is the one failure worth showing. Every reply costs a
    translation now, so a silent stop reads as a broken plugin.
    """


def translate(
    text: str, *, token: str, base_url: str = DEFAULT_URL, timeout: int = 120
) -> str:
    req = urllib.request.Request(
        f"{base_url}/v1/translate",
        data=json.dumps({"text": text}).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)["translation"]


def last_assistant_text(transcript_path: str) -> str | None:
    """Pull the final assistant message text from a Claude Code transcript (JSONL)."""
    last = None
    try:
        with open(transcript_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = entry.get("message") or {}
                if msg.get("role") == "assistant":
                    parts = [
                        c.get("text", "")
                        for c in msg.get("content", [])
                        if c.get("type") == "text"
                    ]
                    if any(parts):
                        last = "\n".join(p for p in parts if p)
    except OSError:
        return None
    return last


def _user_key() -> str:
    try:
        return str(os.getuid())
    except AttributeError:  # Windows
        return re.sub(r"[^A-Za-z0-9-]", "_", getpass.getuser())


def _buffer_dir() -> str | None:
    """Private per-user directory for chunk buffers.

    The system temp dir is world-writable on multi-user hosts, so buffered
    assistant text must not sit there under a predictable world-readable name.
    The directory must be ours alone (0700, a real directory we own) or we
    refuse to buffer at all.
    """
    d = os.path.join(tempfile.gettempdir(), "declaude-" + _user_key())
    try:
        os.mkdir(d, 0o700)
    except FileExistsError:
        pass
    except OSError:
        return None
    try:
        st = os.lstat(d)
    except OSError:
        return None
    if not stat.S_ISDIR(st.st_mode):
        return None
    if hasattr(os, "getuid"):
        if st.st_uid != os.getuid():
            return None
        # A pre-existing dir may have been created looser (old version, umask);
        # 0700 is part of the contract, so tighten it or refuse to buffer.
        if stat.S_IMODE(st.st_mode) != 0o700:
            try:
                os.chmod(d, 0o700)
            except OSError:
                return None
    return d


def _sweep_stale(buffer_dir: str) -> None:
    cutoff = time.time() - STALE_AFTER_SECONDS
    try:
        names = os.listdir(buffer_dir)
    except OSError:
        return
    for name in names:
        path = os.path.join(buffer_dir, name)
        try:
            if os.lstat(path).st_mtime < cutoff:
                os.unlink(path)
        except OSError:
            pass


def _chunk_path(buffer_dir: str, key: str, index: int) -> str:
    return os.path.join(buffer_dir, f"{key}.{index}")


def _write_chunk(buffer_dir: str, key: str, index: int, delta: str) -> None:
    """Write one chunk to its own file, atomically.

    Write-then-rename means a chunk file only ever appears complete, so the
    final invocation can treat existence as done. O_EXCL on the scratch file
    refuses to follow a planted symlink; 0600 keeps the text private.
    """
    scratch = os.path.join(buffer_dir, f"{key}.{index}.part{os.getpid()}")
    fd = os.open(scratch, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(delta)
    os.replace(scratch, _chunk_path(buffer_dir, key, index))


def _collect_chunks(buffer_dir: str, key: str, final_index: int) -> str | None:
    """Assemble chunks 0..final_index-1 in index order, waiting briefly for
    invocations still in flight. None if any chunk never lands (fail open)."""
    want = list(range(final_index))
    deadline = time.monotonic() + CHUNK_WAIT_SECONDS
    while any(not os.path.exists(_chunk_path(buffer_dir, key, i)) for i in want):
        if time.monotonic() >= deadline:
            return None
        time.sleep(0.05)
    parts = []
    for i in want:
        with open(_chunk_path(buffer_dir, key, i), encoding="utf-8") as f:
            parts.append(f.read())
    return "".join(parts)


def _cleanup_chunks(buffer_dir: str, key: str, final_index: int) -> None:
    for i in range(final_index):
        try:
            os.unlink(_chunk_path(buffer_dir, key, i))
        except OSError:
            pass


def _quota_notice(error: urllib.error.HTTPError) -> str:
    """Build the one-line notice shown when the account hits its monthly limit."""
    notice = "monthly translation limit reached, so this reply was not rewritten."
    try:
        body = json.load(error)
    except Exception:  # noqa: BLE001 - the notice must not depend on the body
        return notice
    upgrade = body.get("upgrade_url") if isinstance(body, dict) else None
    if isinstance(upgrade, str):
        return notice + " Upgrade: " + upgrade
    return notice


def _plain_rendition(text: str, token: str, timeout: int) -> str | None:
    """Shared gate for both modes: skip short messages, translate, and drop
    renditions that add nothing. Any failure degrades gracefully to None, except
    an exhausted quota, which returns a QuotaExhausted notice to display."""
    if len(text) < MIN_CHARS:
        return None
    try:
        plain = translate(
            text,
            token=token,
            base_url=os.environ.get("DECLAUDE_URL", DEFAULT_URL),
            timeout=timeout,
        )
    except urllib.error.HTTPError as e:
        if e.code == 402:
            return QuotaExhausted(_quota_notice(e))
        return None  # degrade gracefully: never break the user's session
    except Exception:  # noqa: BLE001 - fail open: no failure may break the session
        return None
    if not plain.strip() or plain.strip() == text.strip():
        return None
    return plain


def handle_message_display(payload: dict, token: str) -> int:
    """Buffer chunks; on the final one, attach the plain rendition via
    displayContent. Emitting nothing leaves the original displayed (fail open).

    MessageDisplay is undocumented and its payload shape may drift between
    Claude Code versions, so anything unexpected means do nothing rather than
    guess."""
    delta = payload.get("delta")
    if delta is None:
        delta = ""
    session_id = payload.get("session_id")
    message_id = payload.get("message_id")
    index = payload.get("index")
    if (
        not isinstance(delta, str)
        or not session_id
        or not message_id
        or isinstance(index, bool)
        or not isinstance(index, int)
        or index < 0
    ):
        return 0
    key = re.sub(r"[^A-Za-z0-9-]", "_", f"{session_id}-{message_id}")
    buffer_dir = _buffer_dir()
    if buffer_dir is None:
        return 0
    try:
        if not payload.get("final"):
            _write_chunk(buffer_dir, key, index, delta)
            return 0
        _sweep_stale(buffer_dir)
        earlier = _collect_chunks(buffer_dir, key, index)
        _cleanup_chunks(buffer_dir, key, index)
    except (OSError, ValueError):
        return 0
    if earlier is None:
        return 0
    plain = _plain_rendition(earlier + delta, token, timeout=25)
    if plain is None:
        return 0
    if isinstance(plain, QuotaExhausted):
        out = f"{delta}\n\n{LABEL} {plain}"
    else:
        out = f"{delta}\n\n{LABEL} plain English:\n\n{plain}"
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "MessageDisplay",
                    "displayContent": out,
                }
            }
        )
    )
    return 0


def handle_stop(payload: dict, token: str) -> int:
    text = last_assistant_text(payload.get("transcript_path", ""))
    if not text:
        return 0
    # Stop is not on the display path, so it can afford to ride out a cold GPU.
    plain = _plain_rendition(text, token, timeout=120)
    if plain is None:
        return 0
    if isinstance(plain, QuotaExhausted):
        print(json.dumps({"systemMessage": f"{LABEL} {plain}"}))
        return 0
    print(json.dumps({"systemMessage": f"{LABEL} plain English:\n\n{plain}"}))
    return 0


def main() -> int:
    # The plugin rewrites replies by default, so a fresh install works at once.
    # An explicit false turns the hook off.
    #
    # Claude Code omits an unset option from the hook environment. It does not
    # export the declared default. Measured on 2026-08-18: with the default
    # declared true and no stored value, the variable arrived absent. So the
    # declared default alone can never turn this hook on, and the empty case
    # has to mean on. Do not restore the old "explicit true only" gate, because
    # that combination ships the feature dead.
    #
    # The second branch protects version 1.0 users. Their manual hook plus this
    # one would bill every reply twice. An unset option does arrive empty, so
    # the branch fires for them.
    #
    # Manual invocations do not carry --plugin and keep their existing behavior.
    plugin_invocation = "--plugin" in sys.argv[1:]
    if plugin_invocation:
        enabled = (
            os.environ.get("CLAUDE_PLUGIN_OPTION_HOOK_ENABLED", "").strip().lower()
        )
        if enabled in {"0", "false", "no", "off"}:
            return 0
        if not enabled and os.environ.get("DECLAUDE_TOKEN"):
            return 0
        token = os.environ.get("CLAUDE_PLUGIN_OPTION_API_KEY") or os.environ.get(
            "DECLAUDE_TOKEN"
        )
    else:
        token = os.environ.get("DECLAUDE_TOKEN")
    if not token:
        return 0  # not configured: never block the session
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if payload.get("hook_event_name") == "MessageDisplay":
        return handle_message_display(payload, token)
    return handle_stop(payload, token)


if __name__ == "__main__":
    sys.exit(main())
