"""Access-log coverage for the review round 1 must-fix (docs/tickets/PRD-21228-review.md):
every tool call must write one structured log line -- tool name, redacted
argument summary, upstream path/status, error code, duration -- and it must
never carry the request's credential. See docs/tickets/PRD-21228.ac.json
TC-CQP-027."""

from __future__ import annotations

import json
import logging

import httpx

from .conftest import (
    TEST_ACCESS_TOKEN,
    TEST_BASE_URL,
    call_tool_json,
    credentials_context,
    install_fake_client,
)
from .test_auth import install_mock_transport


async def test_successful_call_logs_tool_name_path_status_and_request_id(mcp, monkeypatch, caplog):
    """TC-CQP-027a."""
    install_fake_client(
        monkeypatch,
        {"/api/v1/tenants/company-data": {"data": {"name": "Acme MSP"}}},
    )

    with caplog.at_level(logging.INFO, logger="cyberqp_mcp"):
        with credentials_context():
            await call_tool_json(mcp, "cyberqp_get_tenant_company_data", {})

    assert len(caplog.records) == 1
    record = json.loads(caplog.records[0].message)
    assert record["tool"] == "cyberqp_get_tenant_company_data"
    assert record["path"] == "/api/v1/tenants/company-data"
    assert record["method"] == "GET"
    assert record["status"] == 200
    assert record["error_code"] is None
    assert isinstance(record["duration_ms"], (int, float))
    assert record["duration_ms"] >= 0
    # 32 hex chars (uuid4().hex), not merely non-empty.
    assert len(record["request_id"]) == 32
    int(record["request_id"], 16)


async def test_argument_summary_is_logged_and_long_values_truncated(mcp, monkeypatch, caplog):
    """TC-CQP-027b."""
    install_fake_client(
        monkeypatch,
        {"/api/v1/customers": {"data": [], "totalItems": 0}},
    )
    long_name = "x" * 200

    with caplog.at_level(logging.INFO, logger="cyberqp_mcp"):
        with credentials_context():
            await call_tool_json(
                mcp,
                "cyberqp_list_customers",
                {"directory_type": "AD", "name": long_name, "limit": 50},
            )

    record = json.loads(caplog.records[0].message)
    assert record["args"]["directory_type"] == "AD"
    assert "page" not in record["args"], "unset (None) filters should be dropped, not logged"
    assert len(record["args"]["name"]) < len(long_name)
    assert record["args"]["name"].endswith("...(truncated)")


async def test_failed_call_logs_error_code_and_upstream_status_without_leaking_credential(
    mcp, monkeypatch, caplog
):
    """TC-CQP-027c -- the must-fix's central claim: a PAM connector needs an audit
    trail of which tool was called, by which request, with what result."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "token belongs to internal account svc-9f2c"})

    install_mock_transport(monkeypatch, httpx.MockTransport(handler))

    with caplog.at_level(logging.INFO, logger="cyberqp_mcp"):
        with credentials_context():
            await call_tool_json(mcp, "cyberqp_get_tenant_company_data", {})

    record = json.loads(caplog.records[0].message)
    assert record["status"] == 401
    assert record["error_code"] == "unauthorized"

    full_log_text = "\n".join(r.message for r in caplog.records)
    assert TEST_ACCESS_TOKEN not in full_log_text
    assert TEST_BASE_URL not in full_log_text
    assert "svc-9f2c" not in full_log_text, "upstream response body must never reach the log"
