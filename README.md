# cyberqp-mcp

MCP server for [CyberQP](https://www.cyberqp.com) (vendor brand "QuickPass Cybersecurity"), a
privileged access management (PAM) product. This server is strictly **read-only**: it cannot
retrieve a password, an OTP secret, or an install/enrollment token, and it cannot create,
update, enable, disable, or delete anything in CyberQP. Every endpoint capable of any of those
is simply not wrapped as a tool -- see "Deliberately not built" below.

Transport: MCP Streamable HTTP (`POST /mcp`), stateless. Stack: Python 3.12, FastMCP, httpx,
pydantic. License: Apache-2.0. Copyright MSPbots.ai.

---

<div align="center">

## MSPbots Connector

**The MCP Gateway built for MSPs: visible, controlled, and your data stays where it belongs.**

[**Get started at connect.mspbots.ai →**](https://connect.mspbots.ai)

</div>

---

MSPbots Connector gives your AI clients one MCP URL to reach your entire MSP stack (RMM, PSA, documentation, security, finance), and gives you control over who can call which tool and a record of everything that was called.

**Hosted service: [connect.mspbots.ai](https://connect.mspbots.ai)** · Free to use.

### Why Connector

![MSPbots Connector](https://stgoss.mspbots.ai/files/mcp/mspbots-mcp.png)

| | |
|---|---|
| **Visible** | Every tool call is logged: who, which vendor, when. Usage dashboard, CSV export, SIEM streaming. |
| **Controlled** | Role-based, per-tool allowlist. Deny by default. |
| **Protected** | Credentials encrypted per record. AI clients never see your vendor passwords or tokens. |
| **MSP-native** | Built for the MSP stack only: RMM, PSA, documentation, security, finance. |

### Quick start

1. **Sign up** at [connect.mspbots.ai](https://connect.mspbots.ai).
2. **Connect your vendors.** Pick from 150+ connectors and authorize each one on the vendor's own page, or bring your own API keys. No extra vendor accounts needed.
3. **Set access.** Create roles and decide which tools each role may call. Nothing is allowed until you allow it.
4. **Add your MCP URL to your AI client.** Copy the URL from your Connector dashboard into Claude, ChatGPT, Cursor, VS Code, Gemini, Codex, or any MCP-capable client.
5. **Ask your AI to do real work**, and watch every call appear in the audit log.

### Features

**Unified gateway**
- One MCP URL for all your AI clients
- 150+ connectors across the MSP stack
- Custom MCP servers supported, free
- Authorization happens on each vendor's own page; the AI never sees passwords or tokens
- Bring your own credentials: use the vendor API keys you already have
- Multiple accounts per app; connect once, reuse across AI clients
- Tool search: finds the right action for the task
- One sign-in; vendor credentials are injected behind the scenes and OAuth tokens refresh automatically

**Visibility**
- Audit log for every tool call (who, which vendor, when)
- Usage dashboard: call volume, top vendors, error rate, per-user activity
- Export audit logs to CSV, or stream to Loki, Graylog, or LogScale (SIEM)
- Optional recording of tool arguments and result summaries (off by default, enabled per organization)

**Control**
- Per-role, per-tool allowlist, deny by default
- owner / admin / member roles
- SCIM provisioning with Entra ID, Okta, JumpCloud, and Google Workspace

**Security**
- Credentials encrypted one record at a time (AES-256-GCM, per-record key)
- AI clients authenticate with OAuth 2.1 + PKCE
- Vendor responses are scanned for prompt-injection patterns and returned as structured data. This is one layer of defense, not a guarantee against every attack.
- Static egress IP for customer firewall and API allowlisting

### Pricing

**Free.**

Links: [connect.mspbots.ai](https://connect.mspbots.ai) · [mspbots.ai](https://mspbots.ai)

---

## Authentication headers

| Header | Required | Meaning | Where to get it |
|---|---|---|---|
| `X-CyberQp-Access-Token` | Yes | OAuth2 bearer access token for the tenant's CyberQP account. Request only the `profile` and `customer` scopes -- never `password_rotation_write`, since this connector has no write tools. | A tenant's Primary or Super role holder generates it via CyberQP's API consent flow -- see "Getting started with the CyberQP API" on CyberQP's support site. Expires hourly; refreshed by the MSPbots Connector gateway, not by this server. |
| `X-CyberQp-Base-Url` | Yes | The tenant's CyberQP regional API host, e.g. `https://ca.cyberqp.com`, `https://us.getquickpass.com`, or `https://eu.getquickpass.com`. No default -- a tenant pointed at the wrong region must fail loudly, not silently return another region's (empty) data. | Matches the host the tenant already uses to log into the CyberQP dashboard. |

A request missing either header gets HTTP 401 before any call is made to CyberQP; the body names which header(s) are missing.

## Tools (10, all read-only)

| Tool | Wraps | Description |
|---|---|---|
| `cyberqp_list_customers` | `GET /api/v1/customers` | List the tenant's CyberQP customers/clients. |
| `cyberqp_list_customer_accounts` | `GET /api/v1/customers/{id}/accounts` | List a customer's managed (privileged) accounts. |
| `cyberqp_get_customer_account_counts` | `GET /api/v1/customers/{id}/accounts/count` | Get a customer's managed account counts broken down by account type. |
| `cyberqp_list_jit_policies` | `GET /api/v1/jit-policies/account` | List a customer's configured JIT (just-in-time) access policies. |
| `cyberqp_list_customer_jit_accounts` | `GET /api/v1/jit/customer/{customerId}` | List a customer's active JIT accounts. |
| `cyberqp_list_tenant_jit_accounts` | `GET /api/v1/jit/tenant` | List active JIT accounts tenant-wide, across all customers. |
| `cyberqp_check_jit_account` | `GET /api/v1/jit/customer/{customerId}/account/check` | Check whether a JIT account currently exists for a customer. |
| `cyberqp_list_events` | `GET /api/v1/event` | List audit/event records of privileged-access activity. |
| `cyberqp_list_event_types` | `GET /api/v1/event/types` | List the reference event-type codes usable as an event filter. |
| `cyberqp_get_tenant_company_data` | `GET /api/v1/tenants/company-data` | Get the CyberQP tenant's own company metadata. |

No tool in this list can return a password, an OTP secret, or an install/enrollment token, and
none of them creates, updates, enables, disables, or deletes anything.

### Deliberately not built

These CyberQP endpoints exist in its public API but are intentionally excluded from this
server's tool surface -- not implemented at all, not implemented-and-flagged-off:

| Endpoint | Why excluded |
|---|---|
| `GET /api/v1/account/{accountId}/password` | Returns an account password. |
| `GET /api/v1/jit/customer/{customerId}/account/{accountId}/password` | Returns a JIT account's password. |
| `GET/POST/DELETE /api/v1/jit/customer/{customerId}/account/{accountId}/otp` | Return or set an OTP secret. |
| `POST /api/v1/jit/customer/{customerId}/account`, `DELETE .../account/{accountId}`, `PATCH .../enable`, `PATCH .../disable` | Create, delete, enable, or disable a JIT account -- writes. |
| `POST /api/v1/identity-verification/self-serve-notification` | Triggers an identity-verification/MFA push -- a write/side-effecting call. |
| `POST /api/v1/event` | Submits an event -- a write. |
| `GET /api/v1/tenants/install-token`, `GET /api/v1/customers/installer` | Return an agent enrollment token / installer download -- treated as credential-equivalent. |
| `GET/POST /api/v1/auth/*` | OAuth/session plumbing, handled by the Connector gateway that injects the per-request header; not an agent-facing capability. |

## Error handling

Tools never raise exceptions to the protocol layer. Errors are returned as an in-band JSON
envelope: `{"error": {"code": "<code>", "message": "<text>", "retryable": <bool>}}`, where
`code` is one of `not_configured`, `unauthorized`, `not_found`, `invalid_argument`,
`rate_limited`, `upstream_error`. An empty result (e.g. a customer with no accounts) is a
normal successful response, never an error.

## Local development

```bash
uv sync
uv run pytest
uv run mypy src/cyberqp_mcp
uv run python -m cyberqp_mcp
```

The server listens on `0.0.0.0:8080` by default (override with `MCP_HTTP_PORT` /
`MCP_HTTP_HOST`). Test it with real CyberQP credentials in your own shell environment -- never
pass secrets on the command line or write them into a file in this repository:

```bash
curl -N -X POST http://localhost:8080/mcp \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -H "X-CyberQp-Access-Token: $CYBERQP_ACCESS_TOKEN" \
  -H "X-CyberQp-Base-Url: https://ca.cyberqp.com" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

## Container

```bash
docker build --platform linux/amd64 -t cyberqp-mcp:dev .
```
