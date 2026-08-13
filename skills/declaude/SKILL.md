---
name: declaude
description: Rewrite "Claude English" (sycophantic AI-assistant prose - "Great question!", "It's worth noting", hedging filler) into plain, natural English via the hosted declaude API. Use when the user asks to de-Claude, simplify, or humanize AI-generated text, wants text translated to plain English, or wants AI writing tics removed from prose, READMEs, docs, or messages.
---

# declaude — plain-English rewriting

Hosted service: `https://speak-english.tenken.co` (open-source Qwen2.5-14B on dedicated GPUs; text never reaches a commercial AI provider).

## Auth

Requires an API key in `DECLAUDE_TOKEN` (or a key file at `~/.declaude_key`).
Humans mint keys at https://speak-english.tenken.co/signin — shown once, never expires.

## Rewrite text

```bash
TOKEN="${DECLAUDE_TOKEN:-$(cat ~/.declaude_key 2>/dev/null)}"
curl -sS -X POST https://speak-english.tenken.co/v1/translate \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "$(jq -n --arg t "$TEXT" '{text:$t}')" | jq -r .translation
```

- Max input: 50,000 chars. Typical latency 1-3s.
- Preserves facts, code blocks, names, numbers; strips only style.

## Response codes to handle

- `402` — free tier (100/month) exhausted. Body has `upgrade_url`; tell the user to visit it. Do not retry.
- `503` — model warming (spot instance re-heal, ~10-15 min). Honor `Retry-After`; fine to tell the user to retry later.
- `401` — bad/missing key; point the user at /signin.

## MCP alternative

For persistent use inside an MCP client: `claude mcp add --transport http declaude https://speak-english.tenken.co/mcp` — no header needed; the client discovers OAuth and opens a browser sign-in. Exposes a `translate` tool.

## Credit

The rewriting approach and prompt are adapted from
[gvzdv/claudish-to-english](https://github.com/gvzdv/claudish-to-english), the original
local-Ollama Claude Code hook. declaude is its hosted, multi-user descendant.
