"""Token-economy helpers shared by every tool (SOP section 2.5).

Rules enforced here: compact serialization (no indent, ensure_ascii=False),
and a 20,000-character response cap enforced by truncating `data` lists
rather than shipping an oversized payload.
"""

from __future__ import annotations

import json
from typing import Any

DEFAULT_LIMIT = 50
HARD_LIMIT_CAP = 200
MAX_RESPONSE_CHARS = 20_000


def clamp_limit(limit: int | None, default: int = DEFAULT_LIMIT) -> int:
    """Clamp a requested page size to (1, HARD_LIMIT_CAP] -- never unbounded."""
    if limit is None:
        return default
    return max(1, min(limit, HARD_LIMIT_CAP))


def pick(item: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    """Project an upstream record onto an explicit allow-list of fields.

    Used instead of passing upstream objects through verbatim so a future
    upstream schema addition (e.g. a new credential-bearing field) cannot
    silently start flowing through this server.
    """
    return {f: item[f] for f in fields if f in item}


def to_compact_json(payload: dict[str, Any]) -> str:
    """Serialize compactly; truncate an oversized `data` list instead of shipping it whole."""
    text = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    if len(text) <= MAX_RESPONSE_CHARS or not isinstance(payload.get("data"), list):
        return text

    items = list(payload["data"])
    while items:
        candidate_payload = {**payload, "data": items, "has_more": True}
        candidate = json.dumps(candidate_payload, separators=(",", ":"), ensure_ascii=False)
        if len(candidate) <= MAX_RESPONSE_CHARS:
            return candidate
        items = items[: len(items) // 2] if len(items) > 1 else []

    empty_payload = {**payload, "data": [], "has_more": True}
    return json.dumps(empty_payload, separators=(",", ":"), ensure_ascii=False)
