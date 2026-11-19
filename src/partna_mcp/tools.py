"""Инструменты MCP: тонкий слой над портом, без своей логики.

`dry_run` собирает тело того же вида, что уйдёт на сервер, и ничего не
отправляет. Ключи и адреса в ответы не попадают.
"""

from __future__ import annotations

from typing import Any

from . import bodies
from .config import Settings
from .port import ClaimResult, FactResult, LinkResult, PartnerApi


class Tools:
    def __init__(self, api: PartnerApi, settings: Settings) -> None:
        self._api = api
        self._settings = settings

    async def status(self) -> dict[str, Any]:
        return await self._api.status()

    async def claim(
        self, code: str, external_account_id: str, dry_run: bool = False
    ) -> dict[str, Any]:
        body = bodies.claim_body(
            code=code, external_account_id=external_account_id
        )
        if dry_run:
            return self._preview("claim", body)
        return _claim_json(
            await self._api.claim(code=code, external_account_id=external_account_id)
        )

    async def member(
        self,
        event_id: str,
        occurred_at: str,
        member_id: str,
        sponsor_id: str | None = None,
        placement_id: str | None = None,
        leg: str | None = None,
        status: str = "active",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        body = bodies.member_body(
            event_id=event_id,
            occurred_at=occurred_at,
            member_id=member_id,
            sponsor_id=sponsor_id,
            placement_id=placement_id,
            leg=leg,
            status=status,
        )
        if dry_run:
            return self._preview("member", body)
        return _fact_json(
            await self._api.member(
                event_id=event_id,
                occurred_at=occurred_at,
                member_id=member_id,
                sponsor_id=sponsor_id,
                placement_id=placement_id,
                leg=leg,
                status=status,
            )
        )

    async def order(
        self,
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
        dry_run: bool = False,
    ) -> dict[str, Any]:
        body = bodies.order_body(
            event_id=event_id,
            occurred_at=occurred_at,
            order_id=order_id,
            member_id=member_id,
            amount=amount,
            currency=currency,
            personal_volume=personal_volume,
            product_id=product_id,
            retail_amount=retail_amount,
            certificate_amount=certificate_amount,
        )
        if dry_run:
            return self._preview("order", body)
        return _fact_json(
            await self._api.order(
                event_id=event_id,
                occurred_at=occurred_at,
                order_id=order_id,
                member_id=member_id,
                amount=amount,
                currency=currency,
                personal_volume=personal_volume,
                product_id=product_id,
                retail_amount=retail_amount,
                certificate_amount=certificate_amount,
            )
        )

    async def refund(
        self,
        event_id: str,
        occurred_at: str,
        refund_id: str,
        order_id: str,
        amount: int,
        currency: str,
        member_id: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        body = bodies.refund_body(
            event_id=event_id,
            occurred_at=occurred_at,
            refund_id=refund_id,
            order_id=order_id,
            amount=amount,
            currency=currency,
            member_id=member_id,
        )
        if dry_run:
            return self._preview("refund", body)
        return _fact_json(
            await self._api.refund(
                event_id=event_id,
                occurred_at=occurred_at,
                refund_id=refund_id,
                order_id=order_id,
                amount=amount,
                currency=currency,
                member_id=member_id,
            )
        )

    async def partner_link(
        self,
        external_account_id: str,
        destination_url: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        body = bodies.link_body(
            external_account_id=external_account_id,
            destination_url=destination_url,
        )
        if dry_run:
            return self._preview("partner-link", body)
        return _link_json(
            await self._api.partner_link(
                external_account_id=external_account_id,
                destination_url=destination_url,
            )
        )

    async def referral_status(self, external_account_id: str) -> dict[str, Any]:
        return await self._api.referral_status(
            external_account_id=external_account_id
        )

    async def dashboard(self, member_id: str) -> dict[str, Any]:
        return await self._api.dashboard(member_id=member_id)

    async def payouts(self, member_id: str) -> dict[str, Any]:
        return await self._api.payouts(member_id=member_id)

    def _preview(self, name: str, body: dict[str, Any]) -> dict[str, Any]:
        return {
            "dryRun": True,
            "method": "POST",
            "path": bodies.fact_path(self._settings.facts_mode, name),
            "body": body,
            "note": "ничего не отправлено",
        }


def _claim_json(result: ClaimResult) -> dict[str, Any]:
    data: dict[str, Any] = {"status": result.status}
    for key, value in (
        ("eventId", result.event_id),
        ("code", result.code),
        ("memberId", result.member_id),
        ("sponsorId", result.sponsor_id),
        ("claimedAt", result.claimed_at),
    ):
        if value is not None:
            data[key] = value
    return data


def _fact_json(result: FactResult) -> dict[str, Any]:
    data: dict[str, Any] = {"eventId": result.event_id, "queued": result.queued}
    if result.status is not None:
        data["status"] = result.status
    if result.duplicate:
        data["duplicate"] = True
    data.update(result.extra)
    return data


def _link_json(result: LinkResult) -> dict[str, Any]:
    data: dict[str, Any] = {"code": result.code, "url": result.url}
    if result.expires_at is not None:
        data["expiresAt"] = result.expires_at
    return data
