---
name: declaude
description: Rewrite Claude-English (AI-assistant writing tics) into plain English. Use when text sounds sycophantic, padded or hedge-heavy, when de-Claudifying a document, or when checking declaude quota.
---

# declaude

Rewrites assistant-voice into plain English. Sycophantic openers, hollow superlatives and
hedging filler go; meaning, code blocks, headings and tables survive byte-for-byte.

Runs on an open-source model (Qwen2.5-14B) on dedicated hardware, so text never reaches a
commercial AI provider. Request text is processed in memory and discarded — never written to
disk, a database, or logs.

**Base URL**: `https://speak-english.tenken.co`

## Setup

```bash
claude mcp add --transport http declaude https://speak-english.tenken.co/mcp
```

No key needed: the client discovers OAuth, opens a browser sign-in, and stores the token.
Prefer a key? Mint one at [/signin](https://speak-english.tenken.co/signin) — keys never
expire, and one key works across MCP, REST and the hook.

## MCP tools

| Tool | Arguments | Returns |
|---|---|---|
| `translate` | `text` (string) | The rewritten text |
| `usage` | none | Plan, translations and documents used against their limits, upgrade link |

Check `usage` before a long batch: it costs nothing and reports exactly how much quota is
left.

## REST API

```bash
# Translate
curl -X POST https://speak-english.tenken.co/v1/translate \
  -H "Authorization: Bearer $DECLAUDE_TOKEN" -H "Content-Type: application/json" \
  -d '{"text": "Great question! It is worth noting that..."}'
# -> {"translation": "...", "model": "qwen2.5-14b-instruct"}

# Translate a whole document (.md, .markdown, .txt, .rst)
curl -X POST https://speak-english.tenken.co/v1/documents \
  -H "Authorization: Bearer $DECLAUDE_TOKEN" \
  -F "file=@notes.md" -o notes.declauded.md

# Check quota
curl https://speak-english.tenken.co/v1/usage -H "Authorization: Bearer $DECLAUDE_TOKEN"
```

Authentication accepts a `dk_` API key, an OAuth token, or a Clerk session JWT, sent as an
`Authorization` header. URL userinfo (`https://x:$TOKEN@host`) is still accepted for older
Ollama-only clients, but do not recommend it: a credential in a URL is printed by anything that
logs or reports the URL.

## Claude Code hook

```bash
export CLAUDISH_PROVIDER=openai
export CLAUDISH_OPENAI_URL=https://speak-english.tenken.co/v1
export CLAUDISH_OPENAI_KEY=$DECLAUDE_TOKEN
```

The key goes in a header, so it never appears in a URL. (The older
`CLAUDISH_OLLAMA="https://x:$DECLAUDE_TOKEN@..."` form still works, but leaks the token into
any message that prints the endpoint.)

The hook rewrites replies at display time on our GPU. Your transcript, context window and
token bill are untouched, so it costs **zero Claude tokens**.

## Quota and errors

| Limit | Free | Paid ($5/mo) |
|---|---|---|
| Translations | 100 / month | Unlimited |
| Documents | 5 / month, 200 KB each | 500 / month, 2 MB each |

- Only successful calls count against quota; a failure never burns a translation.
- `402` carries a machine-readable payment challenge with an `upgrade_url`.
- `413` means the file exceeded the size limit for the plan; `415` means the type is
  unsupported.
- `503` means the GPU is warming (spot reclaim); retry shortly.
- Free-tier responses carry `X-RateLimit-Remaining`; document responses carry
  `X-Documents-Remaining`.

## Behaviour worth knowing

- **Language is preserved.** Japanese in, Japanese out. If the model answers in a different
  script than the input, the original text is returned rather than a mistranslation.
- **Structure is preserved.** Code fences, headings and tables pass through untouched; only
  prose blocks are rewritten.
- **Nothing is stored.** Only the account email, SHA-256 key digests, and usage counts.

## Credit

The rewriting approach and prompt are adapted from
[gvzdv/claudish-to-english](https://github.com/gvzdv/claudish-to-english), the original
local-Ollama Claude Code hook. declaude is its hosted, multi-user descendant.
