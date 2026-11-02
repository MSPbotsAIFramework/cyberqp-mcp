"""Shared test fixtures.

Per SOP section 10, all tests mock the CyberQP HTTP layer -- no live tenant is
reachable from the dev or CI flow. Two test doubles are provided:

- `install_fake_client`: swaps `CyberQPClient` for a canned-response stub, used
  by the per-tool test modules to assert field trimming, clamping, and
  pagination plumbing without exercising real HTTP status mapping.
- `httpx.MockTransport` (used directly in tests/test_auth.py): exercises the
  real `CyberQPClient` against a fake HTTP transport, to test the actual
  status -> error-code mapping in client.py.
"""

from __future__ import annotations

import contextlib
import json
from collections.abc import Iterator
from typing import Any

import pytest

from cyberqp_mcp.auth import CyberQPCredentials, _credentials
from cyberqp_mcp.server import create_mcp_server

TEST_ACCESS_TOKEN = "test-access-token"
TEST_BASE_URL = "https://ca.cyberqp.com"


@pytest.fixture
def mcp():
    return create_mcp_server()


@contextlib.contextmanager
def credentials_context(
    access_token: str = TEST_ACCESS_TOKEN, base_url: str = TEST_BASE_URL
) -> Iterator[None]:
    token = _credentials.set(CyberQPCredentials(access_token=access_token, base_url=base_url))
    try:
        yield
    finally:
        _credentials.reset(token)


@pytest.fixture
def with_credentials() -> Iterator[None]:
    with credentials_context():
        yield


class FakeCyberQPClient:
    """Test double matching CyberQPClient's `get`/`aclose` surface.

    `responses[path]` is either a dict (returned as-is) or an Exception
    instance (raised) -- lets a test simulate the already-mapped
    CyberQPApiError a real CyberQPClient.get() would raise.
    """

    def __init__(self, access_token: str, base_url: str, *, responses: dict[str, Any]) -> None:
        self.access_token = access_token
        self.base_url = base_url
        self._responses = responses
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.calls.append((path, dict(params or {})))
        outcome = self._responses[path]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    async def aclose(self) -> None:
        pass


def install_fake_client(
    monkeypatch: pytest.MonkeyPatch, responses: dict[str, Any]
) -> list[FakeCyberQPClient]:
    """Patch cyberqp_mcp.tools._shared.CyberQPClient; returns the list of instances created."""
    created: list[FakeCyberQPClient] = []

    def factory(access_token: str, base_url: str) -> FakeCyberQPClient:
        client = FakeCyberQPClient(access_token, base_url, responses=responses)
        created.append(client)
        return client

    monkeypatch.setattr("cyberqp_mcp.tools._shared.CyberQPClient", factory)
    return created


async def call_tool_json(mcp, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Invoke a registered tool and parse its (JSON-string) text content."""
    blocks, _ = await mcp.call_tool(name, arguments)
    return json.loads(blocks[0].text)
