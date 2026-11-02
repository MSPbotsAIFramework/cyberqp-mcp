"""Tenant/company metadata (AC10)."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import CyberQPClient
from ._shared import READ_ONLY, call_tool, tool


def register(mcp: FastMCP) -> None:
    @tool(mcp, annotations=READ_ONLY)
    async def cyberqp_get_tenant_company_data() -> str:
        """Get the CyberQP tenant's own company metadata (name, address, phone, time zone).

        Useful to confirm which CyberQP tenant the supplied credential is scoped to.
        """

        async def handler(client: CyberQPClient) -> dict[str, Any]:
            data = await client.get("/api/v1/tenants/company-data")
            return {"data": data.get("data", {})}

        return await call_tool("cyberqp_get_tenant_company_data", {}, handler)
