"""Tests for tools/tenant.py. See docs/tickets/PRD-21228.ac.json for the
AC -> test-case mapping (TC-CQP-017)."""

from __future__ import annotations

import pytest

from .conftest import call_tool_json, install_fake_client

pytestmark = pytest.mark.usefixtures("with_credentials")


async def test_get_tenant_company_data_happy_path(mcp, monkeypatch):
    """TC-CQP-017 / AC10."""
    install_fake_client(
        monkeypatch,
        {
            "/api/v1/tenants/company-data": {
                "data": {
                    "name": "MSPbots Demo Tenant",
                    "address": "1 Main St",
                    "city": "Austin",
                    "stateProvinceCode": "TX",
                    "zipCode": "78701",
                    "countryCode": "US",
                    "phoneNumber": "+1-512-555-0100",
                    "timeZone": "America/Chicago",
                }
            }
        },
    )

    result = await call_tool_json(mcp, "cyberqp_get_tenant_company_data", {})

    assert result["data"]["name"] == "MSPbots Demo Tenant"
    assert result["data"]["timeZone"] == "America/Chicago"
    assert "error" not in result
