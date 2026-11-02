"""Tests for tools/events.py. See docs/tickets/PRD-21228.ac.json for the
AC -> test-case mapping (TC-CQP-013..016)."""

from __future__ import annotations

import pytest

from .conftest import call_tool_json, install_fake_client

pytestmark = pytest.mark.usefixtures("with_credentials")


async def test_list_events_happy_path_with_filters(mcp, monkeypatch):
    """TC-CQP-013 / AC8."""
    created = install_fake_client(
        monkeypatch,
        {
            "/api/v1/event": {
                "totalItems": 1,
                "limit": 50,
                "hasMore": False,
                "nextCursor": None,
                "data": [
                    {
                        "type": "Event",
                        "id": "e1",
                        "attributes": {
                            "customerId": "c1",
                            "customerName": "Acme Corp",
                            "accountId": "a1",
                            "technicianId": "t1",
                            "technicianName": "Jane Doe",
                            "technicianEmail": "jane.doe@mspbots.ai",
                            "eventType": "ACCOUNT-MANAGEMENT-ADMINISTRATOR",
                            "status": "Success",
                            "title": "Password Accessed",
                            "details": "Password was accessed for admin@acme.com",
                            "source": "admin@acme.com",
                            "accountType": "Active Directory",
                            "createdAt": "2026-01-15T18:30:00.000Z",
                        },
                    }
                ],
            }
        },
    )

    result = await call_tool_json(
        mcp,
        "cyberqp_list_events",
        {
            "customer_id": "c1",
            "event_type": "ACCOUNT-MANAGEMENT-ADMINISTRATOR",
            "start_date": "2026-01-01T00:00:00.000Z",
            "end_date": "2026-01-31T23:59:59.999Z",
        },
    )

    item = result["data"][0]
    assert item["technicianName"] == "Jane Doe"
    assert item["eventType"] == "ACCOUNT-MANAGEMENT-ADMINISTRATOR"
    assert item["status"] == "Success"
    assert item["title"] == "Password Accessed"
    call_params = created[-1].calls[0][1]
    assert call_params["customerId"] == "c1"
    assert call_params["startDate"] == "2026-01-01T00:00:00.000Z"


async def test_list_events_empty_is_not_an_error(mcp, monkeypatch):
    """TC-CQP-014 / AC8, AC13."""
    install_fake_client(
        monkeypatch,
        {
            "/api/v1/event": {
                "totalItems": 0,
                "limit": 50,
                "hasMore": False,
                "nextCursor": None,
                "data": [],
            }
        },
    )

    result = await call_tool_json(
        mcp, "cyberqp_list_events", {"customer_id": "c1", "event_type": "BILLING"}
    )

    assert result["data"] == []
    assert "error" not in result


async def test_list_events_limit_clamped_to_hard_cap(mcp, monkeypatch):
    """TC-CQP-015 / AC8."""
    created = install_fake_client(
        monkeypatch,
        {
            "/api/v1/event": {
                "totalItems": 0,
                "limit": 200,
                "hasMore": False,
                "nextCursor": None,
                "data": [],
            }
        },
    )

    await call_tool_json(mcp, "cyberqp_list_events", {"limit": 500})

    assert created[-1].calls[0][1]["limit"] == 200


async def test_list_event_types_happy_path(mcp, monkeypatch):
    """TC-CQP-016 / AC9."""
    install_fake_client(
        monkeypatch,
        {
            "/api/v1/event/types": {
                "totalItems": 3,
                "data": ["SELF-SERVE", "BILLING", "SECURITY-EVENTS"],
            }
        },
    )

    result = await call_tool_json(mcp, "cyberqp_list_event_types", {})

    assert result["totalItems"] == 3
    assert "BILLING" in result["data"]
