"""Account page: upload documents, manage API keys.

Order follows what people actually do: translate a document first, configure access second.
A freshly minted key opens in a modal because it is shown exactly once.
"""
import base64

_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>declaude: your account</title>
{seo}
<style>
:root{{--bg:#0b0e14;--surface:#11151f;--raise:#161b26;--border:#1f2634;--text:#e6e9ef;
--muted:#9aa4b2;--faint:#5b6472;--accent:#f97316;--accent-soft:#fdba74;--code:#0d1117;
--green:#4ade80;--red:#f87171;--r:12px}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);
  font:16px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  -webkit-font-smoothing:antialiased}}
code,pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}
a{{color:var(--accent-soft);text-decoration:none}}a:hover{{color:var(--accent)}}
.wrap{{max-width:680px;margin:0 auto;padding:0 1.25rem 5rem}}
nav{{display:flex;align-items:center;gap:1.25rem;padding:1.4rem 0;font-size:.95rem}}
nav .logo{{flex:1;font-weight:600;color:var(--muted)}}nav .logo b{{color:var(--accent)}}
nav a{{color:var(--muted)}}nav a:hover{{color:var(--text)}}
header{{padding:1.5rem 0 2rem}}
h1{{font-size:1.9rem;letter-spacing:-.02em;margin-bottom:.35rem}}
.sub{{color:var(--muted)}}
.who{{display:flex;align-items:center;gap:.6rem;color:var(--muted);font-size:.92rem;margin-top:.9rem}}
.dot{{width:7px;height:7px;border-radius:50%;background:var(--green)}}
section.card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);
  padding:1.5rem;margin-bottom:1.25rem}}
.card h2{{font-size:1.05rem;letter-spacing:-.01em;margin-bottom:.25rem}}
.card .lead{{color:var(--muted);font-size:.92rem;margin-bottom:1.1rem}}
#drop{{border:1.5px dashed var(--border);border-radius:10px;padding:2.4rem 1rem;text-align:center;
  cursor:pointer;color:var(--muted);transition:border-color .15s,background .15s}}
#drop:hover,#drop.hot{{border-color:var(--accent);background:#0f1420;color:var(--text)}}
#drop b{{display:block;color:var(--text);font-weight:600;margin-bottom:.2rem}}
.meta{{color:var(--faint);font-size:.82rem}}
.usage-head{{display:flex;align-items:center;gap:.75rem;margin-bottom:1.15rem}}
.usage-head h2{{flex:1;margin:0}}
.badge{{font-size:.72rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;
  padding:.22rem .55rem;border-radius:6px;background:var(--raise);border:1px solid var(--border);
  color:var(--muted)}}
.badge.pro{{background:rgba(249,115,22,.14);border-color:var(--accent);color:var(--accent)}}
.banner{{display:flex;align-items:center;gap:.7rem;background:rgba(74,222,128,.08);
  border:1px solid rgba(74,222,128,.35);border-radius:var(--r);padding:.9rem 1.1rem;
  margin-bottom:1.25rem;font-size:.94rem}}
.banner b{{color:var(--green)}}
.meter{{margin-bottom:1.1rem}}
.meter:last-of-type{{margin-bottom:0}}
.meter .top{{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:.4rem;
  font-size:.9rem}}
.meter .top span:last-child{{color:var(--muted);font-size:.85rem;font-variant-numeric:tabular-nums}}
.bar{{height:7px;border-radius:99px;background:var(--raise);overflow:hidden}}
.bar i{{display:block;height:100%;background:var(--accent);border-radius:99px;
  transition:width .35s ease;width:0}}
