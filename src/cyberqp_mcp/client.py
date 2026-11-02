"""Thin async wrapper around CyberQP's public REST API.

One instance per request: constructed with that request's credentials,
never reused or cached across requests (SOP section 3.4). Network
robustness per SOP section 5: bounded connect/read timeouts, a limited
retry with backoff on 429/5xx only (never on other 4xx), Retry-After
honored when present, one client/connection pool reused for the whole
request.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from .errors import CyberQPApiError

_CONNECT_TIMEOUT = 5.0
_READ_TIMEOUT = 30.0
_MAX_RETRIES = 2
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _map_status_to_error(response: httpx.Response) -> CyberQPApiError:
    status = response.status_code
    if status in (400, 422):
        return CyberQPApiError(
            "invalid_argument", f"CyberQP rejected the request (HTTP {status}).", False
        )
    if status in (401, 403):
        return CyberQPApiError(
            "unauthorized", f"CyberQP rejected the credential (HTTP {status}).", False
        )
    if status == 404:
        return CyberQPApiError(
            "not_found", "The requested resource does not exist in CyberQP.", False
        )
    if status == 429:
        return CyberQPApiError("rate_limited", "CyberQP rate-limited this request.", True)
    if status >= 500:
        return CyberQPApiError(
            "upstream_error", f"CyberQP returned a server error (HTTP {status}).", True
        )
    return CyberQPApiError(
        "upstream_error", f"CyberQP returned an unexpected status (HTTP {status}).", True
    )


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    retry_after = response.headers.get("retry-after")
    if retry_after is not None:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            pass
    return min(2.0**attempt, 8.0)


class CyberQPClient:
    """Scoped to a single request's credentials. Call `aclose()` when done.

    `transport` is a test-only seam (SOP section 10: tests mock the HTTP layer,
    never hit a live CyberQP tenant) -- production code never passes it.
    """

    def __init__(
        self,
        access_token: str,
        base_url: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=httpx.Timeout(
                connect=_CONNECT_TIMEOUT,
                read=_READ_TIMEOUT,
                write=_READ_TIMEOUT,
                pool=_READ_TIMEOUT,
            ),
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        attempt = 0
        while True:
            try:
                response = await self._client.get(path, params=clean_params)
            except httpx.TimeoutException as exc:
                raise CyberQPApiError(
                    "upstream_error", "Request to CyberQP timed out.", True
                ) from exc
            except httpx.RequestError as exc:
                raise CyberQPApiError(
                    "upstream_error",
                    f"Network error calling CyberQP: {type(exc).__name__}.",
                    True,
                ) from exc

            if response.status_code < 400:
                return response.json() if response.content else {}

            if response.status_code in _RETRYABLE_STATUS and attempt < _MAX_RETRIES:
                attempt += 1
                await asyncio.sleep(_retry_delay(response, attempt))
                continue

            raise _map_status_to_error(response)
