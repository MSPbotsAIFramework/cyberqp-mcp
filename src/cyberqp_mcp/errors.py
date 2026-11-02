"""Structured error envelope per the Vendor MCP SOP section 4.2.

Tools never raise exceptions to the MCP protocol layer; every error is returned
as a JSON string the Agent can branch on (`code`, `retryable`).
"""

from __future__ import annotations

import json

ERROR_CODES = frozenset(
    {
        "not_configured",
        "unauthorized",
        "not_found",
        "invalid_argument",
        "rate_limited",
        "upstream_error",
    }
)


class CyberQPApiError(Exception):
    """Raised by the client layer and caught at the tool boundary (see tools/_shared.py)."""

    def __init__(self, code: str, message: str, retryable: bool) -> None:
        if code not in ERROR_CODES:
            raise ValueError(f"unknown error code: {code!r}")
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(message)


def error_envelope(code: str, message: str, retryable: bool) -> str:
    if code not in ERROR_CODES:
        raise ValueError(f"unknown error code: {code!r}")
    return json.dumps(
        {"error": {"code": code, "message": message, "retryable": retryable}},
        separators=(",", ":"),
        ensure_ascii=False,
    )
