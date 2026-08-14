<h1 align="center">declaude</h1>

<p align="center">
  <strong>Claude-English → plain English, as a service.</strong><br>
  Strips sycophantic openers, hollow superlatives and hedging filler.<br>
  Meaning, code and structure survive intact.
</p>

<p align="center">
  <a href="https://github.com/tenkenco/declaude/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/tenkenco/declaude/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/tenkenco/declaude/actions/workflows/security.yml"><img alt="Security" src="https://github.com/tenkenco/declaude/actions/workflows/security.yml/badge.svg"></a>
  <a href="https://github.com/tenkenco/declaude/actions/workflows/daily.yml"><img alt="Daily checks" src="https://github.com/tenkenco/declaude/actions/workflows/daily.yml/badge.svg"></a>
  <a href="https://codecov.io/gh/tenkenco/declaude"><img alt="Coverage" src="https://codecov.io/gh/tenkenco/declaude/branch/main/graph/badge.svg"></a>
</p>

<p align="center">
  <a href="https://registry.modelcontextprotocol.io"><img alt="MCP registry" src="https://img.shields.io/badge/MCP%20registry-io.github.tenkenco%2Fdeclaude-f97316"></a>
  <a href="https://speak-english.tenken.co"><img alt="Live" src="https://img.shields.io/badge/live-speak--english.tenken.co-4ade80"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-blue"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.12%2B-3776ab">
</p>

---

```
Before  Certainly! I'd be delighted to delve into this fascinating topic —
        it's a testament to the rich tapestry of modern software engineering.

After   Sure. Here's an overview of the topic.
```

Runs on an open-source model (Qwen2.5-14B-AWQ) on our own L4 GPUs, so your text never
reaches a commercial AI provider. Prompt logging is disabled at the model server: text is
processed in memory and discarded, never written to disk, a database, or logs.

**Live**: [speak-english.tenken.co](https://speak-english.tenken.co) ·
[Get an API key](https://speak-english.tenken.co/signin) ·
[Translate a document](https://speak-english.tenken.co/documents)

| | Free | $5 / month |
|---|---|---|
| Translations | 100 / month | Unlimited |
| Documents | 5 / month, 200 KB | 500 / month, 2 MB |
| Card required | No | Yes |

## Quick start

**1. Get a key** — sign in at [/signin](https://speak-english.tenken.co/signin). Keys don't expire.

**2. Pick your surface:**

```bash
# REST
curl -X POST https://speak-english.tenken.co/v1/translate \
  -H "Authorization: Bearer $DECLAUDE_TOKEN" -H "Content-Type: application/json" \
  -d '{"text": "Great question! It is worth noting that..."}'
```

```bash
# MCP (Claude Code, Cursor, any MCP client) — sign-in happens in the browser via OAuth
claude mcp add --transport http declaude https://speak-english.tenken.co/mcp
```

```bash
# claudish-to-english plugin (drop-in, no local Ollama needed)
export CLAUDISH_OLLAMA="https://x:$DECLAUDE_TOKEN@speak-english.tenken.co"
export CLAUDISH_MODEL="qwen2.5-14b-instruct"
```

Also: [hook/](hook/) for a standalone Claude Code Stop-hook, and [skills/declaude/](skills/declaude/) to
install declaude as an agent skill.

## Pricing

100 translations/month free. Past that, requests return `402` with a machine-readable
payment challenge and an `upgrade_url` → [$5/month, unlimited](https://speak-english.tenken.co/upgrade).
Only successful translations count against quota.

## Architecture

```
client ── API key / Clerk JWT ──> Cloud Run gateway ── VPC ──> internal LB ──> vLLM GPU MIG
                                     │                                        (Qwen2.5-14B, spot L4)
                                     ├─> Firestore (usage, paid flags, key hashes)
                                     └─> Stripe (payment link + signed webhooks)
```

- **gateway/** — FastAPI: `/v1/translate`, `/mcp`, `/api/chat` (Ollama-compatible), `/v1/keys`,
  `/v1/billing/webhook`, `/signin`, `/upgrade`, `/health`. 86 tests; every boundary injectable.
- **infra/** — Terraform, state in GCS, plan converges to zero diff. GPU tier is private-IP spot
  instances behind an internal L7 LB; template rollouts are deliberate (OPPORTUNISTIC).
- **hook/** — Claude Code hook client (fails open; never blocks a session).
- **CI/CD** — PRs: lint + tests (gateway/hook/infra). Main: test → build → deploy via Workload
  Identity Federation → smoke test.

## Operating notes

- `/healthz` is reserved by Google Frontend on run.app — use `/health`.
- Model swaps are one Terraform variable; 32B needs 2×L4 (quota bump), 14B fits one L4.
- Secrets live in Secret Manager only. API keys are stored as SHA-256 digests.
- Developed strictly test-first; every production defect found in dogfooding became a
  regression test before its fix.
