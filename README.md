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
Before  "Great question! Before I answer, let me make sure I understand what
        you're asking. You want to know why the build is failing. Let me walk
        through my thinking, and then I'll give you the answer."

After   "I understand you want to know why the build is failing. Here's what
        I think is happening."
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

```bash
claude mcp add --transport http declaude https://speak-english.tenken.co/mcp
```

No API key to paste: your client discovers OAuth, opens a browser sign-in, and holds the
token. That is the whole setup.

| Surface | Use it for | Docs |
|---|---|---|
| **MCP server** | Claude Code, Cursor, any MCP client. Tools: `translate`, `usage` | [skill](skills/declaude/SKILL.md) |
| **Claude Code hook** | Rewrites replies as they render, costs zero Claude tokens | [hook/](hook/) |
| **Documents** | Drop a `.md`/`.txt`, get it back rewritten | [web](https://speak-english.tenken.co/documents) |
| **REST API** | `POST /v1/translate`, `/v1/documents`, `/v1/usage` | [skill](skills/declaude/SKILL.md#rest-api) |
| **OpenAI-compatible** | `POST /v1/chat/completions` — point any OpenAI client at `/v1` | [skill](skills/declaude/SKILL.md#rest-api) |

Full usage, authentication and quota behaviour live in
**[skills/declaude/SKILL.md](skills/declaude/SKILL.md)** — installable as an agent skill, so
your agent can read it directly.

## Architecture

```
client ── API key / OAuth / Clerk JWT ──> Cloud Run gateway ── VPC ──> internal LB ──> vLLM GPU MIG
                                              │                                    (Qwen2.5-14B, spot L4)
                                              ├─> Firestore (usage, paid flags, key hashes)
                                              └─> Stripe (payment link + signed webhooks)
```

- **gateway/** — FastAPI. Every boundary is injectable, which is why the suite runs without
  network, GPU or cloud credentials.
- **infra/** — Terraform, state in GCS, plan converges to zero diff. The GPU tier is
  private-IP spot instances behind an internal L7 load balancer.
- **hook/** — Claude Code hook client. Fails open; never blocks a session.
- **CI** — lint, tests and coverage on every PR; security scans and a production smoke test
  daily.

<details>
<summary><b>Operating notes</b></summary>

- `/healthz` is reserved by Google Frontend on run.app — use `/health`.
- Model swaps are one Terraform variable; 32B needs 2×L4 (quota bump), 14B fits one L4.
- MIG template rollouts are deliberate (`OPPORTUNISTIC`): a proactive policy turned benign
  template edits into surprise 15-minute outages.
- Secrets live in Secret Manager only. API keys are stored as SHA-256 digests, so a database
  leak yields no usable credential.
- Prompt logging is disabled at the model server; request text is processed in memory and
  discarded.
- Developed test-first. Every production defect found while dogfooding became a regression
  test before its fix.

</details>

## Development

```bash
cd gateway
uv sync --dev
uv run pytest -q          # 197 tests
uv run ruff check .
```

## Credit

Grew out of [gvzdv/claudish-to-english](https://github.com/gvzdv/claudish-to-english), the
original local-Ollama hook. Licensed [MIT](LICENSE); upstream notice in
[THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).
