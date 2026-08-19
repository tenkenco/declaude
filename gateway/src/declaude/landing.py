"""Single-file landing page. Public, no auth, no external assets."""

LANDING_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>declaude: Claude-English to plain English</title>
<meta name="description" content="An API and MCP server that rewrites Claude-English into plain, natural English. Backed by an open-source model.">
<style>
:root{
  --bg:#0b0e14;--surface:#11151f;--raise:#161b26;--border:#1f2634;
  --text:#e6e9ef;--muted:#9aa4b2;--faint:#5b6472;
  --accent:#f97316;--accent-soft:#fdba74;--code-bg:#0d1117;--green:#4ade80;--red:#f87171;--r:12px;
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--text);
  font:16px/1.65 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  -webkit-font-smoothing:antialiased}
code,pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
main{max-width:720px;margin:0 auto;padding:0 1.25rem}
a{color:var(--accent-soft);text-decoration:none}a:hover{color:var(--accent)}

nav.top{display:flex;align-items:center;gap:1.35rem;padding:1.4rem 0;font-size:.95rem}
nav.top .logo{flex:1;font-weight:600;color:var(--muted)}
nav.top .logo b{color:var(--accent)}
nav.top a{color:var(--muted)}nav.top a:hover{color:var(--text)}

header.hero{padding:3.5rem 0 2.5rem;text-align:center}
h1{font-size:clamp(2rem,5.5vw,3rem);line-height:1.08;letter-spacing:-.03em;margin-bottom:1rem}
h1 .fade{color:var(--faint)}
.sub{color:var(--muted);font-size:1.08rem;max-width:34rem;margin:0 auto}

.demo{margin:2.5rem 0 0;border:1px solid var(--border);border-radius:var(--r);
  overflow:hidden;background:var(--surface);text-align:left}
.demo>div{padding:1.1rem 1.25rem}
.demo .before{border-bottom:1px solid var(--border)}
.demo .label{font-size:.7rem;font-weight:600;text-transform:uppercase;letter-spacing:.09em;
  margin-bottom:.45rem;color:var(--faint)}
.after .label{color:var(--green)}
.demo p{font-size:.97rem}
.demo textarea{width:100%;background:transparent;border:0;color:var(--text);font:inherit;
  font-size:.97rem;resize:vertical;outline:none}
.demo textarea::placeholder{color:var(--faint)}
.demo.hot{border-color:var(--accent)}
.demo-bar{display:flex;gap:.9rem;align-items:center;padding:.85rem 1.25rem;
  border-top:1px solid var(--border);background:var(--raise)}
.demo-bar button{background:var(--accent);color:#0b0e14;border:0;border-radius:9px;
  padding:.5rem 1.15rem;font:inherit;font-weight:600;cursor:pointer}
.demo-bar button:hover{background:var(--accent-soft)}
.demo-bar button:disabled{opacity:.5;cursor:default}

.cta-row{display:flex;gap:.8rem;justify-content:center;flex-wrap:wrap;margin-top:2rem}
.btn{display:inline-block;background:var(--accent);color:#0b0e14 !important;border-radius:10px;
  padding:.8rem 1.5rem;font-weight:600}
