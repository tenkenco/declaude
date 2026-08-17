# declaude hook

Claude Code hook client for the hosted declaude service. One script, two hook
events; it dispatches on `hook_event_name`.

## Install (MessageDisplay, recommended)

The `MessageDisplay` event streams each assistant reply to the hook in chunks
and renders the hook's `displayContent` reply in the terminal. The plain-English
rendition appears inline directly under each reply, at display time only:
nothing enters the model's context window, so it costs zero Claude tokens. The
event exists in current Claude Code but is undocumented; the hook fails open,
so on errors or older versions the original text displays unchanged.

1. Get a `dk_` key at the declaude landing page ([/signin](https://speak-english.tenken.co/signin)).
2. `export DECLAUDE_TOKEN=<key>` in your shell profile.
3. Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "MessageDisplay": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /path/to/declaude_hook.py",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

Set `timeout: 30` explicitly. The event's default timeout is 10 seconds, which
a cold GPU (spot reclaim) can miss.

Messages under 40 characters are skipped, and a rewrite identical to the
original is dropped, so quota is only spent where it helps.

## Install (Stop fallback)

For Claude Code versions without `MessageDisplay`, register the same script
under `Stop`. The rendition of the turn's final message then arrives as a
system message after the turn instead of inline:

```json
{"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "python3 /path/to/declaude_hook.py"}]}]}}
```

Both modes fail open: if the service or your quota is unavailable, your
session is never blocked.

## MCP alternative

```
claude mcp add --transport http declaude https://speak-english.tenken.co/mcp
```

Sign-in happens in the browser (OAuth); no key handling needed. The MCP tools
are for on-demand rewrites of specific text; only the hook rewrites replies
automatically.
