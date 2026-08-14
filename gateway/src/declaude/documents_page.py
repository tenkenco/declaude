"""Document upload page: sign in, drop a file, download the de-Clauded version."""

_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>declaude: documents</title>
<style>
:root{{--bg:#0b0e14;--surface:#11151f;--border:#1f2634;--text:#e6e9ef;--muted:#9aa4b2;
--accent:#f97316;--accent-soft:#fdba74;--red:#f87171}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font:16px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
main{{max-width:640px;margin:0 auto;padding:3.5rem 1.25rem 4rem;
  display:flex;flex-direction:column;align-items:center;text-align:center}}
main>*{{width:100%}}
#clerk>div{{display:flex;justify-content:center}}
a{{color:var(--accent-soft)}}
.logo{{font-size:1.05rem;font-weight:600;color:var(--muted);margin-bottom:2rem}}.logo b{{color:var(--accent)}}
h1{{font-size:1.75rem;letter-spacing:-.02em;margin-bottom:.5rem}}
.sub{{color:var(--muted);margin-bottom:2rem}}
.card{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:1.4rem;margin-top:1.25rem;text-align:left}}
#drop{{border:2px dashed var(--border);border-radius:12px;padding:2.5rem 1rem;cursor:pointer;text-align:center;color:var(--muted)}}
#drop.hot{{border-color:var(--accent);color:var(--text)}}
button{{background:var(--accent);color:#0b0e14;border:0;border-radius:8px;padding:.65rem 1.1rem;font:inherit;font-weight:600;cursor:pointer}}
button:disabled{{opacity:.55;cursor:default}}
.hint{{color:var(--muted);font-size:.9rem}}
.err{{color:var(--red);font-size:.9rem}}
.spin{{display:inline-block;width:1em;height:1em;border:2px solid #9aa4b2;border-top-color:var(--accent);border-radius:50%;animation:r 1s linear infinite;vertical-align:-.15em;margin-right:.5em}}
@keyframes r{{to{{transform:rotate(360deg)}}}}
[hidden]{{display:none !important}}
</style></head>
<body><main>
<p class="logo">de<b>claude</b></p>
<h1>De-Claude a document</h1>
<p class="sub">Upload a Markdown or text file. Prose is rewritten in plain English.
Code blocks, headings, and tables pass through untouched.</p>
<div id="clerk"></div>
<section id="tool" class="card" hidden>
  <div id="drop">Drop a file here or click to choose<br>
    <span class="hint">.md, .markdown, .txt, .rst &middot; free: 5 docs/month up to 200&nbsp;KB &middot; paid: 500/month up to 2&nbsp;MB</span>
  </div>
  <input id="file" type="file" accept=".md,.markdown,.txt,.rst" hidden>
  <p id="busy" hidden style="margin-top:1rem"><span class="spin"></span>Translating <b id="fname"></b>&hellip;</p>
  <p id="done" hidden style="margin-top:1rem">Download started. <span id="left" class="hint"></span></p>
  <p id="error" class="err" hidden style="margin-top:1rem"></p>
</section>
<p class="hint" style="margin-top:2rem"><a href="/">&larr; speak-english.tenken.co</a></p>
<script src="{clerk_js}" data-clerk-publishable-key="{pk}" crossorigin="anonymous" async onload="start()"></script>
<script>
const $ = (id) => document.getElementById(id);
let clerk;
async function start() {{
  clerk = window.Clerk;
  await clerk.load({{appearance:{{variables:{{
    colorBackground:"#11151f",colorInputBackground:"#0d1117",colorText:"#e6e9ef",
    colorTextSecondary:"#9aa4b2",colorInputText:"#e6e9ef",colorPrimary:"#f97316",
    colorNeutral:"#e6e9ef",borderRadius:"8px"}}}}}});
  render();
  clerk.addListener(render);
}}
function render() {{
  const authed = !!clerk.user;
  $("tool").hidden = !authed;
  if (authed) {{ $("clerk").innerHTML = ""; }}
  else clerk.mountSignIn($("clerk"), {{routing:"virtual", forceRedirectUrl: location.href}});
}}
$("drop").addEventListener("click", () => $("file").click());
$("drop").addEventListener("dragover", (e) => {{ e.preventDefault(); $("drop").classList.add("hot"); }});
$("drop").addEventListener("dragleave", () => $("drop").classList.remove("hot"));
$("drop").addEventListener("drop", (e) => {{ e.preventDefault(); $("drop").classList.remove("hot");
  if (e.dataTransfer.files[0]) send(e.dataTransfer.files[0]); }});
$("file").addEventListener("change", () => {{ if ($("file").files[0]) send($("file").files[0]); }});
async function send(f) {{
  $("busy").hidden = false; $("done").hidden = true; $("error").hidden = true;
  $("fname").textContent = f.name;
  try {{
    const token = await clerk.session.getToken();
    const fd = new FormData(); fd.append("file", f);
    const res = await fetch("/v1/documents", {{method:"POST", headers:{{Authorization:"Bearer "+token}}, body:fd}});
    if (res.status === 402) {{
      const d = await res.json();
      throw new Error("Monthly document limit reached. " +
        (d.detail && d.detail.upgrade_url ? "Upgrade at " + d.detail.upgrade_url : ""));
    }}
    if (!res.ok) throw new Error((await res.text()).slice(0, 200));
    const blob = await res.blob();
    const cd = res.headers.get("Content-Disposition") || "";
    const name = (cd.match(/filename="?([^";]+)"?/) || [null, "declauded.md"])[1];
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = name; a.click();
    URL.revokeObjectURL(a.href);
    const left = res.headers.get("X-Documents-Remaining");
    $("left").textContent = left !== null ? left + " documents left this month." : "";
    $("done").hidden = false;
  }} catch (err) {{
    $("error").textContent = err.message; $("error").hidden = false;
  }} finally {{
    $("busy").hidden = true; $("file").value = "";
  }}
}}
</script>
</main></body></html>
"""


def documents_html(publishable_key: str, clerk_js_url: str) -> str:
    return _PAGE.format(pk=publishable_key, clerk_js=clerk_js_url)
