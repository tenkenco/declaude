"""Security headers, including a per-response CSP nonce for our inline scripts.

The account page mints and revokes credentials, so framing and script injection are the
threats worth engineering against. Inline scripts keep the no-build-step constraint, and a
nonce keeps them from requiring 'unsafe-inline'.
"""
import secrets

from starlette.datastructures import MutableHeaders

BASE_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}


# Clerk serves its bot check from Cloudflare Turnstile and keeps sessions fresh in a
# blob: worker, so both need room in the policy or sign-in renders empty.
TURNSTILE = "https://challenges.cloudflare.com"
ANALYTICS = ("https://www.googletagmanager.com https://www.google-analytics.com "
             "https://*.google-analytics.com https://*.analytics.google.com")


def csp(nonce: str, clerk_host: str = "") -> str:
    clerk = f"https://{clerk_host}" if clerk_host else "https://*.clerk.accounts.dev"
    return "; ".join([
        "default-src 'self'",
        f"script-src 'self' 'nonce-{nonce}' {clerk} {TURNSTILE} https://www.googletagmanager.com",
        f"connect-src 'self' {clerk} https://*.clerk.accounts.dev {ANALYTICS}",
        "img-src 'self' data: https:",
        # Clerk injects styles at runtime; nonces cannot reach them
        "style-src 'self' 'unsafe-inline'",
        "font-src 'self' data: https:",
        "worker-src 'self' blob:",
        f"frame-src 'self' {clerk} {TURNSTILE}",
        "frame-ancestors 'none'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self' https://buy.stripe.com",
    ])


def new_nonce() -> str:
    return secrets.token_urlsafe(16)


async def _body_of(response) -> bytes:
    if hasattr(response, "body"):
        return response.body
    chunks = [chunk async for chunk in response.body_iterator]
    return b"".join(chunks)


def install(app, clerk_host_for) -> None:
    """Attach the header middleware. `clerk_host_for` returns the Clerk host at request time."""
    from starlette.responses import Response

    @app.middleware("http")
    async def security_headers(request, call_next):
        nonce = new_nonce()
        request.state.csp_nonce = nonce
        response = await call_next(request)
        is_html = response.headers.get("content-type", "").startswith("text/html")
        if is_html:
            body = (await _body_of(response)).replace(b"<script", b'<script nonce="%s"' % nonce.encode())
            response = Response(body, status_code=response.status_code,
                                headers=dict(response.headers), media_type=response.media_type)
            response.headers["Content-Length"] = str(len(body))
        headers = MutableHeaders(scope=None, raw=response.raw_headers)
        for k, v in BASE_HEADERS.items():
            headers[k] = v
        headers["Content-Security-Policy"] = csp(nonce, clerk_host_for())
        return response
