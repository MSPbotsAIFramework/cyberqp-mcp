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

Fixed in `dc8b8c3` (dev/PRD-21228).

1. **Finding 1 (must-fix, structured access logging)** — added one structured JSON log line per tool call, written at the chokepoint the finding named, `call_tool` in `src/cyberqp_mcp/tools/_shared.py`:
   - `CyberQPClient` (`client.py`) gained `last_path`/`last_status_code`, set on the client before a request can fail so a log line still has the path even on a timeout or network error (status stays `null` in that case — there was no HTTP response to report a status from).
   - `call_tool` now takes the tool's own name and its argument mapping (all 10 call sites in `tools/*.py` updated) and, in a `finally` block around the handler, logs: `request_id` (generated per call, `uuid4().hex`), `tool`, `method` (`GET` — this connector only ever issues reads), `path`, `status`, `error_code` (the mapped `CyberQPApiError.code`, `null` on success), `duration_ms`, and `args` (a redacted summary: unset/`None` filters dropped, strings over 60 chars truncated). Never a header value, access token, or upstream response body — confirmed by test, not just by inspection.
   - `logging.basicConfig(level=logging.INFO, format="%(message)s")` added to `__main__.py:main()` (the production entry point only — not `server.py`, which tests also import, so test runs stay quiet) so each log line is emitted as a standalone JSON object on stdout.
   - New `tests/test_logging.py` (3 cases, `tests/test_logging.py::test_successful_call_logs_tool_name_path_status_and_request_id`, `::test_argument_summary_is_logged_and_long_values_truncated`, `::test_failed_call_logs_error_code_and_upstream_status_without_leaking_credential`) added to `docs/tickets/PRD-21228.ac.json` as `TC-CQP-027..029` (`source: dev` — this gap was found by review, not named as an AC in the original design, so no existing AC number fits). The third case asserts the test access token, the test base URL, and the upstream response body string are all absent from every log record captured during the test — the finding's central claim (an audit trail must exist) is proven, not just the log's shape.
   - `conftest.py`'s `FakeCyberQPClient` test double (used by the per-tool happy-path tests) gained the same `last_path`/`last_status_code` attributes so `call_tool`'s new logging code runs unchanged against it; none of the existing 25 tests needed to change.
   - Verified end-to-end against the real running server, not just the mocked unit tests: `uv run python -m cyberqp_mcp`, then `tools/list` and a real `tools/call` over HTTP with a placeholder credential header — one JSON access-log line appeared on stdout per call, with the fields above and no credential in it.
   - Re-ran the full gate: `uv run pytest -v` → 28 passed (25 prior + 3 new), 0 failed; `uv run mypy --strict src/cyberqp_mcp` → no issues; Chinese-character scan on `src/`, `tests/`, `README.md`, `Dockerfile`, `docker-compose.yml` → clean; `gitleaks` still unavailable on this host (same pre-existing gap round 1 noted, not reintroduced by this fix).
   - Not changed: `CyberQPApiError` (errors.py) still carries only the mapped semantic `code`, not the raw HTTP status — the real status is read off the client instead (`last_status_code`), which is simpler than widening the exception and just as accurate, since each tool handler makes exactly one `client.get()` call (confirmed by reading every `tools/*.py` handler before making this change).
