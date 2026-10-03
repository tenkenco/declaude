---
name: setup
description: Finish declaude setup after installing the plugin. Use when the plain-English renditions do not appear, when the plugin key or opt-in is unset, when the `translate` and `usage` MCP tools are missing, or when the user asks to set up, configure or verify declaude.
---

# declaude setup

The plugin already registers the Claude Code hook. It ships `hooks/hooks.json`, which
Claude Code loads on install. An unset `hook_enabled` option means on, so a fresh
install rewrites replies after its API key is configured. The manifest does not declare
a default because Claude Code may export declared defaults to plugin processes. The
`api_key` option stays optional because the MCP tools sign in on their own.

Version 1.3 also registers the MCP server. The plugin ships `.mcp.json`, so the `translate`
and `usage` tools load in every directory. Earlier versions relied on a manual
`claude mcp add`, which bound the server to one directory.

One case still stays inert. A user who exports `DECLAUDE_TOKEN` and never sets
`hook_enabled` keeps the plugin hook off. That user may still run a version 1.0 manual
hook, and two hooks would translate and bill every reply twice.

Work through the steps below in order. Report the result of each one.

## 1. Remove any manual hook entry

Claude Code merges hooks from several settings files. Search all of them:

```bash
for f in "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/settings.json \
         "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/settings.local.json \
         .claude/settings.json .claude/settings.local.json; do
  [ -f "$f" ] && grep -l declaude_hook "$f"
done
```

Open each file the search names. Look for a `MessageDisplay` or `Stop` entry that runs
`declaude_hook.py`. Remove that entry.

The plugin now registers the hook. A manual entry on top of it translates every reply
twice and bills the user twice. Do not enable the plugin hook until every manual entry is
removed.

## 2. Remove any manual MCP entry

Version 1.3 registers the MCP server through the plugin. Earlier versions told the user to
run `claude mcp add`. That command defaults to `local` scope, so it binds the server to one
directory.

A manual entry does not create a second connection. Claude Code hides the plugin entry
wherever the manual entry applies. The manual entry then keeps its old directory limit. The
tool name also changes between directories, from `declaude` to `plugin:declaude:declaude`.
Remove the manual entry to get one name and one behaviour everywhere.

List the manual entries:

```bash
claude mcp list
```

Remove a `declaude` entry the command reports:

```bash
claude mcp remove declaude
```

Run the removal in the directory where the user first added the server. Local scope stores
the entry per directory, so a removal in another directory reports nothing to remove. Search
the config file to find that directory:

```bash
python3 -c "
import json, pathlib
d = json.loads(pathlib.Path.home().joinpath('.claude.json').read_text())
for path, cfg in d.get('projects', {}).items():
    if 'declaude' in (cfg.get('mcpServers') or {}):
        print(path)
print('user scope:', 'declaude' in d.get('mcpServers', {}))
"
```

Remove every `local` scope entry. Remove a `user` scope entry too while the plugin stays
enabled, because it hides the plugin entry. Keep a `user` scope entry only when the user
disables the plugin and still wants the tools.

The plugin entry signs in on its own. Claude Code reports `Needs authentication` until the
user runs a tool once and completes the browser sign-in.

## 3. Check for a legacy key

```bash
echo "${DECLAUDE_TOKEN:+set}"
```

If the answer is `set`, do not edit or replace it. The plugin can keep using
`DECLAUDE_TOKEN` during migration. If the answer is empty, the user may still have a key in
secure plugin storage; check that in step 4.

## 4. Configure and enable the plugin hook

Only after every manual entry is removed, run:

```
/plugin configure declaude@tenken
```

Set the options in the configuration dialog:

- `api_key`: if a key is already stored, do not edit or replace it. Otherwise get a `dk_`
  key at [/signin](https://speak-english.tenken.co/signin) and enter it in this masked
  field. Do not paste it into the chat. Existing `DECLAUDE_TOKEN` users may leave this
  empty, because the hook falls back to that environment variable.
- `hook_enabled`: type `true` or `false` in this field. An unset value means on. Type
  `false` to stop automatic rewrites. Type `true` if the user exports `DECLAUDE_TOKEN` and
  wants the plugin hook on. The hook exits silently when it has no key, so a missing key
  produces no error message.

Claude Code stores `api_key` in secure storage and exports it only to the plugin process as
`CLAUDE_PLUGIN_OPTION_API_KEY`. It stores the Boolean opt-in in user settings. Project files
cannot supply either value.

## 5. Verify

If the plugin is using legacy `DECLAUDE_TOKEN`, verify that key:

```bash
curl -s -w '\nHTTP %{http_code}\n' https://speak-english.tenken.co/v1/usage \
  -H "Authorization: Bearer $DECLAUDE_TOKEN"
```

`HTTP 200` with plan and usage counts means the key works. `HTTP 401` means the key is
wrong. `HTTP 503` means the GPU is warming up, so retry shortly.

This proves the key, not the hook. Skip the command when the key is in plugin configuration;
secure plugin values are deliberately unavailable to the shell.

The hook itself is proven only in a session. Ask the user to start a new Claude Code
session and send any prompt. A reply longer than 40 characters shows a
`🧼 declaude plain English:` block under it.

## If the MCP tools are missing

The `translate` and `usage` tools need plugin version 1.3 or later. Run
`/plugin update declaude@tenken`, then start a new session.

On an earlier version the tools load only in the directory where the user ran
`claude mcp add`. Step 2 above names that directory.

The server is remote. A failed connection removes the tools for the whole session, so start
a new session after any network or sign-in error.

## If nothing appears

- Open `/plugin configure declaude@tenken` and confirm `hook_enabled` is true and `api_key`
  is set. If the plugin relies on legacy `DECLAUDE_TOKEN`, start Claude Code from a terminal
  that prints `set` for `echo "${DECLAUDE_TOKEN:+set}"`.
- Replies under 40 characters are skipped on purpose.
- A rendition identical to the original is dropped rather than shown.
- The hook fails open. Any error leaves the original reply on screen.
- Run `claude --debug` to see the hook's exit code and output.
- On Windows, the registered command fails, because it calls `python3`. See
  [`hook/README.md`](https://github.com/tenkenco/declaude/blob/main/hook/README.md).
