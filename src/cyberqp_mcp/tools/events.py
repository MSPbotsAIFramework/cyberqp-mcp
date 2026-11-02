"""Audit/event log of privileged-access activity (AC8, AC9, AC13)."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import CyberQPClient
from ..responses import clamp_limit, pick
from ._shared import READ_ONLY, call_tool, tool

_EVENT_FIELDS = (
    "customerId",
    "customerName",
    "accountId",
    "technicianId",
    "technicianName",
    "technicianEmail",
    "eventType",
    "status",
    "title",
    "details",
    "source",
    "accountType",
    "createdAt",
)


def _flatten_event(item: dict[str, Any]) -> dict[str, Any]:
    flat = {"id": item.get("id")}
    flat.update(pick(item.get("attributes", {}), _EVENT_FIELDS))
    return flat

def register(mcp: FastMCP) -> None:
    @tool(mcp, annotations=READ_ONLY)
    async def cyberqp_list_events(
        customer_id: str | None = None,
        account_id: str | None = None,
        event_type: str | None = None,
        status: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> str:
        """List audit events: who did what, when, and the result. All filters are optional.

        Args:
            customer_id: CyberQP customer ID.
            account_id: Account ID.
            event_type: Event type (see cyberqp_list_event_types).
            status: One of Success, Failed.
            start_date: ISO 8601 range start (inclusive).
            end_date: ISO 8601 range end (inclusive).
            limit: Max items per page (default 50, hard cap 200).
            cursor: Pagination cursor from a previous call's nextCursor.
        """

        async def handler(client: CyberQPClient) -> dict[str, Any]:
            data = await client.get(
                "/api/v1/event",
                params={
                    "customerId": customer_id,
                    "accountId": account_id,
                    "eventType": event_type,
                    "status": status,
                    "startDate": start_date,
                    "endDate": end_date,
                    "limit": clamp_limit(limit),
                    "cursor": cursor,
                },
            )
            items = [_flatten_event(item) for item in data.get("data", [])]
            return {
                "data": items,
                "hasMore": data.get("hasMore", False),
                "nextCursor": data.get("nextCursor"),
            }

        return await call_tool(
            "cyberqp_list_events",
            {
                "customer_id": customer_id,
                "account_id": account_id,
                "event_type": event_type,
                "status": status,
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit,
                "cursor": cursor,
            },
            handler,
        )

    @tool(mcp, annotations=READ_ONLY)
    async def cyberqp_list_event_types() -> str:
        """List the reference event-type codes usable as the event_type filter in cyberqp_list_events."""

        async def handler(client: CyberQPClient) -> dict[str, Any]:
            data = await client.get("/api/v1/event/types")
            items = list(data.get("data", []))
            return {"data": items, "totalItems": data.get("totalItems", len(items))}

        return await call_tool("cyberqp_list_event_types", {}, handler)
