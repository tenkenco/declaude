"""FastAPI application factory. All external dependencies are injected."""
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, field_validator

from .auth import Authenticator
from .config import Settings
from .landing import LANDING_HTML
from .model import ModelClient
from .prompts import SYSTEM_PROMPT
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

    async def authenticate(request: Request) -> str:
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            raise HTTPException(401, "missing bearer token")
        try:
            return await auth.verify(header.removeprefix("Bearer "))
        except Exception as exc:
            raise HTTPException(401, "invalid token") from exc

    UserId = Annotated[str, Depends(authenticate)]

    def payment_challenge() -> HTTPException:
        body = {
            "error": "payment_required",
            "message": f"Free tier of {settings.free_tier_monthly_limit} translations/month exceeded.",
            "accepts": [
                {
                    "scheme": "stripe-payment-link",
                    "url": settings.stripe_payment_link,
                    "price_usd_per_month": settings.price_usd_per_month,
                }
            ],
        }
        return HTTPException(402, body, headers={"X-Payment-Required": "stripe-payment-link"})

    async def meter(user_id: str, response: Response) -> None:
        """Enforce the free tier, then record usage. Paid users bypass the gate."""
        period = current_period()
        if not await usage.is_paid(user_id):
            if await usage.get(user_id, period) >= settings.free_tier_monthly_limit:
                raise payment_challenge()
            count = await usage.increment(user_id, period)
            response.headers["X-RateLimit-Limit"] = str(settings.free_tier_monthly_limit)
            response.headers["X-RateLimit-Remaining"] = str(settings.free_tier_monthly_limit - count)
        else:
            await usage.increment(user_id, period)

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

    @app.get("/", include_in_schema=False)
    async def landing() -> HTMLResponse:
        return HTMLResponse(LANDING_HTML)

    @app.get("/healthz")
    @app.get("/health")  # /healthz is intercepted by the Google Frontend on run.app URLs
    async def healthz():
        return {"status": "ok", "model": settings.model_name}

    @app.post("/v1/translate")
    async def translate(body: TranslateRequest, user_id: UserId, response: Response):
        if len(body.text) > settings.max_input_chars:
            raise HTTPException(422, f"text exceeds {settings.max_input_chars} characters")
        await meter(user_id, response)
        translation = await run_translation(body.text)
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
            await meter(user_id, response)  # raises 402 when free tier exhausted
            translation = await run_translation(text)
            return rpc_result(msg_id, {"content": [{"type": "text", "text": translation}], "isError": False})
        return JSONResponse(rpc_error(msg_id, -32601, f"method not found: {method}"))

    @app.exception_handler(HTTPException)
    async def http_exc_handler(request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, dict) else {"error": exc.detail}
        return JSONResponse(detail, status_code=exc.status_code, headers=exc.headers)

    return app
