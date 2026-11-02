"""Customers and their managed accounts (AC1, AC2, AC3, AC13, AC14)."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import CyberQPClient
from ..responses import clamp_limit, pick
from ._shared import READ_ONLY, call_tool, tool

_CUSTOMER_FIELDS = ("id", "type", "guid", "name")
_ACCOUNT_FIELDS = (
    "id",
    "displayName",
    "userPrincipalName",
    "samAccountName",
    "email",
    "accountType",
    "userType",
    "enabled",
)


def _flatten(item: dict[str, Any]) -> dict[str, Any]:
    """CyberQP returns JSON:API-ish `{type, id, attributes: {...}}` records."""
    flat = {"id": item.get("id"), "type": item.get("type")}
    flat.update(item.get("attributes", {}))
    return flat

def register(mcp: FastMCP) -> None:
    @tool(mcp, annotations=READ_ONLY)
    async def cyberqp_list_customers(
        directory_type: str,
        name: str | None = None,
        limit: int = 50,
        page: int | None = None,
    ) -> str:
        """List the tenant's CyberQP customers/clients.

        Args:
            directory_type: Directory type filter. One of AD, OFFICE, LOCAL.
            name: Optional substring filter on the customer's display name.
            limit: Max items per page (default 50, hard cap 200).
            page: Page number; omit for the first page.
        """

        async def handler(client: CyberQPClient) -> dict[str, Any]:
            data = await client.get(
                "/api/v1/customers",
                params={
                    "directoryType": directory_type,
                    "name": name,
                    "limit": clamp_limit(limit),
                    "page": page,
                },
            )
            items = [pick(_flatten(item), _CUSTOMER_FIELDS) for item in data.get("data", [])]
            return {"data": items, "totalItems": data.get("totalItems", len(items))}

        return await call_tool(handler)

    @tool(mcp, annotations=READ_ONLY)
    async def cyberqp_list_customer_accounts(
        customer_id: str,
        account_type: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> str:
        """List a customer's managed (privileged) accounts. No password field is ever returned.

        Args:
            customer_id: CyberQP customer ID (see cyberqp_list_customers).
            account_type: Optional filter. One of enduser, admin, service, jit.
            limit: Max items per page (default 50, hard cap 200).
            cursor: Opaque pagination cursor from a previous call's nextCursor.
        """

        async def handler(client: CyberQPClient) -> dict[str, Any]:
            data = await client.get(
                f"/api/v1/customers/{customer_id}/accounts",
                params={
                    "accountType": account_type,
                    "limit": clamp_limit(limit),
                    "cursor": cursor,
                },
            )
            items = [pick(_flatten(item), _ACCOUNT_FIELDS) for item in data.get("data", [])]
            return {
                "data": items,
                "hasMore": data.get("hasMore", False),
                "nextCursor": data.get("nextCursor"),
            }

        return await call_tool(handler)

    @tool(mcp, annotations=READ_ONLY)
    async def cyberqp_get_customer_account_counts(customer_id: str) -> str:
        """Get a customer's managed account counts broken down by account type.

        Args:
            customer_id: CyberQP customer ID (see cyberqp_list_customers).
        """

        async def handler(client: CyberQPClient) -> dict[str, Any]:
            data = await client.get(f"/api/v1/customers/{customer_id}/accounts/count")
            counts = dict(data.get("data", {}))
            counts.pop("_id", None)
            counts.pop("guid", None)
            return {"data": counts}

        return await call_tool(handler)
