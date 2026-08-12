"""SEO assets: head tags, structured data, robots, sitemap, analytics snippet."""
import json


def head_tags(base_url: str, ga_id: str, *, title: str, description: str, path: str = "/") -> str:
    canonical = base_url.rstrip("/") + path
    og = f"""
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:site_name" content="declaude">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">"""
    ga = ""
    if ga_id:
        ga = f"""
<script async src="https://www.googletagmanager.com/gtag/js?id={ga_id}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}};gtag('js',new Date());gtag('config','{ga_id}',{{anonymize_ip:true}});</script>"""
    return og + ga


def json_ld(base_url: str, price_usd: str) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": "declaude",
        "applicationCategory": "DeveloperApplication",
        "operatingSystem": "Any",
        "url": base_url,
        "description": "API and MCP server that rewrites Claude-English into plain, natural English using an open-source model.",
        "offers": [
            {"@type": "Offer", "price": "0", "priceCurrency": "USD", "description": "100 translations per month free"},
            {"@type": "Offer", "price": price_usd, "priceCurrency": "USD", "description": "Unlimited translations, billed monthly"},
        ],
    }
    return f'<script type="application/ld+json">{json.dumps(data)}</script>'


def robots_txt(base_url: str) -> str:
    return f"""User-agent: *
Allow: /$
Allow: /signin
Disallow: /v1/
Disallow: /api/
Disallow: /mcp

Sitemap: {base_url.rstrip("/")}/sitemap.xml
"""


def sitemap_xml(base_url: str) -> str:
    b = base_url.rstrip("/")
    urls = "".join(f"<url><loc>{b}{p}</loc></url>" for p in ["/", "/signin"])
    return f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'
