# declaude

**Claude-English → plain English, as a service.**

An API + MCP server that rewrites "Claude English" (sycophantic openers, hedging
filler, bullet addiction) into natural prose — inspired by
[gvzdv/claudish-to-english](https://github.com/gvzdv/claudish-to-english), but backed
by a larger open-source model (Qwen2.5-32B-Instruct-AWQ) on dedicated GCP infrastructure
instead of local Ollama.

**Production**: https://declaude-gateway-477468296053.us-central1.run.app (project `declaude-prod`)

## Use it

**Get a key**: open `/signin`, sign in with Clerk, and select **Create an API key**.
The key is shown once and does not expire. Set it as `DECLAUDE_TOKEN`.

**Landing / docs**: open the production URL in a browser.

**MCP** (Claude Code, Cursor, any MCP client):
```
claude mcp add --transport http declaude \
  https://declaude-gateway-477468296053.us-central1.run.app/mcp \
  --header "Authorization: Bearer $DECLAUDE_TOKEN"
```

**HTTP API**:
```
curl -X POST https://declaude-gateway-477468296053.us-central1.run.app/v1/translate \
  -H "Authorization: Bearer $DECLAUDE_TOKEN" -H "Content-Type: application/json" \
  -d '{"text": "Great question! It is worth noting that..."}'
```

**Claude Code hook**: see [hook/](hook/) — attaches a plain-English rendition to every
completed response; fails open.

## Pricing (x402 pattern)

100 free translations/month per user (only successful translations count). Past that,
requests return **HTTP 402** with a machine-readable payment challenge
(`accepts[0].url` → Stripe payment link, $5/mo). Webhook flips the paid flag; paid
users are unmetered.

## Architecture

```
client ── API key ────> Cloud Run gateway ── VPC ──> internal L7 LB ──> vLLM GPU MIG
browser ─ Clerk JWT ──>   (mints keys at POST /v1/keys)
                          │                                             (Qwen2.5-32B-AWQ, L4)
                          ├─> Firestore (usage/paid flags)
                          └─> Stripe (payment link + signed webhooks)
```

- **gateway/** — FastAPI: `/v1/translate`, `/mcp` (JSON-RPC 2.0), `/v1/billing/webhook`,
  `/health`. Clerk JWKS auth; every external boundary injectable (TDD: 43 tests).
- **infra/** — Terraform (state: `gs://declaude-prod-tfstate`). Model tier is private-IP-only
  behind an internal load balancer; scale via `model_replicas` / machine type vars.
- **hook/** — end-user Claude Code hook client.
- **CI/CD** — GitHub Actions: lint + tests on PR; on main: test → build → deploy to Cloud Run
  via Workload Identity Federation (no stored keys) → smoke test.

## Operations

- Secrets live in Secret Manager (`clerk-secret-key`, `stripe-*`); never in state or env files.
- Monitoring: uptime check on `/health` + email alert; $500/mo budget with 50/90/100% alerts.
- Known constraint: L4 capacity in us-central1 flaps; the MIG chases zones a/b/c
  (`ZONE_RESOURCE_POOL_EXHAUSTED` self-heals). GPU quota: 1 (bump via quota preferences
  for multi-replica or 2×L4 32B-full-context serving).
- `/healthz` is intercepted by Google Frontend on run.app — always use `/health` externally.

Developed test-first; every defect found in dogfooding lands as a regression test before the fix.
