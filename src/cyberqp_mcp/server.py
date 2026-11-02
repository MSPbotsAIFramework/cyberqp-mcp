"""FastMCP app construction: mounts POST /mcp and GET /health, wires the
request-scoped credentials middleware.

Two SOP footguns this module exists to avoid (section 7):
  - lifespan must be attached to the *outer* Starlette app, or the inner
    FastMCP app's own lifespan never runs and /mcp fails with "Task group is
    not initialized" while /health still returns 200.
  - DNS-rebinding protection must be disabled, or requests arriving through
    an internal reverse proxy (Host header not localhost) get rejected with
    421.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from .auth import CredentialsMiddleware
from .tools import customers, events, jit, tenant

INSTRUCTIONS = (
    "CyberQP is a privileged access management (PAM) product: it manages privileged "
    "local-admin and service accounts, time-bound (just-in-time) elevated access, and an "
    "audit trail of privileged-access activity for an MSP's customers. This server is "
    "strictly read-only -- it cannot retrieve a password, an OTP secret, or an "
    "install/enrollment token, and it cannot create, update, enable, disable, or delete "
    "anything in CyberQP. Typical flow: cyberqp_list_customers to find a customer, then "
    "cyberqp_list_customer_accounts or cyberqp_get_customer_account_counts for its managed "
    "accounts, cyberqp_list_customer_jit_accounts or cyberqp_list_tenant_jit_accounts for "
    "currently active just-in-time access, cyberqp_list_jit_policies for the policies "
    "governing it, and cyberqp_list_events for an audit trail of who did what and when."
)


def create_mcp_server() -> FastMCP:
    mcp = FastMCP(
        "cyberqp-mcp",
        instructions=INSTRUCTIONS,
        stateless_http=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
    customers.register(mcp)
    jit.register(mcp)
    events.register(mcp)
    tenant.register(mcp)
    return mcp


async def health(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


def create_app() -> Starlette:
    mcp = create_mcp_server()
    mcp_asgi_app = mcp.streamable_http_app()

    app = Starlette(
        routes=[
            Route("/health", health, methods=["GET"]),
            Mount("/", app=mcp_asgi_app),
        ],
        lifespan=mcp_asgi_app.router.lifespan_context,
    )
    app.add_middleware(CredentialsMiddleware)
    return app
