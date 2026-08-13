"""FastAPI application factory. All external dependencies are injected."""
import base64
import time
from collections.abc import Callable
from typing import Annotated
from urllib.parse import parse_qs

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
)
from fastapi.responses import Response as RawResponse
from pydantic import BaseModel, field_validator

from .auth import Authenticator
from .config import Settings
from .keys import generate_key, hash_key
from .landing import LANDING_HTML
from .model import ModelClient
from .oauth import (
    CODE_TTL_SECONDS,
    AuthCode,
    hash_code,
    new_code,
    resource_metadata,
    server_metadata,
    verify_pkce,
)
from .oauth_page import authorize_html
from .prompts import SYSTEM_PROMPT
from .seo import head_tags, json_ld, robots_txt, sitemap_xml
from .signin import clerk_js_for, signin_html
from .usage import UsageStore, current_period

PROTOCOL_VERSION = "2025-03-26"

TRANSLATE_TOOL = {
    "name": "translate",
    "description": "Rewrite Claude-English (AI-assistant writing tics) into plain, natural English while preserving meaning exactly.",
    "inputSchema": {
        "type": "object",
        "properties": {"text": {"type": "string", "description": "The text to de-Claudify."}},
        "required": ["text"],
    },
}


class TranslateRequest(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be empty")
        return v


WebhookVerifier = Callable[[bytes, str], dict]


def default_webhook_verifier(payload: bytes, sig_header: str) -> dict:
    """Verify a Stripe webhook signature using STRIPE_WEBHOOK_SECRET from the environment."""
    import json
    import os

    import stripe

    event = stripe.Webhook.construct_event(payload, sig_header, os.environ["STRIPE_WEBHOOK_SECRET"])
    # StripeObject attribute access is unreliable across versions; normalize to plain JSON types.
    return json.loads(str(event))  # StripeObject.__str__ is canonical JSON


def create_app(
    *,
    model: ModelClient,
    auth: Authenticator,
    usage: UsageStore,
    settings: Settings,
    webhook_verifier: WebhookVerifier | None = None,
) -> FastAPI:
    app = FastAPI(title="declaude", version="0.1.0")
    verify_webhook = webhook_verifier or default_webhook_verifier

    async def _resolve_api_key(key: str) -> str:
        user_id = await usage.get_user_for_key(hash_key(key))
        if user_id is None:
            raise HTTPException(401, "invalid api key")
        return user_id

    async def authenticate(request: Request) -> str:
        header = request.headers.get("Authorization", "")
        if header.startswith("Basic "):
            # curl userinfo (https://x:KEY@host) arrives as Basic base64("x:KEY")
            try:
                _, _, key = base64.b64decode(header.removeprefix("Basic ")).decode().partition(":")
            except Exception as exc:
                raise HTTPException(401, "malformed basic auth") from exc
            return await _resolve_api_key(key)
        if not header.startswith("Bearer "):
            raise HTTPException(401, "missing bearer token", headers=_www_auth(request))
        token = header.removeprefix("Bearer ")
        if token.startswith("dk_"):
            return await _resolve_api_key(token)
        try:
            return await auth.verify(token)
        except Exception as exc:
            raise HTTPException(401, "invalid token", headers=_www_auth(request)) from exc

    UserId = Annotated[str, Depends(authenticate)]

    async def authenticate_session(request: Request) -> str:
        """Clerk session JWTs only: an API key must not be able to mint another key."""
        header = request.headers.get("Authorization", "")
        if header.startswith("Basic ") or header.removeprefix("Bearer ").startswith("dk_"):
            raise HTTPException(403, "api keys cannot mint keys; sign in at /signin")
        return await authenticate(request)

    SessionUserId = Annotated[str, Depends(authenticate_session)]

    def payment_challenge() -> HTTPException:
        body = {
            "error": "payment_required",
            "message": f"Free tier of {settings.free_tier_monthly_limit} translations/month exceeded.",
            "upgrade_url": settings.public_base_url.rstrip("/") + "/upgrade",
            "accepts": [
                {
                    "scheme": "stripe-payment-link",
                    "url": settings.stripe_payment_link,
                    "price_usd_per_month": settings.price_usd_per_month,
                }
            ],
        }
        return HTTPException(402, body, headers={"X-Payment-Required": "stripe-payment-link"})

    async def check_quota(user_id: str) -> bool:
        """Gate BEFORE the model call. Returns whether the user is on the free tier."""
        if await usage.is_paid(user_id):
            return False
        if await usage.get(user_id, current_period()) >= settings.free_tier_monthly_limit:
            raise payment_challenge()
        return True

    async def record_usage(user_id: str, free_tier: bool, response: Response) -> None:
        """Record AFTER a successful translation so failures never burn quota."""
        count = await usage.increment(user_id, current_period())
        if free_tier:
            response.headers["X-RateLimit-Limit"] = str(settings.free_tier_monthly_limit)
            response.headers["X-RateLimit-Remaining"] = str(max(0, settings.free_tier_monthly_limit - count))

    async def run_translation(text: str) -> str:
        if len(text) > settings.max_input_chars:
            raise HTTPException(422, f"text exceeds {settings.max_input_chars} characters")
        try:
            return await model.complete(SYSTEM_PROMPT, text)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                503,
                {"error": "model_unavailable", "message": "model backend is unavailable or warming up; retry shortly"},
                headers={"Retry-After": "30"},
            ) from exc

    def _with_seo(html: str, *, title: str, description: str, path: str) -> str:
        extra = head_tags(settings.public_base_url, settings.ga_measurement_id,
                          title=title, description=description, path=path)
        if path == "/":
            extra += json_ld(settings.public_base_url, settings.price_usd_per_month)
        return html.replace("</head>", extra + "\n</head>", 1)

    @app.get("/", include_in_schema=False)
    async def landing() -> HTMLResponse:
        return HTMLResponse(_with_seo(
            LANDING_HTML,
            title="declaude — Claude-English to plain English",
            description="API and MCP server that rewrites Claude-English into plain, natural English. 100 free translations a month.",
            path="/",
        ))

    @app.get("/robots.txt", include_in_schema=False)
    async def robots() -> PlainTextResponse:
        return PlainTextResponse(robots_txt(settings.public_base_url))

    @app.get("/sitemap.xml", include_in_schema=False)
    async def sitemap() -> RawResponse:
        return RawResponse(content=sitemap_xml(settings.public_base_url), media_type="application/xml")

    @app.get("/upgrade", include_in_schema=False)
    async def upgrade():
        """Stable human-facing upgrade URL; 402 payloads and hook notices can always point here."""
        if settings.stripe_payment_link:
            return RedirectResponse(settings.stripe_payment_link, status_code=307)
        return HTMLResponse("<h1>declaude Pro</h1><p>Payments are not configured yet. Contact the operator.</p>")

    @app.get("/signin", include_in_schema=False)
    async def signin():
        return HTMLResponse(_with_seo(
            signin_html(settings.clerk_publishable_key),
            title="declaude — sign in and get your API key",
            description="Sign in once, mint a permanent API key for the declaude translation API and MCP server.",
            path="/signin",
        ))

    @app.post("/v1/keys")
    async def create_api_key(user_id: SessionUserId):
        """Mint a long-lived API key. The plaintext is returned once and never stored."""
        key = generate_key()
        await usage.add_api_key(hash_key(key), user_id)
        return {"key": key}

    @app.get("/healthz")
    @app.get("/health")  # /healthz is intercepted by the Google Frontend on run.app URLs
    async def healthz():
        return {"status": "ok", "model": settings.model_name}

    @app.post("/v1/translate")
    async def translate(body: TranslateRequest, user_id: UserId, response: Response):
        if len(body.text) > settings.max_input_chars:
            raise HTTPException(422, f"text exceeds {settings.max_input_chars} characters")
        free_tier = await check_quota(user_id)
        translation = await run_translation(body.text)
        await record_usage(user_id, free_tier, response)
        return {"translation": translation, "model": settings.model_name}

    # ---- Stripe billing webhook (public: Stripe signature is the auth) ----

    def _webhook_user_id(obj: dict) -> str | None:
        return (obj.get("metadata") or {}).get("clerk_user_id") or obj.get("client_reference_id")

    @app.post("/v1/billing/webhook")
    async def billing_webhook(request: Request):
        payload = await request.body()
        sig_header = request.headers.get("Stripe-Signature", "")
        try:
            event = verify_webhook(payload, sig_header)
        except Exception as exc:
            raise HTTPException(400, "invalid webhook signature") from exc

        event_type = event.get("type")
        obj = (event.get("data") or {}).get("object") or {}
        user_id = _webhook_user_id(obj)
        if event_type == "checkout.session.completed" and user_id:
            await usage.set_paid(user_id, True)
        elif event_type == "customer.subscription.deleted" and user_id:
            await usage.set_paid(user_id, False)
        return {"received": True}

    def _www_auth(request: Request) -> dict[str, str] | None:
        if request.url.path != "/mcp":
            return None
        meta = settings.public_base_url.rstrip("/") + "/.well-known/oauth-protected-resource"
        return {"WWW-Authenticate": f'Bearer resource_metadata="{meta}"'}

    # ---- OAuth 2.1 (MCP clients: discovery, DCR, PKCE) ----

    @app.get("/.well-known/oauth-protected-resource", include_in_schema=False)
    async def oauth_resource():
        return resource_metadata(settings.public_base_url)

    @app.get("/.well-known/oauth-authorization-server", include_in_schema=False)
    async def oauth_server():
        return server_metadata(settings.public_base_url)

    @app.post("/oauth/register", status_code=201)
    async def oauth_register(request: Request):
        """RFC 7591 dynamic registration. Public clients only; PKCE carries the security."""
        body = {}
        try:
            body = await request.json()
        except ValueError:
            pass
        client_id = "cli_" + new_code()[:24]
        name = str(body.get("client_name") or "")[:80]
        if name:
            await usage.put_oauth_client(client_id, name)
        return {
            "client_id": client_id,
            "client_name": name,
            "redirect_uris": body.get("redirect_uris", []),
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
        }

    @app.get("/oauth/authorize", include_in_schema=False)
    async def oauth_authorize(request: Request):
        p = request.query_params
        if p.get("code_challenge_method", "S256") != "S256" or not p.get("code_challenge"):
            raise HTTPException(400, "PKCE S256 required")
        if not p.get("redirect_uri"):
            raise HTTPException(400, "redirect_uri required")
        pk = settings.clerk_publishable_key
        name = await usage.get_oauth_client(p.get("client_id", ""))
        return HTMLResponse(authorize_html(pk, clerk_js_for(pk), name or ""))

    @app.post("/oauth/approve")
    async def oauth_approve(request: Request):
        """The signed-in browser exchanges its Clerk session for an authorization code."""
        body = await request.json()
        try:
            user_id = await auth.verify(body.get("token", ""))
        except Exception as exc:
            raise HTTPException(401, "invalid session") from exc
        if body.get("code_challenge_method") != "S256" or not body.get("code_challenge"):
            raise HTTPException(400, "PKCE S256 required")
        redirect_uri = body.get("redirect_uri") or ""
        code = new_code()
        grant = AuthCode(
            user_id=user_id,
            redirect_uri=redirect_uri,
            code_challenge=body["code_challenge"],
            expires_at=time.time() + CODE_TTL_SECONDS,
        )
        await usage.put_oauth_code(hash_code(code), grant.__dict__)
        sep = "&" if "?" in redirect_uri else "?"
        state = body.get("state") or ""
        return {"redirect_to": f"{redirect_uri}{sep}code={code}&state={state}"}

    @app.post("/oauth/token")
    async def oauth_token(request: Request):
        form = parse_qs((await request.body()).decode())
        get = lambda k: (form.get(k) or [""])[0]
        if get("grant_type") != "authorization_code":
            raise HTTPException(400, "unsupported grant_type")
        data = await usage.pop_oauth_code(hash_code(get("code")))
        if data is None:
            raise HTTPException(400, "invalid or already-used code")
        grant = AuthCode(**data)
        if grant.expired():
            raise HTTPException(400, "code expired")
        if get("redirect_uri") != grant.redirect_uri:
            raise HTTPException(400, "redirect_uri mismatch")
        if not verify_pkce(get("code_verifier"), grant.code_challenge):
            raise HTTPException(400, "PKCE verification failed")
        key = generate_key()
        await usage.add_api_key(hash_key(key), grant.user_id)
        return {"access_token": key, "token_type": "Bearer", "scope": "translate"}

    # ---- Ollama-compatible surface (claudish-to-english plugin & friends) ----

    @app.post("/api/chat")
    async def ollama_chat(request: Request, user_id: UserId, response: Response):
        body = await request.json()
        messages = body.get("messages") or []
        system = next((m.get("content", "") for m in messages if m.get("role") == "system"), SYSTEM_PROMPT)
        prompt = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
        if not prompt.strip():
            raise HTTPException(422, "no user message")
        if len(prompt) > settings.max_input_chars:
            raise HTTPException(422, f"text exceeds {settings.max_input_chars} characters")
        free_tier = await check_quota(user_id)
        try:
            content = await model.complete(system, prompt)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                503,
                {"error": "model backend is unavailable or warming up; retry shortly"},
                headers={"Retry-After": "30"},
            ) from exc
        await record_usage(user_id, free_tier, response)
        return {
            "model": settings.model_name,
            "message": {"role": "assistant", "content": content},
            "done": True,
        }

    # ---- MCP (JSON-RPC 2.0 over HTTP) ----

    def rpc_result(id, result):
        return {"jsonrpc": "2.0", "id": id, "result": result}

    def rpc_error(id, code, message):
        return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}

    @app.post("/mcp")
    async def mcp(request: Request, user_id: UserId, response: Response):
        try:
            msg = await request.json()
        except ValueError:  # malformed body -> JSON-RPC parse error
            return JSONResponse(rpc_error(None, -32700, "parse error"), status_code=400)
        method, params, msg_id = msg.get("method"), msg.get("params") or {}, msg.get("id")

        if method == "initialize":
            return rpc_result(msg_id, {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "declaude", "version": "0.1.0"},
            })
        if method == "notifications/initialized":
            return Response(status_code=202)
        if method == "tools/list":
            return rpc_result(msg_id, {"tools": [TRANSLATE_TOOL]})
        if method == "tools/call":
            name = params.get("name")
            if name != "translate":
                return JSONResponse(rpc_error(msg_id, -32602, f"unknown tool: {name}"))
            text = (params.get("arguments") or {}).get("text", "")
            if not text.strip():
                return JSONResponse(rpc_error(msg_id, -32602, "text must not be empty"))
            free_tier = await check_quota(user_id)  # raises 402 when free tier exhausted
            translation = await run_translation(text)
            await record_usage(user_id, free_tier, response)
            return rpc_result(msg_id, {"content": [{"type": "text", "text": translation}], "isError": False})
        return JSONResponse(rpc_error(msg_id, -32601, f"method not found: {method}"))

    @app.exception_handler(HTTPException)
    async def http_exc_handler(request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, dict) else {"error": exc.detail}
        return JSONResponse(detail, status_code=exc.status_code, headers=exc.headers)

    return app
