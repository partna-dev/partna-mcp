"""Настройки MCP: адреса и ключи берутся только из окружения.

Ключ тенанта никогда не печатается и не принимается аргументом инструмента.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PARTNA_", env_file=".env", extra="ignore"
    )

    backend: str = "http"
    bridge_url: str | None = None
    engine_url: str | None = None
    api_key: str | None = None
    bridge_token: str | None = None
    timeout_seconds: float = 10.0

    @property
    def facts_url(self) -> str:
        base = self.bridge_url or self.engine_url
        if not base:
            raise ValueError(
                "нужен PARTNA_BRIDGE_URL или PARTNA_ENGINE_URL: MCP не знает, куда писать"
            )
        return base.rstrip("/")

    @property
    def facts_mode(self) -> str:
        return "bridge" if self.bridge_url else "engine"

    @property
    def reads_url(self) -> str:
        if not self.engine_url:
            raise ValueError("для чтения нужен PARTNA_ENGINE_URL")
        return self.engine_url.rstrip("/")
