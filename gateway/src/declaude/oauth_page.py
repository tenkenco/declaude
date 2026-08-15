"""Authorize page: Clerk sign-in that returns HERE, then auto-approves and redirects.

The person already chose to connect this app in their MCP client; signing in IS the
consent. No raw client IDs, no extra clicks, no detour to Clerk's hosted portal.
"""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>declaude — authorize</title>
<style>
body{{background:#0b0e14;color:#e6e9ef;font:16px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
main{{max-width:560px;margin:0 auto;padding:3.5rem 1.25rem;
  display:flex;flex-direction:column;align-items:center;text-align:center}}
main>*{{width:100%}}
#clerk{{width:100%;display:flex;justify-content:center}}
#clerk>div{{display:flex;justify-content:center}}
.card{{text-align:left}}
.logo{{font-size:1.05rem;font-weight:600;color:#9aa4b2;margin-bottom:2rem}}.logo b{{color:#f97316}}
h1{{font-size:1.6rem;letter-spacing:-.02em;margin-bottom:.5rem}}
.sub{{color:#9aa4b2;margin-bottom:2rem}}
.card{{background:#11151f;border:1px solid #1f2634;border-radius:12px;padding:1.4rem;margin-top:1.25rem}}
button{{background:#f97316;color:#0b0e14;border:0;border-radius:8px;padding:.65rem 1.1rem;font:inherit;font-weight:600;cursor:pointer}}
.err{{color:#f87171}}
.spin{{display:inline-block;width:1em;height:1em;border:2px solid #9aa4b2;border-top-color:#f97316;border-radius:50%;animation:r 1s linear infinite;vertical-align:-.15em;margin-right:.5em}}
@keyframes r{{to{{transform:rotate(360deg)}}}}
[hidden]{{display:none !important}}
</style></head>
<body><main>
<p class="logo">de<b>claude</b></p>
<h1>Connect {client_name}</h1>
<p class="sub">Sign in to let <b>{client_name}</b> translate text with your declaude account.</p>
<div id="clerk"></div>
<section id="done-card" class="card" hidden>
  <p id="status"><span class="spin"></span>Signed in as <b id="who"></b> — returning you to {client_name}&hellip;</p>
  <p id="error" class="err" hidden></p>
  <p id="retry-row" hidden style="margin-top:.75rem"><button id="retry">Try again</button></p>
</section>
<script id="clerk-js" src="{clerk_js}" data-clerk-publishable-key="{pk}"
        crossorigin="anonymous" async></script>
<script>
const q = new URLSearchParams(location.search);
let clerk;
async function start() {{
  clerk = window.Clerk;
  await clerk.load({{appearance:{{variables:{{
    colorBackground:"#11151f",colorInputBackground:"#0d1117",colorText:"#e6e9ef",
    colorTextSecondary:"#9aa4b2",colorInputText:"#e6e9ef",colorPrimary:"#f97316",
    colorNeutral:"#e6e9ef",borderRadius:"8px"}}}}}});
  if (clerk.user) {{ autoApprove(); return; }}
  // Pin every sign-in path (email code, GitHub, Google) back to THIS page, params intact.
  clerk.mountSignIn(document.getElementById("clerk"), {{
    routing: "virtual",
    forceRedirectUrl: location.href,
    fallbackRedirectUrl: location.href,
  }});
  clerk.addListener(({{user}}) => {{ if (user) autoApprove(); }});
}}
let approving = false;
async function autoApprove() {{
  if (approving) return; approving = true;
  document.getElementById("clerk").innerHTML = "";
  document.getElementById("who").textContent =
    clerk.user.primaryEmailAddress?.emailAddress || "your account";
  document.getElementById("done-card").hidden = false;
  try {{
    const token = await clerk.session.getToken();
    const res = await fetch("/oauth/approve", {{
      method: "POST", headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{
        token, client_id: q.get("client_id"), redirect_uri: q.get("redirect_uri"),
        state: q.get("state"), code_challenge: q.get("code_challenge"),
        code_challenge_method: q.get("code_challenge_method"),
      }}),
    }});
    if (!res.ok) throw new Error("server returned " + res.status);
    location.href = (await res.json()).redirect_to;
  }} catch (err) {{
    approving = false;
    const el = document.getElementById("error");
    el.textContent = "Could not finish authorization: " + err.message; el.hidden = false;
    document.getElementById("retry-row").hidden = false;
  }}
}}
document.addEventListener("click", (e) => {{ if (e.target.id === "retry") autoApprove(); }});

// The loader is wired here, not with an onload= attribute: a CSP nonce covers this script
// but never inline event handlers, so an attribute handler is silently dropped and the page
// stays blank. Clerk may also finish before this script runs, hence the guard.
function bootClerk() {{
  const el = document.getElementById("clerk-js");
  let booted = false;
  const boot = () => {{ if (!booted) {{ booted = true; start(); }} }};
  el.addEventListener("load", boot);
  el.addEventListener("error", () => {{
    document.getElementById("clerk").innerHTML =
      '<p class="err">Could not load sign-in. Check your network and reload.</p>';
  }});
  if (window.Clerk) boot();
}}
bootClerk();
</script>
</main></body></html>
"""


def authorize_html(publishable_key: str, clerk_js_url: str, client_name: str) -> str:
    return PAGE.format(pk=publishable_key, clerk_js=clerk_js_url,
                       client_name=client_name or "this application")
