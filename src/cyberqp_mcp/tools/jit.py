"""JIT (just-in-time) privileged access: policies, active accounts, existence
check (AC4, AC5, AC6, AC7, AC13, AC14)."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import CyberQPClient
from ..responses import clamp_limit, pick
from ._shared import READ_ONLY, call_tool, tool

_POLICY_FIELDS = ("name", "description", "active", "privilegedGroups", "durations")
_ACCOUNT_FIELDS = (
    "customerId",
    "customerName",
    "displayName",
    "username",
    "accountType",
    "userType",
    "enabled",
    "expiration",
    "reason",
    "mode",
)


def _flatten_policy(item: dict[str, Any]) -> dict[str, Any]:
    flat = {"id": item.get("_id")}
    flat.update(pick(item, _POLICY_FIELDS))
    return flat

def _flatten_account(item: dict[str, Any]) -> dict[str, Any]:
    flat = {"id": item.get("id")}
    flat.update(pick(item, _ACCOUNT_FIELDS))
    jit_policy = item.get("jitPolicy")
    if isinstance(jit_policy, dict):
        flat["jitPolicy"] = _flatten_policy(jit_policy)
    return flat

def register(mcp: FastMCP) -> None:
    @tool(mcp, annotations=READ_ONLY)
    async def cyberqp_list_jit_policies(customer_id: str, account_type: str) -> str:
        """List a customer's configured JIT (just-in-time) access policies.

        Args:
            customer_id: CyberQP customer ID (see cyberqp_list_customers).
            account_type: Directory type the policy applies to. One of AD, OFFICE, LOCAL, HYBRID.
        """

        async def handler(client: CyberQPClient) -> dict[str, Any]:
            data = await client.get(
                "/api/v1/jit-policies/account",
                params={"customerId": customer_id, "accountType": account_type},
            )
            items = [_flatten_policy(item) for item in data.get("data", [])]
            return {"data": items, "maxCount": data.get("maxCount", len(items))}

        return await call_tool(
            "cyberqp_list_jit_policies",
            {"customer_id": customer_id, "account_type": account_type},
            handler,
        )

    @tool(mcp, annotations=READ_ONLY)
    async def cyberqp_list_customer_jit_accounts(
        customer_id: str,
        search_text: str | None = None,
        limit: int = 50,
        page: int | None = None,
    ) -> str:
        """List a customer's active JIT accounts. Never includes a password or OTP field.

        Args:
            customer_id: CyberQP customer ID (see cyberqp_list_customers).
            search_text: Optional substring filter on display name or username.
            limit: Max items per page (default 50, hard cap 200).
            page: Page number; omit for the first page.
        """

        async def handler(client: CyberQPClient) -> dict[str, Any]:
            data = await client.get(
                f"/api/v1/jit/customer/{customer_id}",
                params={"searchText": search_text, "limit": clamp_limit(limit), "page": page},
            )
            items = [_flatten_account(item) for item in data.get("data", [])]
            return {"data": items, "maxCount": data.get("maxCount", len(items))}

        return await call_tool(
            "cyberqp_list_customer_jit_accounts",
            {
                "customer_id": customer_id,
                "search_text": search_text,
                "limit": limit,
                "page": page,
            },
            handler,
        )

    @tool(mcp, annotations=READ_ONLY)
    async def cyberqp_list_tenant_jit_accounts(
        search_text: str | None = None,
        limit: int = 50,
        page: int | None = None,
    ) -> str:
        """List active JIT accounts tenant-wide, across all customers. Never includes a password or OTP field.

        Args:
            search_text: Optional substring filter on display name or username.
            limit: Max items per page (default 50, hard cap 200).
            page: Page number; omit for the first page.
        """

        async def handler(client: CyberQPClient) -> dict[str, Any]:
            data = await client.get(
                "/api/v1/jit/tenant",
                params={"searchText": search_text, "limit": clamp_limit(limit), "page": page},
            )
            items = [_flatten_account(item) for item in data.get("data", [])]
            return {"data": items, "maxCount": data.get("maxCount", len(items))}

        return await call_tool(
            "cyberqp_list_tenant_jit_accounts",
            {"search_text": search_text, "limit": limit, "page": page},
            handler,
        )

    @tool(mcp, annotations=READ_ONLY)
    async def cyberqp_check_jit_account(
        customer_id: str,
        user_type: str,
        agent_id: str | None = None,
    ) -> str:
        """Check whether a JIT account currently exists for a customer and directory type.

        Args:
            customer_id: CyberQP customer ID (see cyberqp_list_customers).
            user_type: Directory type to check. One of AD, OFFICE, LOCAL.
            agent_id: Optional agent/computer ID to narrow the check to.
        """

        async def handler(client: CyberQPClient) -> dict[str, Any]:
            data = await client.get(
                f"/api/v1/jit/customer/{customer_id}/account/check",
                params={"userType": user_type, "agentId": agent_id},
            )
            return {"exists": data.get("account") is not None}

        return await call_tool(
            "cyberqp_check_jit_account",
            {"customer_id": customer_id, "user_type": user_type, "agent_id": agent_id},
            handler,
        )
