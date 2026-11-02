"""Non-credential configuration only.

Credentials (access token, regional base URL) are per-request and never belong
here -- they come from HTTP headers and live in auth.py's ContextVar.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    mcp_http_host: str = "0.0.0.0"
    mcp_http_port: int = 8080


settings = Settings()
