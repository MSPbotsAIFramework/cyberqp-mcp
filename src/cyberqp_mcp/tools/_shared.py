"""Shared plumbing for every tool module: build a request-scoped client, run
the handler, map any CyberQPApiError to the structured error envelope.

This is the one place that turns "a tool ran" into "a JSON string result" --
every tools/*.py module calls through it instead of repeating the
try/except/finally boilerplate.
"""

from __future__ import annotations

import inspect
import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ..auth import get_credentials
from ..client import CyberQPClient
from ..errors import CyberQPApiError, error_envelope
from ..responses import to_compact_json

ToolHandler = Callable[[CyberQPClient], Awaitable[dict[str, Any]]]

READ_ONLY = ToolAnnotations(readOnlyHint=True)

# Structured access log (SOP section 6): one JSON line per tool call, written
# at the single chokepoint every tool already passes through (call_tool,
# below). Never carries a header value or an upstream response body -- only
# the tool name, a redacted argument summary, the upstream path/status, the
# mapped error code (if any), and duration.
logger = logging.getLogger("cyberqp_mcp")

_ARG_SUMMARY_MAX_CHARS = 60


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


def _summarize_args(args: Mapping[str, Any]) -> dict[str, Any]:
    """Redacted argument summary for the access log (SOP section 6).

    Drops unset (None) filters and truncates long free-text values -- none of
    these tools ever take a credential as a parameter (SOP section 3.1: the
    only way in is a request header), so there is nothing here that needs
    masking rather than just shortening.
    """
    summary: dict[str, Any] = {}
    for key, value in args.items():
        if value is None:
            continue
        if isinstance(value, str) and len(value) > _ARG_SUMMARY_MAX_CHARS:
            summary[key] = value[:_ARG_SUMMARY_MAX_CHARS] + "...(truncated)"
        else:
            summary[key] = value
    return summary


async def call_tool(name: str, args: Mapping[str, Any], handler: ToolHandler) -> str:
    request_id = uuid.uuid4().hex
    started = time.monotonic()
    creds = get_credentials()
    client = CyberQPClient(access_token=creds.access_token, base_url=creds.base_url)
    error_code: str | None = None
    try:
        payload = await handler(client)
        return to_compact_json(payload)
    except CyberQPApiError as exc:
        error_code = exc.code
        return error_envelope(exc.code, exc.message, exc.retryable)
    finally:
        duration_ms = round((time.monotonic() - started) * 1000, 1)
        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "tool": name,
                    "method": "GET",
                    "path": client.last_path,
                    "status": client.last_status_code,
                    "error_code": error_code,
                    "duration_ms": duration_ms,
                    "args": _summarize_args(args),
                },
                separators=(",", ":"),
                default=str,
            )
        )
        await client.aclose()