.bar i.warn{{background:#fbbf24}}
.bar i.full{{background:var(--red)}}
.bar.unlimited i{{width:100%;background:linear-gradient(90deg,var(--accent),var(--accent-soft));opacity:.5}}
.keylist{{display:flex;flex-direction:column;gap:.5rem;margin-bottom:1rem}}
.keyrow{{display:flex;align-items:center;gap:.75rem;background:var(--raise);
  border:1px solid var(--border);border-radius:9px;padding:.6rem .85rem}}
.keyrow code{{flex:1;font-size:.86rem;color:var(--text)}}
.keyrow .when{{color:var(--faint);font-size:.8rem}}
button{{background:var(--accent);color:#0b0e14;border:0;border-radius:9px;padding:.6rem 1.1rem;
  font:inherit;font-weight:600;cursor:pointer}}
button:hover{{background:var(--accent-soft)}}
button:disabled{{opacity:.5;cursor:default}}
button.ghost{{background:transparent;color:var(--muted);border:1px solid var(--border);font-weight:500}}
button.ghost:hover{{background:var(--raise);color:var(--text)}}
button.tiny{{padding:.32rem .7rem;font-size:.82rem}}
.row{{display:flex;gap:.6rem;flex-wrap:wrap;align-items:center}}
pre{{background:var(--code);border:1px solid var(--border);border-radius:9px;padding:.85rem 1rem;
  overflow-x:auto;font-size:.84rem;white-space:pre-wrap;word-break:break-all}}
.copyable{{position:relative}}
.copyable pre{{padding-right:3rem}}
.copybtn{{position:absolute;top:.5rem;right:.5rem;background:var(--raise);border:1px solid var(--border);
  border-radius:7px;padding:.35rem;line-height:0;cursor:pointer;color:var(--muted);transition:.15s}}
.copybtn:hover{{background:var(--surface);color:var(--text);border-color:var(--accent)}}
.copybtn svg{{width:15px;height:15px;display:block;pointer-events:none}}
.copybtn.done{{color:var(--green);border-color:var(--green)}}
dialog{{border:1px solid var(--border);border-radius:var(--r);background:var(--surface);
  color:var(--text);padding:0;max-width:540px;width:calc(100% - 2.5rem);
  /* the * reset above wipes the UA stylesheet's margin:auto, which is what centres
     a showModal() dialog - restore it explicitly */
  margin:auto;position:fixed;inset:0}}
dialog::backdrop{{background:rgba(4,6,10,.72)}}
.modal-in{{padding:1.6rem}}
dialog h2{{font-size:1.15rem;margin-bottom:.3rem}}
.warn{{color:var(--accent-soft);font-size:.88rem;margin-bottom:1rem}}
.err{{color:var(--red);font-size:.9rem}}
.ok{{color:var(--green);font-size:.9rem}}
.spin{{display:inline-block;width:.9em;height:.9em;border:2px solid var(--faint);
  border-top-color:var(--accent);border-radius:50%;animation:r .8s linear infinite;
  vertical-align:-.1em;margin-right:.45em}}
@keyframes r{{to{{transform:rotate(360deg)}}}}
[hidden]{{display:none !important}}
</style></head>
<body>
<div class="wrap">
<nav>
  <span class="logo">de<b>claude</b></span>
  <a href="/">Home</a><a href="/#pricing">Pricing</a>
  <button id="out" class="ghost tiny" hidden>Sign out</button>
</nav>

<div id="clerk"></div>

<div id="app" hidden>
  <p id="upgraded" class="banner" hidden><b>You're on Pro.</b>
  <span>Unlimited translations and 500 documents a month. Your existing keys keep working.</span></p>

  <header>
    <h1>Your account</h1>
    <p class="sub">Translate documents, or connect a client with an API key.</p>
    <p class="who"><span class="dot"></span><span id="who"></span></p>
  </header>

  <section class="card" id="usage-card">
    <div class="usage-head">
      <h2>This month</h2>
      <span id="plan" class="badge">Free</span>
      <a id="upgrade" class="badge pro" href="/upgrade" hidden style="text-decoration:none">Upgrade $5/mo</a>
      <button id="manage" class="ghost tiny" hidden>Manage</button>
    </div>
    <div class="meter">
      <div class="top"><span>Translations</span><span id="t-count">—</span></div>
      <div class="bar" id="t-bar"><i></i></div>
    </div>
    <div class="meter">
      <div class="top"><span>Documents</span><span id="d-count">—</span></div>
      <div class="bar" id="d-bar"><i></i></div>
    </div>
    <p id="u-note" class="meta" style="margin-top:1rem"></p>
  </section>

  <section class="card" id="docs-card">
    <h2>De-Claude a document</h2>
    <p class="lead">Prose is rewritten. Code blocks, headings, and tables pass through untouched.</p>
    <div id="drop">
      <b>Drop a file, or click to choose</b>
      <span class="meta">.md, .markdown, .txt, .rst</span>
    </div>
    <input id="dfile" type="file" accept=".md,.markdown,.txt,.rst" hidden>
    <p id="dbusy" hidden style="margin-top:.9rem"><span class="spin"></span>Translating <b id="dname"></b></p>
    <p id="ddone" class="ok" hidden style="margin-top:.9rem">Download started. <span id="dleft" class="meta"></span></p>
    <p id="derror" class="err" hidden style="margin-top:.9rem"></p>
  </section>

  <section class="card" id="keys-card">
    <h2>API keys</h2>
    <p class="lead">One key authenticates the Claude Code hook, an MCP client, and the REST API.
    It never expires. Deleting it cuts off anything using it.</p>
    <div id="keys" class="keylist"></div>
    <div class="row"><button id="mint">Create a key</button></div>
  </section>
</div>
</div>

<dialog id="key-modal">
  <div class="modal-in">
    <h2>Your new API key</h2>
    <p class="warn">Copy it now. It is shown once and stored only as a hash.</p>
    <div class="copyable">
      <pre id="key"></pre>
      <button class="copybtn" data-copy="key" aria-label="Copy key" title="Copy key"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button>
    </div>
    <p class="meta" style="margin-top:1.1rem">Use it in the Claude Code hook
    (or export it as <code>DECLAUDE_TOKEN</code>):</p>
    <div class="copyable">
      <pre id="cmd"></pre>
      <button class="copybtn" data-copy="cmd" aria-label="Copy hook command" title="Copy command"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button>
    </div>
    <div class="row" style="margin-top:1.1rem">
      <button id="closem">Done</button>
    </div>
  </div>
</dialog>

<script src="{clerk_js}" data-clerk-publishable-key="{pk}" crossorigin="anonymous" async
        onload="start()" onerror="failed()"></script>
<script>
const $ = (id) => document.getElementById(id);
let clerk = null;

function failed() {{
  $("clerk").innerHTML = '<p class="err">Could not load sign-in. Check your network and reload.</p>';
}}

async function start() {{
  clerk = window.Clerk;
  try {{
    await clerk.load({{appearance:{{variables:{{
      colorBackground:"#11151f",colorInputBackground:"#0d1117",colorText:"#e6e9ef",
      colorTextSecondary:"#9aa4b2",colorInputText:"#e6e9ef",colorPrimary:"#f97316",
      colorNeutral:"#e6e9ef",borderRadius:"9px"}}}}}});
  }} catch (e) {{ failed(); return; }}
  render();
  clerk.addListener(render);
}}

function render() {{
  const authed = !!clerk.user;
  if (authed && new URLSearchParams(location.search).has("upgraded")) {{
    $("upgraded").hidden = false;
    history.replaceState({{}}, "", location.pathname);  // survive a refresh without re-showing
  }}
  $("app").hidden = !authed;
  $("out").hidden = !authed;
  if (authed) {{
    $("who").textContent = clerk.user.primaryEmailAddress?.emailAddress || clerk.user.id;
    $("clerk").innerHTML = "";
    loadUsage();
    loadKeys();
  }} else {{
    clerk.mountSignIn($("clerk"), {{routing:"virtual", forceRedirectUrl: location.href}});
  }}
}}

function fmtDate(ts) {{
  if (!ts) return "";
  return new Date(ts * 1000).toLocaleDateString(undefined, {{month:"short", day:"numeric", year:"numeric"}});
}}

function meter(barId, countId, used, limit) {{
  const fill = $(barId).querySelector("i");
  if (limit === null) {{
    $(barId).classList.add("unlimited");
    $(countId).textContent = used.toLocaleString() + " used · unlimited";
    return;
  }}
  const pct = Math.min(100, Math.round((used / limit) * 100));
  fill.style.width = pct + "%";
  fill.className = pct >= 100 ? "full" : pct >= 80 ? "warn" : "";
  $(countId).textContent = used.toLocaleString() + " / " + limit.toLocaleString();
}}

async function loadUsage() {{
  try {{
    const token = await clerk.session.getToken();
    const res = await fetch("/v1/usage", {{headers:{{Authorization:"Bearer "+token}}}});
    if (!res.ok) return;
    const u = await res.json();
    const paid = u.plan === "paid";
    $("plan").textContent = paid ? "Pro" : "Free";
    $("plan").classList.toggle("pro", paid);
    $("upgrade").hidden = paid;
    if (u.upgrade_url) {{
      const email = clerk.user.primaryEmailAddress?.emailAddress;
      // Stripe Link would otherwise autofill a saved browser address, not this account
      $("upgrade").href = u.upgrade_url + (email ? "&email=" + encodeURIComponent(email) : "");
    }}
    meter("t-bar", "t-count", u.translations.used, u.translations.limit);
    meter("d-bar", "d-count", u.documents.used, u.documents.limit);
    const left = u.translations.limit === null ? null : u.translations.limit - u.translations.used;
    $("manage").hidden = !paid;
    $("u-note").textContent = paid
      ? "Unlimited translations. Documents reset on the 1st. Cancel any time from Manage."
      : (left <= 0 ? "Free translations used up. Upgrade to keep going."
                   : left + " translations left this month. Resets on the 1st.");
  }} catch (e) {{ /* best effort */ }}
}}

async function loadKeys() {{
  try {{
    const token = await clerk.session.getToken();
    const res = await fetch("/v1/keys", {{headers:{{Authorization:"Bearer "+token}}}});
    if (!res.ok) return;
    const items = (await res.json()).keys;
    $("keys").innerHTML = items.length ? items.map((k) =>
      '<div class="keyrow"><code>' + k.prefix + '</code>' +
      '<span class="when">' + (fmtDate(k.created_at) || "in use") + '</span>' +
      '<button class="ghost tiny" data-del="' + k.id + '">Delete</button></div>').join("")
      : '<p class="meta">No keys yet. Create one to use the hook, an MCP client, or the API.</p>';
  }} catch (e) {{ /* best effort */ }}
}}

async function mint() {{
  const btn = $("mint");
  btn.disabled = true;
  try {{
    const token = await clerk.session.getToken();
    const res = await fetch("/v1/keys", {{method:"POST", headers:{{Authorization:"Bearer "+token}}}});
    if (!res.ok) throw new Error("server returned " + res.status);
    const data = await res.json();
    $("key").textContent = data.key;
    $("cmd").textContent = 'export CLAUDISH_OLLAMA="https://x:' + data.key + '@{host}"';
    $("key-modal").showModal();
    loadKeys();
  }} catch (err) {{
    alert("Could not create a key: " + err.message);
  }} finally {{ btn.disabled = false; }}
}}

const CHECK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" ' +
  'stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>';

async function copyFrom(btn) {{
  const src = $(btn.dataset.copy);
  const icon = btn.innerHTML;
  try {{
    await navigator.clipboard.writeText(src.textContent);
    btn.innerHTML = CHECK; btn.classList.add("done"); btn.title = "Copied";
  }} catch (e) {{
    const r = document.createRange(); r.selectNodeContents(src);
    const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
    btn.title = "Press Cmd+C";
  }}
  setTimeout(() => {{ btn.innerHTML = icon; btn.classList.remove("done"); btn.title = "Copy"; }}, 1600);
}}

async function sendDoc(f) {{
  $("dbusy").hidden = false; $("ddone").hidden = true; $("derror").hidden = true;
  $("dname").textContent = f.name;
  try {{
    const token = await clerk.session.getToken();
    const fd = new FormData(); fd.append("file", f);
    const res = await fetch("/v1/documents", {{method:"POST",
      headers:{{Authorization:"Bearer "+token}}, body: fd}});
    if (res.status === 402) throw new Error("Monthly document limit reached. See /#pricing to upgrade.");
    if (!res.ok) throw new Error((await res.text()).slice(0, 160));
    const blob = await res.blob();
    const cd = res.headers.get("Content-Disposition") || "";
    const name = (cd.match(/filename="?([^";]+)"?/) || [null, "declauded.md"])[1];
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = name; a.click();
    URL.revokeObjectURL(a.href);
    const left = res.headers.get("X-Documents-Remaining");
    $("dleft").textContent = left !== null ? left + " left this month" : "";
    $("ddone").hidden = false;
    loadUsage();
  }} catch (err) {{
    $("derror").textContent = err.message; $("derror").hidden = false;
  }} finally {{ $("dbusy").hidden = true; $("dfile").value = ""; }}
}}

document.addEventListener("click", async (e) => {{
  const t = e.target;
  if (t.id === "mint") return mint();
  const cp = t.closest?.(".copybtn");
  if (cp) return copyFrom(cp);
  if (t.id === "closem") return $("key-modal").close();
  if (t.id === "out") return clerk.signOut();
  if (t.id === "manage") {{
    t.disabled = true;
    try {{
      const token = await clerk.session.getToken();
      const res = await fetch("/v1/billing/portal", {{method:"POST",
        headers:{{Authorization:"Bearer "+token}}}});
      if (!res.ok) throw new Error("could not open billing portal");
      location.href = (await res.json()).url;
    }} catch (err) {{ alert(err.message); t.disabled = false; }}
    return;
  }}
  if (t.id === "drop" || t.closest?.("#drop")) return $("dfile").click();
  const id = t.dataset && t.dataset.del;
  if (id) {{
    if (!confirm("Delete this key? Anything using it stops working immediately.")) return;
    const token = await clerk.session.getToken();
    await fetch("/v1/keys/" + id, {{method:"DELETE", headers:{{Authorization:"Bearer "+token}}}});
    loadKeys();
  }}
}});
document.addEventListener("change", (e) => {{
  if (e.target.id === "dfile" && e.target.files[0]) sendDoc(e.target.files[0]);
}});
["dragover","dragenter"].forEach((ev) => document.addEventListener(ev, (e) => {{
  if (e.target.closest?.("#drop")) {{ e.preventDefault(); $("drop").classList.add("hot"); }}
}}));
["dragleave","drop"].forEach((ev) => document.addEventListener(ev, (e) => {{
  if (e.target.closest?.("#drop")) {{ e.preventDefault(); $("drop").classList.remove("hot"); }}
}}));
document.addEventListener("drop", (e) => {{
  if (e.target.closest?.("#drop") && e.dataTransfer.files[0]) sendDoc(e.dataTransfer.files[0]);
}});
</script>
</body>
</html>
"""


_UNCONFIGURED = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>declaude: sign-in unavailable</title>
<style>body{background:#0b0e14;color:#e6e9ef;font:16px/1.6 ui-sans-serif,system-ui,sans-serif}
main{max-width:520px;margin:0 auto;padding:4rem 1.25rem}code{background:#0d1117;border:1px solid #1f2634;
border-radius:5px;padding:.15rem .4rem}</style></head><body><main>
<h1>Sign-in is not configured</h1>
<p>This gateway has no Clerk publishable key, so the sign-in widget cannot load.
Set <code>DECLAUDE_CLERK_PUBLISHABLE_KEY</code> (or <code>CLERK_JWKS_URL</code>, which it is
derived from) and redeploy.</p>
</main></body></html>"""


def signin_html(publishable_key: str, clerk_js_url: str = "", seo: str = "", host: str = "speak-english.tenken.co") -> str:
    if not publishable_key:
        return _UNCONFIGURED
    return _PAGE.format(pk=publishable_key, clerk_js=clerk_js_url or clerk_js_for(publishable_key),
                        seo=seo, host=host)


def publishable_key_from_jwks(jwks_url: str) -> str:
    """Derive the publishable key from the JWKS URL.

    Both values encode the same Clerk frontend host, and the JWKS URL is already set in
    production. Deriving it keeps /signin working after an image-only deploy, so the page
    never depends on a separate Terraform apply."""
    from urllib.parse import urlparse

    host = urlparse(jwks_url).hostname or ""
    if not host:
        return ""
    prefix = "pk_test_" if host.endswith(".accounts.dev") else "pk_live_"
    return prefix + base64.b64encode(f"{host}$".encode()).decode()


def clerk_js_for(publishable_key: str) -> str:
    """Derive the ClerkJS bundle URL from the publishable key.

    A publishable key is `pk_test_<base64 of "<frontend-api-host>$">`, so the host the
    bundle must be served from is recoverable without a second config value."""
    _, _, encoded = publishable_key.partition("_")
    _, _, encoded = encoded.partition("_")
    try:
        host = base64.b64decode(encoded + "==").decode().rstrip("$")
    except ValueError:  # binascii.Error and UnicodeDecodeError both subclass ValueError
        return ""
    return f"https://{host}/npm/@clerk/clerk-js@5/dist/clerk.browser.js"