.btn:hover{background:var(--accent-soft);color:#0b0e14 !important}
.btn.ghost{background:transparent;color:var(--text) !important;border:1px solid var(--border)}
.btn.ghost:hover{border-color:var(--accent);color:var(--accent) !important}

section{padding:3.25rem 0;border-top:1px solid var(--border)}
h2{font-size:1.25rem;letter-spacing:-.015em;margin-bottom:1.5rem}
.ways{display:grid;gap:1.75rem;grid-template-columns:repeat(auto-fit,minmax(190px,1fr))}
.ways h3{font-size:.98rem;margin-bottom:.3rem;display:flex;align-items:center;gap:.5rem}
.ways .n{width:1.4rem;height:1.4rem;border-radius:50%;background:var(--raise);
  border:1px solid var(--border);color:var(--accent);font-size:.75rem;font-weight:700;
  display:inline-flex;align-items:center;justify-content:center}
.ways p{color:var(--muted);font-size:.9rem}
.ways code{font-size:.8rem;color:var(--accent-soft)}

pre{background:var(--code-bg);border:1px solid var(--border);border-radius:10px;
  padding:.95rem 1.15rem;overflow-x:auto;font-size:.83rem;line-height:1.6;margin:.6rem 0}
pre code{color:#d2d8e0}
.hint{color:var(--muted);font-size:.9rem}
.hint code{background:var(--code-bg);border:1px solid var(--border);border-radius:5px;
  padding:.1rem .35rem;font-size:.82em}

table.price{width:100%;border-collapse:collapse;font-size:.94rem}
table.price th,table.price td{padding:.7rem .5rem;text-align:left;border-bottom:1px solid var(--border)}
table.price th{color:var(--faint);font-weight:500;font-size:.8rem;text-transform:uppercase;
  letter-spacing:.07em}
table.price td:first-child{color:var(--muted)}
table.price .amount{font-size:1.05rem;font-weight:600;color:var(--text)}
table.price .amount small{color:var(--muted);font-weight:400;font-size:.8rem}

footer{padding:2.5rem 0 3.5rem;border-top:1px solid var(--border);color:var(--faint);font-size:.88rem}
footer nav{display:flex;gap:1.25rem;flex-wrap:wrap}
footer a{color:var(--muted)}
</style>
</head>
<body>
<main>
<nav class="top" aria-label="Main">
  <span class="logo">de<b>claude</b></span>
  <a href="/signin">Account</a>
  <a href="#use">Use it</a>
  <a href="#pricing">Pricing</a>
  <a href="https://github.com/tenkenco/declaude">GitHub</a>
</nav>

<header class="hero">
  <h1>Claude writes like this.<br><span class="fade">You don't have to read it.</span></h1>
  <p class="sub">declaude rewrites assistant-voice into plain English. Meaning, code, and
  structure survive intact.</p>

  <div class="demo" id="try">
    <div class="before"><p class="label">Before</p>
      <textarea id="demo-in" rows="3" maxlength="1200" placeholder="One thing I didn&#x27;t touch, but you won&#x27;t want to leave hanging, is the migration script. I&#x27;d be happy to walk you through it whenever you&#x27;re ready!"></textarea></div>
    <div class="after"><p class="label">After</p>
      <p id="demo-out">One thing I didn&#x27;t cover is the migration script. When you&#x27;re ready, I can go through it with you.</p></div>
    <div class="demo-bar">
      <button id="demo-go">Translate</button>
      <span id="demo-note" class="hint">No sign-in needed. Type, paste, or drop a file.</span>
    </div>
  </div>

  <div class="cta-row">
    <a class="btn" href="/signin">Get a free key</a>
    <a class="btn ghost" href="/documents">Translate a document</a>
  </div>
</header>

<section id="use">
  <h2>Three ways to use it</h2>
  <div class="ways">
    <div>
      <h3><span class="n">1</span>Claude Code plugin</h3>
      <p>Two commands install the hook. Replies render in plain English, and your transcript
      and token bill stay untouched.</p>
    </div>
    <div>
      <h3><span class="n">2</span>MCP server</h3>
      <p>Browser sign-in, no key pasting.</p>
    </div>
    <div>
      <h3><span class="n">3</span>Documents</h3>
      <p>Drop a Markdown file, get it back rewritten.</p>
    </div>
  </div>

  <pre><code>/plugin marketplace add tenkenco/declaude
/plugin install declaude@tenken
/declaude:setup</code></pre>

  <pre><code>claude mcp add --transport http declaude \\
  https://speak-english.tenken.co/mcp</code></pre>

  <pre><code>curl -X POST https://speak-english.tenken.co/v1/translate \\
  -H "Authorization: Bearer $DECLAUDE_TOKEN" \\
  -d '{"text": "Certainly! Let me delve into that."}'

{"translation": "Sure, here you go.", "model": "qwen2.5-14b-instruct"}</code></pre>
  <p class="hint">Runs on an open-source model (Qwen2.5-14B) on our own GPUs. Your text is
  processed in memory and discarded: never written to disk, a database, or logs.</p>
</section>

<section id="pricing">
  <h2>Pricing</h2>
  <table class="price">
    <thead><tr><th></th><th>Free</th><th>$5 / month</th></tr></thead>
    <tbody>
      <tr><td>Translations</td><td>100 / month</td><td>Unlimited</td></tr>
      <tr><td>Documents</td><td>5 / month, 200 KB</td><td>500 / month, 2 MB</td></tr>
      <tr><td>Card required</td><td>No</td><td>Yes</td></tr>
      <tr><td></td><td class="amount">$0</td><td class="amount">$5 <small>/ mo</small></td></tr>
    </tbody>
  </table>
  <p class="hint" style="margin-top:1.1rem">At the free limit the API returns
  <code>402</code> with a payment link. Subscribing keeps the same key.</p>
</section>

<footer>
  <nav aria-label="Footer">
    <a href="https://github.com/tenkenco/declaude">GitHub</a>
    <a href="/documents">Documents</a>
    <a href="/signin">Account</a>
    <a href="#pricing">Pricing</a>
  </nav>
  <p style="margin-top:.9rem">Built by
  <a href="https://www.tenken.co" rel="noopener">Tenken</a>. Based on
  <a href="https://github.com/gvzdv/claudish-to-english" rel="noopener">claudish-to-english</a>
  by <a href="https://github.com/gvzdv" rel="noopener">gvzdv</a>, the original local-Ollama
  hook this service grew out of.</p>
</footer>
</main>
<script>
(function () {
  const inp = document.getElementById("demo-in"), out = document.getElementById("demo-out"),
        go = document.getElementById("demo-go"), note = document.getElementById("demo-note"),
        box = document.getElementById("try");
  async function run() {
    const text = inp.value.trim() || inp.placeholder;
    go.disabled = true; out.textContent = "…";
    try {
      const r = await fetch("/v1/demo", { method: "POST",
        headers: {"Content-Type": "application/json"}, body: JSON.stringify({ text }) });
      const d = await r.json();
      if (r.status === 429) { out.textContent = d.error; note.innerHTML = 'Daily demo limit reached — <a href="/signin">get a free key</a> for 100/month.'; }
      else if (!r.ok) { out.textContent = d.error || "Something went wrong — try again."; }
      else out.textContent = d.translation;
    } catch (e) { out.textContent = "Network error — try again."; }
    go.disabled = false;
  }
  go.addEventListener("click", run);
  inp.addEventListener("keydown", (e) => { if ((e.metaKey || e.ctrlKey) && e.key === "Enter") run(); });
  ["dragover","dragenter"].forEach((ev) => box.addEventListener(ev, (e) => { e.preventDefault(); box.classList.add("hot"); }));
  ["dragleave","drop"].forEach((ev) => box.addEventListener(ev, (e) => { e.preventDefault(); box.classList.remove("hot"); }));
  box.addEventListener("drop", () => { location.href = "/documents"; });
})();
</script>
</body>
</html>
"""
