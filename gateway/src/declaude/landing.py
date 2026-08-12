"""Single-file landing page. Public, no auth, no external assets."""

LANDING_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>declaude — Claude-English to plain English</title>
<meta name="description" content="An API and MCP server that rewrites Claude-English into plain, natural English. Backed by an open-source model.">
<style>
:root{
  --bg:#0b0e14;--surface:#11151f;--border:#1f2634;
  --text:#e6e9ef;--muted:#9aa4b2;--accent:#f97316;--accent-soft:#fdba74;
  --code-bg:#0d1117;--green:#4ade80;--red:#f87171;
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{
  background:var(--bg);color:var(--text);
  font:16px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  -webkit-font-smoothing:antialiased;
}
code,pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
main{max-width:760px;margin:0 auto;padding:0 1.25rem}
a{color:var(--accent-soft)}
a:hover{color:var(--accent)}
header.hero{padding:5rem 0 3rem;text-align:left}
.logo{font-size:1.05rem;font-weight:600;letter-spacing:.02em;color:var(--muted);margin-bottom:2.5rem}
.logo b{color:var(--accent)}
h1{font-size:clamp(1.9rem,5vw,2.75rem);line-height:1.15;letter-spacing:-.02em;margin-bottom:1rem}
.sub{color:var(--muted);font-size:1.125rem;max-width:36rem}
.demo{margin:2.5rem 0 0;border:1px solid var(--border);border-radius:12px;overflow:hidden;background:var(--surface)}
.demo>div{padding:1rem 1.25rem}
.demo .before{border-bottom:1px solid var(--border)}
.demo .label{font-size:.72rem;font-weight:600;text-transform:uppercase;letter-spacing:.08em;margin-bottom:.35rem}
.before .label{color:var(--red)}
.after .label{color:var(--green)}
.demo p{color:var(--text);font-size:.95rem}
section{padding:2.5rem 0;border-top:1px solid var(--border)}
h2{font-size:1.35rem;letter-spacing:-.01em;margin-bottom:.35rem}
.lead{color:var(--muted);margin-bottom:1.25rem}
pre{
  background:var(--code-bg);border:1px solid var(--border);border-radius:10px;
  padding:1rem 1.25rem;overflow-x:auto;font-size:.85rem;line-height:1.55;margin:.75rem 0;
}
pre code{color:#d2d8e0}
.hint{color:var(--muted);font-size:.9rem}
.hint code{background:var(--code-bg);border:1px solid var(--border);border-radius:5px;padding:.1rem .35rem;font-size:.82em}
ul.pricing{list-style:none;display:grid;gap:1rem;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));margin-top:1.25rem}
ul.pricing li{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:1.4rem}
ul.pricing .tier{font-weight:600;margin-bottom:.25rem}
ul.pricing .price{font-size:1.6rem;font-weight:700;margin-bottom:.5rem}
ul.pricing .price small{font-size:.9rem;font-weight:400;color:var(--muted)}
ul.pricing p{color:var(--muted);font-size:.92rem}
footer{border-top:1px solid var(--border);padding:2rem 0 3rem;color:var(--muted);font-size:.9rem}
footer nav{display:flex;gap:1.5rem;flex-wrap:wrap}
</style>
</head>
<body>
<main>
<header class="hero">
  <p class="logo">de<b>claude</b></p>
  <h1>Turn Claude-English into plain English.</h1>
  <p class="sub">declaude is a translation API and MCP server that strips AI-assistant
  writing tics — em-dash pileups, hollow superlatives, "delve", "certainly!" — while
  preserving meaning exactly. Backed by an open-source model (Qwen2.5-14B on dedicated GPUs) on GCP.</p>
  <div class="demo" role="figure" aria-label="Before and after example">
    <div class="before"><p class="label">Before</p>
      <p>Certainly! I'd be delighted to delve into this fascinating topic — it's a
      testament to the rich tapestry of modern software engineering.</p></div>
    <div class="after"><p class="label">After</p>
      <p>Sure. Here's an overview of the topic.</p></div>
  </div>
</header>

<section id="mcp">
  <h2>Quickstart: MCP</h2>
  <p class="lead">Add declaude to any MCP client over HTTP. The tool <code>translate</code> is exposed at <code>/mcp</code>.</p>
  <pre><code>claude mcp add --transport http declaude \\
  https://declaude-gateway-477468296053.us-central1.run.app/mcp \\
  --header "Authorization: Bearer &lt;clerk session token&gt;"</code></pre>
  <p class="hint">Authenticate with a Clerk session token in the
  <code>Authorization: Bearer</code> header.</p>
</section>

<section id="api">
  <h2>Quickstart: REST API</h2>
  <p class="lead">One endpoint: <code>POST /v1/translate</code>. Send text, get plain English back.</p>
  <pre><code>curl -X POST https://declaude-gateway-477468296053.us-central1.run.app/v1/translate \\
  -H "Authorization: Bearer &lt;clerk session token&gt;" \\
  -H "Content-Type: application/json" \\
  -d '{"text": "Certainly! Let me delve into that."}'

{"translation": "Sure, here you go.", "model": "qwen2.5-32b-instruct"}</code></pre>
</section>

<section id="pricing">
  <h2>Pricing</h2>
  <p class="lead">Start free. Upgrade when you hit the limit — the API tells you how.</p>
  <ul class="pricing">
    <li>
      <p class="tier">Free</p>
      <p class="price">$0 <small>/ month</small></p>
      <p>100 translations per month. No card required.
      Remaining quota reported via <code>X-RateLimit-Remaining</code>.</p>
    </li>
    <li>
      <p class="tier">Unlimited</p>
      <p class="price">$5 <small>/ month</small></p>
      <p>Unlimited translations via Stripe. When the free tier runs out, the API
      responds <code>402 Payment Required</code> with a Stripe payment link — pay
      once and keep the same token.</p>
    </li>
  </ul>
</section>

<footer>
  <nav aria-label="Footer">
    <a href="https://github.com/tenkenco/declaude">github.com/tenkenco/declaude</a>
    <a href="#mcp">MCP quickstart</a>
    <a href="#api">API</a>
    <a href="#pricing">Pricing</a>
  </nav>
</footer>
</main>
</body>
</html>
"""
