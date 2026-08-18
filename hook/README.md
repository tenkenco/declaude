# declaude hook

Claude Code hook client for the hosted declaude service. One script, two hook
events; it dispatches on `hook_event_name`.

The plugin installs this hook for you. Install it by hand only if you do not
want the plugin.

## Install (plugin, recommended)

```
/plugin marketplace add tenkenco/declaude
/plugin install declaude@tenken
```

The plugin ships `hooks/hooks.json` at its root, and Claude Code loads that file
on install. It registers the `MessageDisplay` event and points at
`hook/declaude_hook.py` inside the plugin, with a 30 second timeout.

The `hook_enabled` option defaults to true. So a fresh install rewrites replies
as soon as you set an `api_key`. The key stays optional, because the MCP tools
sign in on their own and must not demand one.

New install:

1. Get a `dk_` key at [/signin](https://speak-english.tenken.co/signin).
2. Run `/plugin configure declaude@tenken` and paste the key in the masked
   `api_key` field.
3. Run `/reload-plugins`, as the configuration dialog instructs.

The hook prints nothing when it has no key. So run `/declaude:setup` if no
rendition appears.

Upgrade from version 1.0: run `/declaude:setup` instead. It removes any manual
hook entry first, because a manual entry plus the plugin bills you twice.

The `hook_enabled` field takes `true` or `false`. Type `false` to stop automatic
rewrites.

The hook carries one more guard for version 1.0 users. It stays inert when you
export `DECLAUDE_TOKEN` and Claude Code passes no value for `hook_enabled`. So
run `/declaude:setup` when you upgrade, and remove the manual hook yourself.

Claude Code omits an unset option from the hook environment. It does not export
the declared default. Measured on 2026-08-18: with the default declared true and
no stored value, the variable arrived absent. So the guard fires, and the
declared default alone can never turn the hook on. The hook treats an empty
value as on for that reason.

The hook stays quiet about most failures, so a bad network never breaks a
session. It speaks up for one case. An exhausted monthly quota shows a notice
with the upgrade link. It shows that notice once, then records the answer and
skips both the notice and the request. The record expires after an hour, so a
paid upgrade takes effect without a restart.

Claude Code stores `api_key` in secure storage rather than `settings.json`. The
plugin hook exits silently while disabled or while neither the secure key nor
`DECLAUDE_TOKEN` exists. So a missing key produces no error and no rewrite. A
manual hook still uses `DECLAUDE_TOKEN`, so existing version 1.0 setups keep
working until the user deliberately migrates them.

If you already registered this hook by hand, remove that entry now. A manual
entry plus the plugin translates every reply twice and bills you twice. Claude
Code merges hooks from several settings files, so check them all:

```bash
for f in "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/settings.json \
         "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/settings.local.json \
         .claude/settings.json .claude/settings.local.json; do
  [ -f "$f" ] && grep -l declaude_hook "$f"
done
```

Windows: the registered command calls `python3`, which Windows does not ship
under that name. Skip the plugin registration there. Install by hand instead,
with `python` or the `py` launcher in the command.

## Install (manual, MessageDisplay)

The `MessageDisplay` event streams each assistant reply to the hook in chunks
and renders the hook's `displayContent` reply in the terminal. The plain-English
rendition appears inline directly under each reply, at display time only:
nothing enters the model's context window, so it costs zero Claude tokens. Older
Claude Code versions lack the event; the hook fails open, so on errors or older
versions the original text displays unchanged.

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

Manual installs use `DECLAUDE_TOKEN` and do not read plugin configuration.

Messages under 40 characters are skipped before the service is called, so they
cost no quota. A rendition that comes back empty or identical to the original
is dropped rather than displayed (that call is still billed).

While a reply streams, chunks are buffered in a private per-user directory
(`declaude-<uid>`, mode 0700, files 0600) under the system temp dir. Buffers
from interrupted streams are swept after an hour.

## Install (Stop fallback)

For Claude Code versions without `MessageDisplay`, register the same script
under `Stop`. The rendition of the turn's final message then arrives as a
system message after the turn instead of inline:

```json
{"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "python3 /path/to/declaude_hook.py"}]}]}}
```

Register the hook ONCE. The plugin install and the two manual installs are three
routes to the same script, so pick one. With two of them live on a current
Claude Code, each reply is translated twice and billed twice. If you upgrade
from the old Stop install, remove the `Stop` entry when you add
`MessageDisplay` or the plugin.

Both modes fail open: if the service or your quota is unavailable, your
session is never blocked.

## Two similar directory names

`hooks/` is the name the plugin specification requires. It holds `hooks.json`,
the registration Claude Code reads on install. `hook/` predates it and holds the
script and its tests. Keep the two apart.

## MCP alternative

```
claude mcp add --transport http declaude https://speak-english.tenken.co/mcp
```

Sign-in happens in the browser (OAuth); no key handling needed. The MCP tools
are for on-demand rewrites of specific text; only the hook rewrites replies
automatically.
