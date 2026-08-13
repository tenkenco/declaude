# declaude hook

Claude Code hook client for the hosted declaude service.

## Install

1. Get a Clerk session token (sign in at the declaude landing page).
2. `export DECLAUDE_TOKEN=<token>`
3. Add to `~/.claude/settings.json`:

```json
{"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "python3 /path/to/declaude_hook.py"}]}]}}
```

Every completed response gets a plain-English rendition attached. Fails open:
if the service or your quota is unavailable, your session is never blocked.

## MCP alternative

```
claude mcp add --transport http declaude https://speak-english.tenken.co/mcp \
  --header "Authorization: Bearer $DECLAUDE_TOKEN"
```
