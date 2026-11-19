"""Тела и пути фактов: одна форма для моста и ядра.

Мост и ядро делают одно и то же, но разными путями. Здесь собраны и пути, и
тела, чтобы `dry_run` показывал ровно то, что уйдёт на сервер.
"""

from __future__ import annotations

from typing import Any

BRIDGE_PATHS = {
    "claim": "/v1/claim",
    "member": "/v1/member",
    "order": "/v1/order",
    "refund": "/v1/refund",
    "partner-link": "/v1/partner-link",
}

ENGINE_PATHS = {
    "claim": "/v1/referrals/claim",
    "member": "/v1/members",
    "order": "/v1/orders",
    "refund": "/v1/refunds",
    "partner-link": "/v1/referral-links",
}


def fact_path(mode: str, name: str) -> str:
    return (BRIDGE_PATHS if mode == "bridge" else ENGINE_PATHS)[name]


def claim_body(*, code: str, external_account_id: str) -> dict[str, Any]:
    return {"code": code, "externalAccountId": external_account_id}


def member_body(
    *,
    event_id: str,
    occurred_at: str,
    member_id: str,
    sponsor_id: str | None = None,
    placement_id: str | None = None,
    leg: str | None = None,
    status: str = "active",
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "eventId": event_id,
        "occurredAt": occurred_at,
        "memberId": member_id,
        "status": status,
    }
    if sponsor_id:
        body["sponsorId"] = sponsor_id
    if placement_id:
        body["placementId"] = placement_id
    if leg:
        body["leg"] = leg
    return body


def order_body(
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
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "eventId": event_id,
        "occurredAt": occurred_at,
        "orderId": order_id,
        "memberId": member_id,
        "amount": amount,
        "currency": currency,
        "personalVolume": personal_volume,
    }
    if product_id:
        body["productId"] = product_id
    if retail_amount is not None:
        body["retailAmount"] = retail_amount
    if certificate_amount is not None:
        body["certificateAmount"] = certificate_amount
    return body


def refund_body(
    *,
    event_id: str,
    occurred_at: str,
    refund_id: str,
    order_id: str,
    amount: int,
    currency: str,
    member_id: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "eventId": event_id,
        "occurredAt": occurred_at,
        "refundId": refund_id,
        "orderId": order_id,
        "amount": amount,
        "currency": currency,
    }
    if member_id:
        body["memberId"] = member_id
    return body


def link_body(
    *, external_account_id: str, destination_url: str | None = None
) -> dict[str, Any]:
    body: dict[str, Any] = {"externalAccountId": external_account_id}
    if destination_url:
        body["destinationUrl"] = destination_url
    return body
