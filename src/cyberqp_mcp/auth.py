"""Request-scoped credential extraction (SOP section 3).

Three hard rules this module exists to enforce:
  1. Credentials come only from HTTP headers -- never an env var fallback.
  2. Each request gets its own isolated credential value (ContextVar, reset in
     a finally block) -- no global or module-level storage.
  3. Nothing here is cached across requests.
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

ACCESS_TOKEN_HEADER = "x-cyberqp-access-token"
BASE_URL_HEADER = "x-cyberqp-base-url"

ACCESS_TOKEN_HEADER_DISPLAY = "X-CyberQp-Access-Token"
BASE_URL_HEADER_DISPLAY = "X-CyberQp-Base-Url"

# /health is a pure local liveness probe (SOP section 1.1) -- it must not require
# vendor credentials or depend on CyberQP being reachable.
_PATHS_WITHOUT_CREDENTIALS = {"/health"}


@dataclass(frozen=True)
class CyberQPCredentials:
    access_token: str
    base_url: str


_credentials: contextvars.ContextVar[CyberQPCredentials | None] = contextvars.ContextVar(
    "cyberqp_credentials", default=None
)


def get_credentials() -> CyberQPCredentials:
    """Read this request's credentials.

    Only ever called from inside a tool invocation, which only happens after
    CredentialsMiddleware has confirmed both headers are present -- so a miss
    here means the middleware was bypassed, not that the headers were missing.
    """
    creds = _credentials.get()
    if creds is None:
        raise RuntimeError(
            "No CyberQP credentials in request context. CredentialsMiddleware "
            "should have returned 401 before any tool could run."
        )
    return creds


class CredentialsMiddleware:
    """Reads per-tenant credentials from headers into a ContextVar for this request only."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") in _PATHS_WITHOUT_CREDENTIALS:
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        access_token = headers.get(ACCESS_TOKEN_HEADER)
        base_url = headers.get(BASE_URL_HEADER)

        missing: list[str] = []
        if not access_token:
            missing.append(ACCESS_TOKEN_HEADER_DISPLAY)
        if not base_url:
            missing.append(BASE_URL_HEADER_DISPLAY)

        if missing:
            response = JSONResponse(
                {
                    "error": {
                        "code": "unauthorized",
                        "message": "Missing required header(s): " + ", ".join(missing),
                        "retryable": False,
                    },
                    "missing_headers": missing,
                },
                status_code=401,
            )
            await response(scope, receive, send)
            return

        # Both are non-None here -- the missing-header branch above returned otherwise.
        assert access_token is not None
        assert base_url is not None

        token = _credentials.set(
            CyberQPCredentials(access_token=access_token, base_url=base_url.rstrip("/"))
        )
        try:
            await self.app(scope, receive, send)
        finally:
            _credentials.reset(token)
