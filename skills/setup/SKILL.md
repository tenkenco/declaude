---
name: setup
description: Finish declaude setup after installing the plugin. Use when the plain-English renditions do not appear, when DECLAUDE_TOKEN is unset, or when the user asks to set up, configure or verify declaude.
---

# declaude setup

The plugin already registers the Claude Code hook. It ships `hooks/hooks.json`, which
Claude Code loads on install. The hook stays silent until the user supplies a key, so one
step remains: set `DECLAUDE_TOKEN`.

Work through the steps below in order. Report the result of each one.

## 1. Check for an existing key

```bash
echo "${DECLAUDE_TOKEN:+set}"
```

Treat this answer as a hint, not proof. Your shell reads the user's profile. The hook does
not. It inherits the environment of the process that started Claude Code. So a `set` answer
here still fails at display time when the user added the key after that process started.

An empty answer means the key is missing. Run every step below. A `set` answer means the key
exists, so skip step 2, but still run steps 3 to 5.

## 2. Get a key

Send the user to [/signin](https://speak-english.tenken.co/signin). They sign in and mint a
`dk_` key. Keys never expire. One key works for the hook, the MCP server and the REST API.

Do not ask the user to paste the key into the chat. Ask them to add it in step 3 themselves.

## 3. Store the key and restart

Tell the user to add this line to their shell profile, such as `~/.zshrc`:

```bash
export DECLAUDE_TOKEN=dk_your_key_here
```

Then the user must open a new terminal and start Claude Code again. This step is never
optional. The hook reads the environment of the process that started Claude Code, and a
`/reload-plugins` call does not pick up a new environment variable.

## 4. Remove any manual hook entry

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
twice and bills the user twice.

## 5. Verify

```bash
curl -s -w '\nHTTP %{http_code}\n' https://speak-english.tenken.co/v1/usage \
  -H "Authorization: Bearer $DECLAUDE_TOKEN"
```

`HTTP 200` with plan and usage counts means the key works. `HTTP 401` means the key is
wrong. `HTTP 503` means the GPU is warming up, so retry shortly.

This call proves the key, not the hook. It runs in your shell, which reads the user's
profile. So it can pass while the hook still has no key.

The hook itself is proven only in a session. Ask the user to start a new Claude Code
session and send any prompt. A reply longer than 40 characters shows a
`[declaude] plain English:` block under it.

## If nothing appears

- The running Claude Code process may lack the key. This is the most common cause. The user
  set the key after starting Claude Code, or started it from a desktop icon that never read
  the shell profile. Ask them to start Claude Code from a terminal that prints the key with
  `echo "${DECLAUDE_TOKEN:+set}"`.
- Replies under 40 characters are skipped on purpose.
- A rendition identical to the original is dropped rather than shown.
- The hook fails open. Any error leaves the original reply on screen.
- Run `claude --debug` to see the hook's exit code and output.
- On Windows, the registered command fails, because it calls `python3`. See
  [`hook/README.md`](https://github.com/tenkenco/declaude/blob/main/hook/README.md).
