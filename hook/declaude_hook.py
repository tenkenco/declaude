#!/usr/bin/env python3
"""Claude Code Stop-hook: rewrite the assistant's final message from Claude-English
into plain English via the hosted declaude service.

Install (settings.json):
  {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "python3 /path/to/declaude_hook.py"}]}]}}

Env:
  DECLAUDE_TOKEN  - Clerk session token (required)
  DECLAUDE_URL    - service base URL (default: production)
"""
from __future__ import annotations  # runs on end-user Pythons as old as 3.7

import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_URL = "https://speak-english.tenken.co"


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


def main() -> int:
    token = os.environ.get("DECLAUDE_TOKEN")
    if not token:
        return 0  # not configured: never block the session
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    text = last_assistant_text(payload.get("transcript_path", ""))
    if not text or len(text) < 40:
        return 0
    try:
        plain = translate(text, token=token, base_url=os.environ.get("DECLAUDE_URL", DEFAULT_URL))
    except urllib.error.HTTPError as e:
        if e.code == 402:
            print("declaude: free tier exhausted — upgrade via the payment link in the 402 response", file=sys.stderr)
        return 0  # degrade gracefully: never break the user's session
    except Exception:
        return 0
    print(json.dumps({"systemMessage": f"[declaude] plain-English version:\n\n{plain}"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
