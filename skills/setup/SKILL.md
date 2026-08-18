---
name: setup
description: Finish declaude setup after installing the plugin. Use when the plain-English renditions do not appear, when the plugin key or opt-in is unset, or when the user asks to set up, configure or verify declaude.
---

# declaude setup

The plugin already registers the Claude Code hook. It ships `hooks/hooks.json`, which
Claude Code loads on install. Its `hook_enabled` option defaults to true, so a fresh
install rewrites replies at once. The `api_key` option stays optional, because the MCP
tools sign in on their own and must not demand a key.

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

## 2. Check for a legacy key

```bash
echo "${DECLAUDE_TOKEN:+set}"
```

If the answer is `set`, do not edit or replace it. The plugin can keep using
`DECLAUDE_TOKEN` during migration. If the answer is empty, the user may still have a key in
secure plugin storage; check that in step 3.

## 3. Configure and enable the plugin hook

Only after every manual entry is removed, run:

```
/plugin configure declaude@tenken
```

Set the options in the configuration dialog:

- `api_key`: if a key is already stored, do not edit or replace it. Otherwise get a `dk_`
  key at [/signin](https://speak-english.tenken.co/signin) and enter it in this masked
  field. Do not paste it into the chat. Existing `DECLAUDE_TOKEN` users may leave this
  empty, because the hook falls back to that environment variable.
- `hook_enabled`: type `true` or `false` in this field. It is true by default. Type
  `false` to stop automatic rewrites. Type `true` if the user exports `DECLAUDE_TOKEN` and
  wants the plugin hook on. The hook exits silently when it has no key, so a missing key
  produces no error message.

Claude Code stores `api_key` in secure storage and exports it only to the plugin process as
`CLAUDE_PLUGIN_OPTION_API_KEY`. It stores the Boolean opt-in in user settings. Project files
cannot supply either value.

## 4. Verify

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
