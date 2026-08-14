# r/ClaudeAI

**Title**: I built a thing that rewrites Claude's "Great question!" voice into plain English — without using any of your tokens

**Body**:

The rewrite runs as a Claude Code display hook: it fires after Claude finishes, gets
processed on my own GPU (open-weight Qwen, not a paid API), and only changes what you see.
Your transcript and context window are untouched, so it costs zero Claude tokens.

Three ways to use it:
- **Hook** — replies render in plain English automatically
- **MCP** — `claude mcp add --transport http declaude https://speak-english.tenken.co/mcp`
  (no header, no key pasting; it opens a browser sign-in)
- **Documents** — drop a .md file, get it back with the sycophancy stripped and code blocks
  untouched

100 translations + 5 documents free per month. It grew out of gvzdv's open-source
claudish-to-english, which was a local Ollama hook — this is the hosted version, so no
local model needed.

Source (MIT): https://github.com/tenkenco/declaude

---

# r/mcp

**Title**: declaude — MCP server that rewrites assistant-voice into plain English (OAuth, no key pasting)

**Body**:

Just published to the official MCP registry as `io.github.tenkenco/declaude`.

```
claude mcp add --transport http declaude https://speak-english.tenken.co/mcp
```

No `--header`, no API key to paste: the server advertises resource metadata on 401, the
client discovers the auth server, registers dynamically, and runs PKCE. You sign in in a
browser and the client holds the token.

One tool, `translate`. Runs on Qwen2.5-14B on my own GPUs, so your text never reaches a
third-party AI API, and prompt logging is disabled at the model server. 100 free/month.
