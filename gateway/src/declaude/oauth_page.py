"""Authorize page for the OAuth flow: Clerk sign-in, then approve -> redirect with code."""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>declaude — authorize</title>
<style>
body{{background:#0b0e14;color:#e6e9ef;font:16px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
main{{max-width:560px;margin:0 auto;padding:3.5rem 1.25rem}}
.logo{{font-size:1.05rem;font-weight:600;color:#9aa4b2;margin-bottom:2rem}}.logo b{{color:#f97316}}
h1{{font-size:1.6rem;letter-spacing:-.02em;margin-bottom:.5rem}}
.sub{{color:#9aa4b2;margin-bottom:2rem}}
.card{{background:#11151f;border:1px solid #1f2634;border-radius:12px;padding:1.4rem;margin-top:1.25rem}}
button{{background:#f97316;color:#0b0e14;border:0;border-radius:8px;padding:.65rem 1.1rem;font:inherit;font-weight:600;cursor:pointer}}
.err{{color:#f87171}}
[hidden]{{display:none !important}}
</style></head>
<body><main>
<p class="logo">de<b>claude</b></p>
<h1>Authorize this application</h1>
<p class="sub"><b>{client_id}</b> wants to translate text with your declaude account.</p>
<div id="clerk"></div>
<section id="approve-card" class="card" hidden>
  <p>Signed in as <b id="who"></b>.</p>
  <p style="margin-top:.75rem"><button id="approve">Approve and continue</button></p>
  <p id="error" class="err" hidden></p>
</section>
<script src="{clerk_js}" data-clerk-publishable-key="{pk}" crossorigin="anonymous" async onload="start()"></script>
<script>
const q = new URLSearchParams(location.search);
let clerk;
async function start() {{
  clerk = window.Clerk;
  await clerk.load({{appearance:{{variables:{{colorBackground:"#11151f",colorText:"#e6e9ef",colorPrimary:"#f97316",colorInputBackground:"#0d1117",colorInputText:"#e6e9ef"}}}}}});
  render();
}}
function render() {{
  if (clerk.user) {{
    document.getElementById("who").textContent = clerk.user.primaryEmailAddress?.emailAddress || clerk.user.id;
    document.getElementById("approve-card").hidden = false;
    document.getElementById("clerk").innerHTML = "";
  }} else {{
    clerk.mountSignIn(document.getElementById("clerk"));
  }}
}}
document.addEventListener("click", async (e) => {{
  if (e.target.id !== "approve") return;
  e.target.disabled = true;
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
    const el = document.getElementById("error");
    el.textContent = "Authorization failed: " + err.message; el.hidden = false;
    e.target.disabled = false;
  }}
}});
</script>
</main></body></html>
"""


def authorize_html(publishable_key: str, clerk_js_url: str, client_id: str) -> str:
    return PAGE.format(pk=publishable_key, clerk_js=clerk_js_url, client_id=client_id or "An application")
