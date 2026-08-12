# declaude

Claude-English → plain English translation service.

An open-source-model-backed API + MCP server that rewrites "Claude English"
(sycophantic openers, hedging filler, bullet addiction) into natural prose,
inspired by [gvzdv/claudish-to-english](https://github.com/gvzdv/claudish-to-english)
but hosted on GCP instead of local Ollama.

- **gateway/** — FastAPI service: `/v1/translate`, `/mcp` (JSON-RPC), Clerk auth,
  free tier + x402-style 402 payment gate (Stripe).
- **infra/** — Terraform for a dedicated GCP project: vLLM GPU serving behind a
  load balancer, Cloud Run gateway, secrets, CI/CD.

Developed test-first; every merge is dogfooded end-to-end before deploy.
