"""Tests for auth.py (credential headers) and the upstream status mapping in
client.py, exercised through a tool call. See docs/tickets/PRD-21228.ac.json
for the AC -> test-case mapping (TC-CQP-018..020, TC-CQP-024, TC-CQP-025)."""

from __future__ import annotations

import httpx
import pytest
from starlette.testclient import TestClient

from .conftest import TEST_ACCESS_TOKEN, TEST_BASE_URL, call_tool_json, credentials_context
from cyberqp_mcp.client import CyberQPClient as RealCyberQPClient
from cyberqp_mcp.server import create_app

MCP_REQUEST_HEADERS = {"Accept": "application/json, text/event-stream"}
MCP_BODY = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}


def install_mock_transport(
    monkeypatch: pytest.MonkeyPatch, transport: httpx.AsyncBaseTransport
) -> None:
    """Wire the real CyberQPClient to a fake HTTP transport, so its status
    mapping (client.py) runs for real while no network call is made."""

    def factory(access_token: str, base_url: str) -> RealCyberQPClient:
        return RealCyberQPClient(access_token, base_url, transport=transport)

    monkeypatch.setattr("cyberqp_mcp.tools._shared.CyberQPClient", factory)


def test_missing_access_token_header_returns_401_before_upstream_call():
    """TC-CQP-018 / AC11."""
    app = create_app()
    with TestClient(app) as client:
        response = client.post(
            "/mcp",
            json=MCP_BODY,
            headers={**MCP_REQUEST_HEADERS, "X-CyberQp-Base-Url": TEST_BASE_URL},
        )

    assert response.status_code == 401
    body = response.json()
    assert "X-CyberQp-Access-Token" in body["missing_headers"]
    assert "X-CyberQp-Base-Url" not in body["missing_headers"]


def test_missing_base_url_header_named_specifically():
    """TC-CQP-019 / AC11."""
    app = create_app()
    with TestClient(app) as client:
        response = client.post(
            "/mcp",
            json=MCP_BODY,
            headers={**MCP_REQUEST_HEADERS, "X-CyberQp-Access-Token": TEST_ACCESS_TOKEN},
        )

    assert response.status_code == 401
    body = response.json()
    assert body["missing_headers"] == ["X-CyberQp-Base-Url"]


async def test_upstream_401_maps_to_unauthorized_without_leaking_body(mcp, monkeypatch):
    """TC-CQP-020 / AC12."""
    secret_body = "token belongs to internal account svc-9f2c, do not log"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": secret_body})

    install_mock_transport(monkeypatch, httpx.MockTransport(handler))

    with credentials_context():
        result = await call_tool_json(mcp, "cyberqp_get_tenant_company_data", {})

    assert result["error"]["code"] == "unauthorized"
    assert result["error"]["retryable"] is False
    assert secret_body not in result["error"]["message"]
    assert "Traceback" not in result["error"]["message"]


async def test_upstream_429_maps_to_rate_limited(mcp, monkeypatch):
    """TC-CQP-024 / AC12."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "0"}, json={"message": "slow down"})

    install_mock_transport(monkeypatch, httpx.MockTransport(handler))

    with credentials_context():
        result = await call_tool_json(mcp, "cyberqp_get_tenant_company_data", {})

    assert result["error"]["code"] == "rate_limited"
    assert result["error"]["retryable"] is True


async def test_upstream_5xx_or_timeout_maps_to_upstream_error(mcp, monkeypatch):
    """TC-CQP-025 / AC12."""

    def server_error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, headers={"Retry-After": "0"}, json={"message": "down"})

    install_mock_transport(monkeypatch, httpx.MockTransport(server_error_handler))
    with credentials_context():
        result = await call_tool_json(mcp, "cyberqp_get_tenant_company_data", {})

    assert result["error"]["code"] == "upstream_error"
    assert result["error"]["retryable"] is True

    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("connection timed out", request=request)

    install_mock_transport(monkeypatch, httpx.MockTransport(timeout_handler))
    with credentials_context():
        result = await call_tool_json(mcp, "cyberqp_get_tenant_company_data", {})

    assert result["error"]["code"] == "upstream_error"
    assert result["error"]["retryable"] is True
