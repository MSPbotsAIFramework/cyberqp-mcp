"""Shared plumbing for every tool module: build a request-scoped client, run
the handler, map any CyberQPApiError to the structured error envelope.

This is the one place that turns "a tool ran" into "a JSON string result" --
every tools/*.py module calls through it instead of repeating the
try/except/finally boilerplate.
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ..auth import get_credentials
from ..client import CyberQPClient
from ..errors import CyberQPApiError, error_envelope
from ..responses import to_compact_json

ToolHandler = Callable[[CyberQPClient], Awaitable[dict[str, Any]]]

READ_ONLY = ToolAnnotations(readOnlyHint=True)


AnyCallable = Callable[..., Any]


def tool(mcp: FastMCP, **kwargs: Any) -> Callable[[AnyCallable], AnyCallable]:
    """Like @mcp.tool(), but strips the function-body indentation from the
    docstring before it becomes the tool description (SOP section 2.2 token
    economy) -- `fn.__doc__` is used by FastMCP verbatim, indentation and all.
    """

    def decorator(fn: AnyCallable) -> AnyCallable:
        doc = inspect.cleandoc(fn.__doc__ or "")
        return mcp.tool(description=doc, **kwargs)(fn)

    return decorator


async def call_tool(handler: ToolHandler) -> str:
    creds = get_credentials()
    client = CyberQPClient(access_token=creds.access_token, base_url=creds.base_url)
    try:
        payload = await handler(client)
    except CyberQPApiError as exc:
        return error_envelope(exc.code, exc.message, exc.retryable)
    finally:
        await client.aclose()
    return to_compact_json(payload)
