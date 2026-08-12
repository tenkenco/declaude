"""Sign-in page. Clerk handles the sign-in; the page then mints a declaude API key.

Served at GET /signin. The publishable key is public by design, so injecting it into
the HTML is safe. Without it the page explains the misconfiguration instead of failing."""

_UNCONFIGURED = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>declaude — sign in</title></head>
<body style="font:16px/1.6 system-ui;max-width:40rem;margin:4rem auto;padding:0 1.25rem">
<h1>Sign-in is not configured</h1>
<p>Set <code>DECLAUDE_CLERK_PUBLISHABLE_KEY</code> on the gateway and redeploy.</p>
</body></html>
"""

_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>declaude — sign in and get your API key</title>
<style>
:root{{
  --bg:#0b0e14;--surface:#11151f;--border:#1f2634;
  --text:#e6e9ef;--muted:#9aa4b2;--accent:#f97316;--accent-soft:#fdba74;
  --code-bg:#0d1117;--green:#4ade80;--red:#f87171;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);
  font:16px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  -webkit-font-smoothing:antialiased}}
code,pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}
main{{max-width:640px;margin:0 auto;padding:3.5rem 1.25rem 4rem}}
a{{color:var(--accent-soft)}}
.logo{{font-size:1.05rem;font-weight:600;color:var(--muted);margin-bottom:2rem}}
.logo b{{color:var(--accent)}}
h1{{font-size:1.75rem;letter-spacing:-.02em;margin-bottom:.5rem}}
.sub{{color:var(--muted);margin-bottom:2rem}}
#clerk{{margin-bottom:1.5rem}}
.card{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:1.4rem;margin-top:1.25rem}}
button{{background:var(--accent);color:#0b0e14;border:0;border-radius:8px;
  padding:.65rem 1.1rem;font:inherit;font-weight:600;cursor:pointer}}
button:disabled{{opacity:.55;cursor:default}}
button.ghost{{background:transparent;color:var(--muted);border:1px solid var(--border);font-weight:400}}
pre{{background:var(--code-bg);border:1px solid var(--border);border-radius:10px;
  padding:.9rem 1rem;overflow-x:auto;font-size:.85rem;margin:.75rem 0;white-space:pre-wrap;word-break:break-all}}
.hint{{color:var(--muted);font-size:.9rem}}
.warn{{color:var(--accent-soft);font-size:.9rem}}
.err{{color:var(--red);font-size:.9rem}}
.row{{display:flex;gap:.6rem;flex-wrap:wrap;align-items:center;margin-top:.75rem}}
[hidden]{{display:none !important}}
</style>
</head>
<body>
<main>
  <p class="logo">de<b>claude</b></p>
  <h1>Get your API key</h1>
  <p class="sub">Sign in once. Your key does not expire, so it works in a Claude Code hook,
  an MCP client, or a shell profile.</p>

  <div id="clerk"></div>

  <section id="issue" class="card" hidden>
    <p>You are signed in as <b id="who"></b>.</p>
    <div class="row">
      <button id="mint">Create an API key</button>
      <button id="out" class="ghost">Sign out</button>
    </div>
    <p class="hint" style="margin-top:.75rem">A new key does not revoke an old one.</p>
    <p id="error" class="err" hidden></p>
  </section>

  <section id="result" class="card" hidden>
    <p><b>Your API key</b></p>
    <p class="warn">Copy it now. It is shown once and never stored in plain text.</p>
    <pre id="key"></pre>
    <div class="row">
      <button id="copy">Copy key</button>
      <button id="copycmd" class="ghost">Copy hook command</button>
    </div>
    <p class="hint" style="margin-top:1rem">Use it in the Claude Code hook:</p>
    <pre id="cmd"></pre>
  </section>
</main>

<script src="{clerk_js}" data-clerk-publishable-key="{pk}" crossorigin="anonymous" async
        onload="start()" onerror="failed()"></script>
<script>
const $ = (id) => document.getElementById(id);
let clerk = null;

function failed() {{
  $("clerk").innerHTML =
    '<p class="err">Could not load the sign-in script. Check your network and reload.</p>';
}}

function show(el, on) {{ el.hidden = !on; }}

async function start() {{
  clerk = window.Clerk;
  try {{
    await clerk.load();
  }} catch (e) {{
    failed();
    return;
  }}
  render();
}}

function render() {{
  if (clerk.user) {{
    $("who").textContent =
      clerk.user.primaryEmailAddress?.emailAddress || clerk.user.id;
    show($("issue"), true);
    $("clerk").innerHTML = "";
  }} else {{
    show($("issue"), false);
    show($("result"), false);
    clerk.mountSignIn($("clerk"));
  }}
}}

async function mint() {{
  const btn = $("mint");
  btn.disabled = true;
  show($("error"), false);
  try {{
    const token = await clerk.session.getToken();
    const res = await fetch("/v1/keys", {{
      method: "POST",
      headers: {{ Authorization: "Bearer " + token }},
    }});
    if (!res.ok) throw new Error("server returned " + res.status);
    const data = await res.json();
    $("key").textContent = data.key;
    $("cmd").textContent =
      'export DECLAUDE_TOKEN=' + data.key;
    show($("result"), true);
  }} catch (e) {{
    $("error").textContent = "Could not create a key: " + e.message;
    show($("error"), true);
  }} finally {{
    btn.disabled = false;
  }}
}}

async function copyText(text, btn, done) {{
  try {{
    await navigator.clipboard.writeText(text);
    const was = btn.textContent;
    btn.textContent = done;
    setTimeout(() => (btn.textContent = was), 1500);
  }} catch (e) {{
    btn.textContent = "Copy failed — select the text";
  }}
}}

document.addEventListener("click", (e) => {{
  if (e.target.id === "mint") mint();
  if (e.target.id === "out") clerk.signOut().then(render);
  if (e.target.id === "copy") copyText($("key").textContent, e.target, "Copied");
  if (e.target.id === "copycmd") copyText($("cmd").textContent, e.target, "Copied");
}});
</script>
</body>
</html>
"""


def signin_html(publishable_key: str, clerk_js_url: str = "") -> str:
    if not publishable_key:
        return _UNCONFIGURED
    return _PAGE.format(pk=publishable_key, clerk_js=clerk_js_url or clerk_js_for(publishable_key))


def clerk_js_for(publishable_key: str) -> str:
    """Derive the ClerkJS bundle URL from the publishable key.

    A publishable key is `pk_test_<base64 of "<frontend-api-host>$">`, so the host the
    bundle must be served from is recoverable without a second config value."""
    import base64

    _, _, encoded = publishable_key.partition("_")
    _, _, encoded = encoded.partition("_")
    try:
        host = base64.b64decode(encoded + "==").decode().rstrip("$")
    except ValueError:  # binascii.Error and UnicodeDecodeError both subclass ValueError
        host = ""
    if not host:
        return "https://clerk.browser.js.invalid"
    return f"https://{host}/npm/@clerk/clerk-js@5/dist/clerk.browser.js"
