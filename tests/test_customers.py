"""Tests for tools/customers.py. See docs/tickets/PRD-21228.ac.json for the
AC -> test-case mapping (TC-CQP-001..006, TC-CQP-021)."""

from __future__ import annotations

import pytest

from .conftest import call_tool_json, credentials_context, install_fake_client
from cyberqp_mcp.errors import CyberQPApiError

pytestmark = pytest.mark.usefixtures("with_credentials")


async def test_list_customers_happy_path_no_credential_fields(mcp, monkeypatch):
    """TC-CQP-001 / AC1."""
    install_fake_client(
        monkeypatch,
        {
            "/api/v1/customers": {
                "totalItems": 2,
                "data": [
                    {
                        "type": "ADClient",
                        "id": "c1",
                        "attributes": {"guid": "guid-1", "name": "Acme Corp"},
                    },
                    {
                        "type": "ADClient",
                        "id": "c2",
                        "attributes": {"guid": "guid-2", "name": "Beta LLC"},
                    },
                ],
            }
        },
    )

    result = await call_tool_json(mcp, "cyberqp_list_customers", {"directory_type": "AD"})

    assert result["totalItems"] == 2
    assert [item["name"] for item in result["data"]] == ["Acme Corp", "Beta LLC"]
    for item in result["data"]:
        assert "password" not in item
        assert "otp" not in item
        assert "installToken" not in item


async def test_list_customers_limit_clamped_to_hard_cap(mcp, monkeypatch):
    """TC-CQP-002 / AC1."""
    created = install_fake_client(
        monkeypatch, {"/api/v1/customers": {"totalItems": 0, "data": []}}
    )

    await call_tool_json(
        mcp, "cyberqp_list_customers", {"directory_type": "AD", "limit": 500}
    )

    assert created[-1].calls[0][1]["limit"] == 200


async def test_list_customer_accounts_happy_path_no_password_field(mcp, monkeypatch):
    """TC-CQP-003 / AC2."""
    install_fake_client(
        monkeypatch,
        {
            "/api/v1/customers/c1/accounts": {
                "totalItems": 1,
                "limit": 50,
                "hasMore": False,
                "nextCursor": None,
                "data": [
                    {
                        "type": "Account",
                        "id": "a1",
                        "attributes": {
                            "displayName": "John Doe",
                            "userPrincipalName": "john.doe@acme.com",
                            "samAccountName": "john.doe",
                            "email": "john.doe@acme.com",
                            "accountType": "enduser",
                            "userType": "AD",
                            "enabled": True,
                        },
                    }
                ],
            }
        },
    )

    result = await call_tool_json(
        mcp, "cyberqp_list_customer_accounts", {"customer_id": "c1"}
    )

    assert len(result["data"]) == 1
    item = result["data"][0]
    assert item["displayName"] == "John Doe"
    assert item["accountType"] == "enduser"
    assert item["enabled"] is True
    assert "password" not in item
    assert result["hasMore"] is False


async def test_list_customer_accounts_empty_is_not_an_error(mcp, monkeypatch):
    """TC-CQP-004 / AC2, AC13."""
    install_fake_client(
        monkeypatch,
        {
            "/api/v1/customers/c1/accounts": {
                "totalItems": 0,
                "limit": 50,
                "hasMore": False,
                "nextCursor": None,
                "data": [],
            }
        },
    )

    result = await call_tool_json(
        mcp, "cyberqp_list_customer_accounts", {"customer_id": "c1"}
    )

    assert result == {"data": [], "hasMore": False, "nextCursor": None}
    assert "error" not in result


async def test_list_customer_accounts_unknown_customer_is_not_found(mcp, monkeypatch):
    """TC-CQP-005 / AC14."""
    install_fake_client(
        monkeypatch,
        {
            "/api/v1/customers/does-not-exist/accounts": CyberQPApiError(
                "not_found", "The requested resource does not exist in CyberQP.", False
            )
        },
    )

    result = await call_tool_json(
        mcp, "cyberqp_list_customer_accounts", {"customer_id": "does-not-exist"}
    )

    assert result["error"]["code"] == "not_found"
    assert result["error"]["retryable"] is False


async def test_get_customer_account_counts_happy_path(mcp, monkeypatch):
    """TC-CQP-006 / AC3."""
    install_fake_client(
        monkeypatch,
        {
            "/api/v1/customers/c1/accounts/count": {
                "data": {
                    "_id": "c1",
                    "guid": "guid-1",
                    "name": "Acme Corp",
                    "enduser": 5,
                    "admin": 4,
                    "service": 0,
                    "jit": 1,
                }
            }
        },
    )

    result = await call_tool_json(
        mcp, "cyberqp_get_customer_account_counts", {"customer_id": "c1"}
    )

    assert result["data"]["enduser"] == 5
    assert result["data"]["admin"] == 4
    assert "_id" not in result["data"]
    assert "guid" not in result["data"]


async def test_list_customers_empty_tenant_is_not_an_error(mcp, monkeypatch):
    """TC-CQP-021 / AC13."""
    install_fake_client(
        monkeypatch, {"/api/v1/customers": {"totalItems": 0, "data": []}}
    )

    result = await call_tool_json(mcp, "cyberqp_list_customers", {"directory_type": "AD"})

    assert result == {"data": [], "totalItems": 0}
    assert "error" not in result
