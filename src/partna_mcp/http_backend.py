"""HTTP-адаптер порта: говорит с мостом (или ядром) по публичному контракту."""

from __future__ import annotations

from typing import Any

import httpx

from . import bodies
from .config import Settings
from .port import ClaimResult, FactResult, LinkResult


class BackendError(RuntimeError):
    """Ошибка бэкенда без секретов: только статус и текст от сервиса."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


class HttpBackend:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._client = client
        self._owned = client is None

    async def __aenter__(self) -> HttpBackend:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._settings.timeout_seconds)
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._owned and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def status(self) -> dict[str, Any]:
        facts = await self._call(
            "GET", self._settings.facts_url + "/health", key="facts"
        )
        reads = False
        if self._settings.engine_url:
            try:
                await self._call(
                    "GET", self._settings.reads_url + "/health", key="engine"
                )
                reads = True
            except BackendError:
                reads = False
        return {
            "factsUrl": self._settings.facts_url,
            "factsMode": self._settings.facts_mode,
            "facts": facts.get("status") == "ok",
            "readsAvailable": reads,
            "keyConfigured": bool(self._settings.api_key),
        }

    async def claim(self, *, code: str, external_account_id: str) -> ClaimResult:
        data = await self._fact(
            "claim", bodies.claim_body(code=code, external_account_id=external_account_id)
        )
        return ClaimResult(
            status=str(data.get("status") or "claimed"),
            event_id=data.get("eventId"),
            code=data.get("code"),
            member_id=data.get("memberId"),
            sponsor_id=data.get("sponsorId"),
            claimed_at=data.get("claimedAt"),
        )

    async def member(self, **kwargs: Any) -> FactResult:
        return self._result(
            await self._fact("member", bodies.member_body(**kwargs))
        )

    async def order(self, **kwargs: Any) -> FactResult:
        return self._result(await self._fact("order", bodies.order_body(**kwargs)))

    async def refund(self, **kwargs: Any) -> FactResult:
        return self._result(await self._fact("refund", bodies.refund_body(**kwargs)))

    async def partner_link(
        self, *, external_account_id: str, destination_url: str | None = None
    ) -> LinkResult:
        data = await self._fact(
            "partner-link",
            bodies.link_body(
                external_account_id=external_account_id, destination_url=destination_url
            ),
        )
        return LinkResult(
            code=str(data.get("code") or ""),
            url=str(data.get("url") or ""),
            expires_at=data.get("expiresAt"),
        )

    async def referral_status(self, *, external_account_id: str) -> dict[str, Any]:
        return await self._call(
            "GET",
            self._settings.reads_url + "/v1/referrals/status",
            key="engine",
            params={"externalAccountId": external_account_id},
        )

    async def dashboard(self, *, member_id: str) -> dict[str, Any]:
        return await self._call(
            "GET",
            f"{self._settings.reads_url}/v1/portal/partners/{member_id}",
            key="engine",
        )

    async def payouts(self, *, member_id: str) -> dict[str, Any]:
        return await self._call(
            "GET",
            f"{self._settings.reads_url}/v1/portal/partners/{member_id}/payouts",
            key="engine",
        )

    async def _fact(self, name: str, body: dict[str, Any]) -> dict[str, Any]:
        path = bodies.fact_path(self._settings.facts_mode, name)
        return await self._call(
            "POST", self._settings.facts_url + path, key="facts", json=body
        )

    async def _call(
        self,
        method: str,
        url: str,
        *,
        key: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        client = await self._client_or_raise()
        headers = self._headers(key)
        try:
            response = await client.request(
                method, url, headers=headers, params=params, json=json
            )
        except httpx.HTTPError as error:
            raise BackendError(502, f"сервис недоступен: {error}") from None
        if response.status_code >= 400:
            raise BackendError(response.status_code, _detail(response))
        try:
            return response.json()
        except ValueError:
            raise BackendError(502, "сервис ответил не JSON") from None

    def _headers(self, key: str) -> dict[str, str]:
        if key == "facts":
            if self._settings.facts_mode == "bridge":
                token = self._settings.bridge_token
                return {"Authorization": f"Bearer {token}"} if token else {}
            return (
                {"X-API-Key": self._settings.api_key}
                if self._settings.api_key
                else {}
            )
        if key == "engine" and self._settings.api_key:
            return {"X-API-Key": self._settings.api_key}
        return {}

    async def _client_or_raise(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._settings.timeout_seconds)
        return self._client

    def _result(self, data: dict[str, Any]) -> FactResult:
        engine = data.get("engine") or {}
        return FactResult(
            event_id=str(data.get("eventId") or engine.get("eventId") or ""),
            queued=bool(data.get("queued")),
            status=engine.get("status"),
            duplicate=bool(engine.get("duplicate")),
            extra={k: v for k, v in data.items() if k not in {"queued", "eventId", "engine"}},
        )


def _detail(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return f"ошибка {response.status_code}"
    if isinstance(body, dict) and body.get("detail"):
        return str(body["detail"])
    return f"ошибка {response.status_code}"
