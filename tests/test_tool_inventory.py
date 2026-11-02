"""Static inventory check: the registered tool set is exactly the 10 approved
read-only tools, and the excluded (credential-exposing / write) endpoints are
not merely unused but structurally unreachable. See docs/tickets/PRD-21228.ac.json
(TC-CQP-023 / AC15)."""

from __future__ import annotations

import asyncio
import inspect
import pathlib

import cyberqp_mcp
from cyberqp_mcp.client import CyberQPClient
from cyberqp_mcp.server import create_mcp_server

APPROVED_TOOL_NAMES = {
    "cyberqp_list_customers",
    "cyberqp_list_customer_accounts",
    "cyberqp_get_customer_account_counts",
    "cyberqp_list_jit_policies",
    "cyberqp_list_customer_jit_accounts",
    "cyberqp_list_tenant_jit_accounts",
    "cyberqp_check_jit_account",
    "cyberqp_list_events",
    "cyberqp_list_event_types",
    "cyberqp_get_tenant_company_data",
}

# Path fragments unique to the excluded (credential-exposing or write) endpoints
# -- see docs/tickets/PRD-21228.md "Deliberately not built". None of these
# substrings collide with a path this server legitimately calls.
FORBIDDEN_PATH_SUBSTRINGS = (
    "/password",
    "/otp",
    "/install-token",
    "/installer",
    "self-serve-notification",
    "/auth/login",
    "/auth/refresh-token",
    "/auth/revoke-token",
    "/auth/notification-engine-token",
    "/auth/status",
)

# CyberQPClient only ever issues GET requests (see below); these would be the
# call sites for a write endpoint if one were ever added.
FORBIDDEN_HTTP_CALL_SITES = (".post(", ".patch(", ".delete(", ".put(")


def _production_source() -> str:
    root = pathlib.Path(cyberqp_mcp.__file__).parent
    return "\n".join(p.read_text() for p in root.rglob("*.py"))


def test_registered_tools_match_approved_read_only_set():
    mcp = create_mcp_server()
    tools = asyncio.run(mcp.list_tools())

    names = {t.name for t in tools}
    assert names == APPROVED_TOOL_NAMES, f"unexpected tool set: {names}"

    for t in tools:
        assert t.annotations is not None, f"{t.name} has no annotations"
        assert t.annotations.readOnlyHint is True, f"{t.name} is not marked readOnlyHint"
        assert not t.annotations.destructiveHint, f"{t.name} is marked destructive"

    # Structural guarantee, not just "never called": the client has no method
    # capable of issuing a write request at all.
    public_methods = {
        name for name, _ in inspect.getmembers(CyberQPClient, predicate=inspect.isfunction)
        if not name.startswith("_")
    }
    assert public_methods == {"get", "aclose"}, (
        f"CyberQPClient exposes unexpected methods: {public_methods}"
    )

    source = _production_source()
    for forbidden in FORBIDDEN_PATH_SUBSTRINGS:
        assert forbidden not in source, f"forbidden endpoint path found in source: {forbidden}"
    for call_site in FORBIDDEN_HTTP_CALL_SITES:
        assert call_site not in source, f"forbidden HTTP write call found in source: {call_site}"
