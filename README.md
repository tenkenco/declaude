# declaude

**Claude-English → plain English, as a service.**

Declaude is a translation service that rewrites the distinctive, sycophantic writing style of AI assistants into plain, natural English. The service uses a robust open-source model (Qwen2.5-14B) running on dedicated GPU infrastructure, ensuring that your data never touches a commercial AI provider. It offers a generous free tier of 100 translations per month, with unlimited usage available for just $5 per month. Developers can integrate Declaude through a REST API, an MCP server, or a drop-in Claude Code plugin.

**Live**: [speak-english.tenken.co](https://speak-english.tenken.co) · [Get an API key](https://speak-english.tenken.co/signin)

> The paragraph above was written by an AI assistant, then rewritten by declaude itself.

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
# MCP (Claude Code, Cursor, any MCP client)
claude mcp add --transport http declaude https://speak-english.tenken.co/mcp \
  --header "Authorization: Bearer $DECLAUDE_TOKEN"
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
