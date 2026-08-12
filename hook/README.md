# declaude hook

Claude Code hook client for the hosted declaude service.

## Install

1. Open <https://declaude-gateway-477468296053.us-central1.run.app/signin> and sign in.
2. Select **Create an API key** and copy the key. The page shows it once.
3. Add the key and the hook to `~/.claude/settings.json`:

```json
{
  "env": { "DECLAUDE_TOKEN": "dc_..." },
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /path/to/declaude_hook.py",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

4. Start a new Claude Code session. Settings load at launch, so an existing session
   keeps the old configuration.

Every completed response gets a plain-English rendition attached. The hook fails open:
if the service or your quota is unavailable, your session is never blocked.

API keys do not expire. Revoke one by deleting its document from the `api_keys`
collection in Firestore.

## MCP alternative

```
claude mcp add --transport http declaude https://declaude-gateway-477468296053.us-central1.run.app/mcp \
  --header "Authorization: Bearer $DECLAUDE_TOKEN"
```
