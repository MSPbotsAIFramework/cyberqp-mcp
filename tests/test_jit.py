"""Tests for tools/jit.py. See docs/tickets/PRD-21228.ac.json for the
AC -> test-case mapping (TC-CQP-007..012, TC-CQP-022)."""

from __future__ import annotations

import pytest

from .conftest import call_tool_json, install_fake_client
from cyberqp_mcp.errors import CyberQPApiError

pytestmark = pytest.mark.usefixtures("with_credentials")


async def test_list_jit_policies_happy_path_no_credential_fields(mcp, monkeypatch):
    """TC-CQP-007 / AC4."""
    install_fake_client(
        monkeypatch,
        {
            "/api/v1/jit-policies/account": {
                "maxCount": 1,
                "data": [
                    {
                        "_id": "p1",
                        "name": "Standard elevation",
                        "description": "30 minute elevation for AD accounts",
                        "adminId": "admin-1",
                        "active": True,
                        "privilegedGroups": ["Domain Admins"],
                        "directoryType": "AD",
                        "isLoginGroupRestricted": False,
                        "durations": ["PT30M", "PT1H"],
                        "createdAt": "2026-01-01T00:00:00.000Z",
                    }
                ],
            }
        },
    )

    result = await call_tool_json(
        mcp, "cyberqp_list_jit_policies", {"customer_id": "c1", "account_type": "AD"}
    )

    assert result["maxCount"] == 1
    policy = result["data"][0]
    assert policy == {
        "id": "p1",
        "name": "Standard elevation",
        "description": "30 minute elevation for AD accounts",
        "active": True,
        "privilegedGroups": ["Domain Admins"],
        "durations": ["PT30M", "PT1H"],
    }


async def test_list_customer_jit_accounts_happy_path_no_credential_fields(mcp, monkeypatch):
    """TC-CQP-008 / AC5."""
    policy = {
        "_id": "p1",
        "name": "Standard elevation",
        "active": True,
        "privilegedGroups": ["Domain Admins"],
        "durations": ["PT30M"],
    }
    install_fake_client(
        monkeypatch,
        {
            "/api/v1/jit/customer/c1": {
                "maxCount": 1,
                "data": [
                    {
                        "customerId": "c1",
                        "customerName": "Acme Corp",
                        "id": "jit-1",
                        "displayName": "Jane Doe",
                        "username": "jane.doe",
                        "userType": "AD",
                        "accountType": "admin",
                        "enabled": True,
                        "computerName": "WIN-01",
                        "expiration": "2026-01-01T01:00:00.000Z",
                        "reason": "Server maintenance",
                        "jitPolicy": policy,
                        "domainName": "acme.local",
                        "mode": "STANDARD",
                    }
                ],
            }
        },
    )

    result = await call_tool_json(
        mcp, "cyberqp_list_customer_jit_accounts", {"customer_id": "c1"}
    )

    item = result["data"][0]
    assert item["enabled"] is True
    assert item["expiration"] == "2026-01-01T01:00:00.000Z"
    assert item["jitPolicy"]["name"] == "Standard elevation"
    assert "password" not in item
    assert "otp" not in item


async def test_list_customer_jit_accounts_empty_is_not_an_error(mcp, monkeypatch):
    """TC-CQP-009 / AC5, AC13."""
    install_fake_client(monkeypatch, {"/api/v1/jit/customer/c1": {"maxCount": 0, "data": []}})

    result = await call_tool_json(
        mcp, "cyberqp_list_customer_jit_accounts", {"customer_id": "c1"}
    )

    assert result == {"data": [], "maxCount": 0}
    assert "error" not in result


async def test_list_tenant_jit_accounts_happy_path(mcp, monkeypatch):
    """TC-CQP-010 / AC6."""
    install_fake_client(
        monkeypatch,
        {
            "/api/v1/jit/tenant": {
                "maxCount": 2,
                "data": [
                    {
                        "customerId": "c1",
                        "customerName": "Acme Corp",
                        "id": "jit-1",
                        "displayName": "Jane Doe",
                        "username": "jane.doe",
                        "userType": "AD",
                        "accountType": "admin",
                        "enabled": True,
                        "computerName": "WIN-01",
                        "expiration": None,
                        "reason": "",
                        "jitPolicy": {"_id": "p1", "name": "Standard", "active": True},
                        "domainName": "acme.local",
                    },
                    {
                        "customerId": "c2",
                        "customerName": "Beta LLC",
                        "id": "jit-2",
                        "displayName": "Max Mustermann",
                        "username": "max",
                        "userType": "OFFICE",
                        "accountType": "service",
                        "enabled": False,
                        "computerName": "WIN-02",
                        "expiration": None,
                        "reason": "",
                        "jitPolicy": {"_id": "p2", "name": "Service", "active": False},
                        "domainName": "beta.local",
                    },
                ],
            }
        },
    )

    result = await call_tool_json(mcp, "cyberqp_list_tenant_jit_accounts", {})

    assert {item["customerId"] for item in result["data"]} == {"c1", "c2"}
    assert result["maxCount"] == 2


async def test_check_jit_account_exists_true(mcp, monkeypatch):
    """TC-CQP-011 / AC7."""
    install_fake_client(
        monkeypatch,
        {
            "/api/v1/jit/customer/c1/account/check": {
                "account": {
                    "customerId": "c1",
                    "customerName": "Acme Corp",
                    "id": "jit-1",
                    "displayName": "Jane Doe",
                    "username": "jane.doe",
                    "userType": "AD",
                    "accountType": "admin",
                    "enabled": True,
                    "computerName": "WIN-01",
                    "expiration": "2026-01-01T01:00:00.000Z",
                    "reason": "On call",
                    "jitPolicy": {"_id": "p1"},
                    "domainName": "acme.local",
                }
            }
        },
    )

    result = await call_tool_json(
        mcp, "cyberqp_check_jit_account", {"customer_id": "c1", "user_type": "AD"}
    )

    assert result == {"exists": True}


async def test_check_jit_account_exists_false(mcp, monkeypatch):
    """TC-CQP-012 / AC7."""
    install_fake_client(
        monkeypatch, {"/api/v1/jit/customer/c1/account/check": {"account": None}}
    )

    result = await call_tool_json(
        mcp, "cyberqp_check_jit_account", {"customer_id": "c1", "user_type": "AD"}
    )

    assert result == {"exists": False}
    assert "error" not in result


async def test_list_jit_policies_unknown_customer_is_not_found(mcp, monkeypatch):
    """TC-CQP-022 / AC14."""
    install_fake_client(
        monkeypatch,
        {
            "/api/v1/jit-policies/account": CyberQPApiError(
                "not_found", "The requested resource does not exist in CyberQP.", False
            )
        },
    )

    result = await call_tool_json(
        mcp,
        "cyberqp_list_jit_policies",
        {"customer_id": "does-not-exist", "account_type": "AD"},
    )

    assert result["error"]["code"] == "not_found"
