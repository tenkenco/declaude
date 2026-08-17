#!/usr/bin/env python3
"""Claude Code hook: rewrite the assistant's messages from Claude-English into
plain English via the hosted declaude service.

Two install modes, same script (it dispatches on hook_event_name):

MessageDisplay (recommended) - the plain rendition appears inline under each
reply as it is displayed, and nothing enters the model's context window:
  {"hooks": {"MessageDisplay": [{"hooks": [{"type": "command",
    "command": "python3 /path/to/declaude_hook.py", "timeout": 30}]}]}}

Stop (fallback for Claude Code versions without MessageDisplay) - the plain
rendition of the turn's final message is shown as a system message:
  {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "python3 /path/to/declaude_hook.py"}]}]}}

Env:
  DECLAUDE_TOKEN  - dk_ API key or session token (required)
  DECLAUDE_URL    - service base URL (default: production)
"""
from __future__ import annotations  # runs on end-user Pythons as old as 3.7

import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request

DEFAULT_URL = "https://speak-english.tenken.co"
MIN_CHARS = 40  # don't burn a translation on one-liners


def translate(text: str, *, token: str, base_url: str = DEFAULT_URL, timeout: int = 120) -> str:
    req = urllib.request.Request(
        f"{base_url}/v1/translate",
        data=json.dumps({"text": text}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)["translation"]


def last_assistant_text(transcript_path: str) -> str | None:
    """Pull the final assistant message text from a Claude Code transcript (JSONL)."""
    last = None
    try:
        with open(transcript_path) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = entry.get("message") or {}
                if msg.get("role") == "assistant":
                    parts = [c.get("text", "") for c in msg.get("content", []) if c.get("type") == "text"]
                    if any(parts):
                        last = "\n".join(p for p in parts if p)
    except OSError:
        return None
    return last


def _buffer_path(payload: dict) -> str:
    """Per-message chunk buffer. MessageDisplay fires once per streamed chunk,
    each in a fresh process, so the accumulating text has to live on disk."""
    key = "{}-{}".format(payload.get("session_id", ""), payload.get("message_id", ""))
    key = re.sub(r"[^A-Za-z0-9-]", "_", key)
    return os.path.join(tempfile.gettempdir(), "declaude-md-" + key)


def _translate_or_none(text: str, token: str) -> str | None:
    try:
        return translate(text, token=token, base_url=os.environ.get("DECLAUDE_URL", DEFAULT_URL), timeout=25)
    except urllib.error.HTTPError as e:
        if e.code == 402:
            print("declaude: free tier exhausted — upgrade via the payment link in the 402 response", file=sys.stderr)
        return None  # degrade gracefully: never break the user's session
    except Exception:
        return None


def handle_message_display(payload: dict, token: str) -> int:
    """Buffer chunks; on the final one, attach the plain rendition via displayContent.
    Emitting nothing leaves the original chunk displayed as-is (fail open)."""
    delta = payload.get("delta") or ""
    path = _buffer_path(payload)
    try:
        with open(path, "a") as f:
            f.write(delta)
        if not payload.get("final"):
            return 0
        with open(path) as f:
            text = f.read()
        os.unlink(path)
    except OSError:
        return 0
    if len(text) < MIN_CHARS:
        return 0
    plain = _translate_or_none(text, token)
    if plain is None or plain.strip() == text.strip():
        return 0
    out = f"{delta}\n\n[declaude] plain English:\n\n{plain}"
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "MessageDisplay", "displayContent": out}}))
    return 0


def handle_stop(payload: dict, token: str) -> int:
    text = last_assistant_text(payload.get("transcript_path", ""))
    if not text or len(text) < MIN_CHARS:
        return 0
    plain = _translate_or_none(text, token)
    if plain is None:
        return 0
    print(json.dumps({"systemMessage": f"[declaude] plain-English version:\n\n{plain}"}))
    return 0


def main() -> int:
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
