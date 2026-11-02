"""Entry point: run the Starlette app with uvicorn."""

from __future__ import annotations

import logging

import uvicorn

from .config import settings
from .server import create_app


def main() -> None:
    # One JSON line per tool call (tools/_shared.py:call_tool, SOP section 6).
    # format="%(message)s" because the message is already a complete JSON
    # object -- no extra prefix to keep each log line valid JSON.
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    uvicorn.run(create_app(), host=settings.mcp_http_host, port=settings.mcp_http_port)


if __name__ == "__main__":
    main()
