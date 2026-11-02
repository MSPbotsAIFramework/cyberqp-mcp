# PRD-21228 · Code review

## Round 1 · 2026-11-02 · reviewed dev/PRD-21228 @ 965031b (base main @ 1e9be1e)

Verdict: changes requested

### What was checked

- Full diff `origin/main...965031b` (33 files, all new: server, auth, client, errors, responses, 4 tool modules, tests, README, Dockerfile, pyproject.toml, docs).
- Re-ran gates in a fresh worktree: `uv run pytest -v` → 25 passed, 0 failed (matches Self-test claim); `uv run mypy --strict src/cyberqp_mcp` → no issues (matches claim).
- Diffed the README's "MSPbots Connector" section against `~/.claude/skills/vendor-mcp-development/reference/readme-connector-section.md` byte-for-byte — identical.
- Re-ran the Chinese-character scan and a manual credential-pattern grep — no matches (confirms the Self-test's gitleaks-unavailable fallback).
- Read every source file in `src/cyberqp_mcp/` and every test module against the 10-tool contract in the tech design.
- Attempted `docker build --platform linux/amd64` to close the gap the dev leg's Self-test flagged ("no Docker daemon available on this host") — this environment also has no Docker socket permission for this account (`permission denied … docker.sock`), so the container build still could not be verified here. Not treated as a new gap: it is the same pre-existing gap the dev leg already flagged, and `mcppub register` will do a real build + deploy + health check at publish time regardless (R5 of this review).

### Findings

1. **[must-fix]** `docs/tickets/PRD-21228.md:166` vs. no implementation anywhere in `src/cyberqp_mcp/` — Tech design's Non-functional section states: *"Observability: standard access logging — method, tool name, HTTP status, duration — never header values or response bodies (SOP §6)."* This is written as a design decision that was carried out, but it was not: `grep -rn "^import logging\|getLogger\|structlog\|request_id\|correlation" src/` returns nothing. There is no logger, no request-id, no per-tool-call record anywhere in the server. SOP §14's pre-delivery checklist ("日志与敏感信息") explicitly requires "结构化日志带 request-id" as a deliverable item, and `mcp-track.md` §4.3 lists "SOP §14 Checklist" as one of the must-fix criteria for this track. Unlike the two other gaps this ticket is genuinely blocked on (no Docker daemon, no live CyberQP tenant), this one is not flagged anywhere in Self-test/Handoff as a known, accepted gap — it is simply absent while the design claims it is present. A connector that passes through multi-tenant privileged-access-management data with zero audit trail of which tool was called, by which request, with what result, is also a real operational gap for a PAM-visibility product, not just a paperwork mismatch.
   What would fix it: add structured logging (JSON or key=value) at the one chokepoint every tool call already passes through, `src/cyberqp_mcp/tools/_shared.py:44` (`call_tool`) — log a generated/propagated request-id, the tool name, a redacted argument summary, the upstream path and status code (available from `CyberQPApiError`/the happy-path return), and elapsed time. Must not log `access_token` or raw response bodies, per the same SOP section.

### Fixes

(none yet — round 1)
