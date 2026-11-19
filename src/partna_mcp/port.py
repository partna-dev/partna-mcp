"""Порт партнёрской программы: то, что умеет MCP, без привязки к транспорту.

Семантика повторяет сервисные функции ядра: одна операция — один факт.
Локальный адаптер вызывает их напрямую, HTTP-адаптер — по публичному
контракту фактов. Инструменты знают только этот протокол.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class ClaimResult:
    status: str
    event_id: str | None = None
    code: str | None = None
    member_id: str | None = None
    sponsor_id: str | None = None
    claimed_at: str | None = None


@dataclass(frozen=True, slots=True)
class FactResult:
    event_id: str
    queued: bool
    status: str | None = None
    duplicate: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LinkResult:
    code: str
    url: str
    expires_at: str | None = None


class PartnerApi(Protocol):
    """Ровно те операции, которые нужны инструментам MCP."""

    async def status(self) -> dict[str, Any]: ...

    async def claim(self, *, code: str, external_account_id: str) -> ClaimResult: ...

    async def member(
        self,
        *,
        event_id: str,
        occurred_at: str,
        member_id: str,
        sponsor_id: str | None = None,
        placement_id: str | None = None,
        leg: str | None = None,
        status: str = "active",
    ) -> FactResult: ...

    async def order(
        self,
        *,
        event_id: str,
        occurred_at: str,
        order_id: str,
        member_id: str,
        amount: int,
        currency: str,
        personal_volume: str,
        product_id: str | None = None,
        retail_amount: int | None = None,
        certificate_amount: int | None = None,
    ) -> FactResult: ...

    async def refund(
        self,
        *,
        event_id: str,
        occurred_at: str,
        refund_id: str,
        order_id: str,
        amount: int,
        currency: str,
        member_id: str | None = None,
    ) -> FactResult: ...

    async def partner_link(
        self, *, external_account_id: str, destination_url: str | None = None
    ) -> LinkResult: ...

    async def referral_status(self, *, external_account_id: str) -> dict[str, Any]: ...

    async def dashboard(self, *, member_id: str) -> dict[str, Any]: ...

    async def payouts(self, *, member_id: str) -> dict[str, Any]: ...
