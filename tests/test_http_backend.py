from __future__ import annotations

import json

import httpx
import pytest

from partna_mcp.config import Settings
from partna_mcp.http_backend import BackendError, HttpBackend


def _client(calls: list[httpx.Request], handler=None) -> httpx.AsyncClient:
    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if handler is not None:
            return handler(request)
        return httpx.Response(200, json={"status": "ok"})

    return httpx.AsyncClient(transport=httpx.MockTransport(respond))


def _settings(**overrides) -> Settings:
    values = {
        "bridge_url": "https://bridge.example",
        "engine_url": "https://engine.example",
        "api_key": "tenant-key",
        "bridge_token": "bridge-token",
    }
    values.update(overrides)
    return Settings(**values)


async def test_facts_go_to_the_bridge_by_default() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "queued": False,
                "eventId": "order:1",
                "engine": {
                    "eventId": "order:1",
                    "status": "accepted",
                    "duplicate": False,
                },
            },
        )

    backend = HttpBackend(_settings(), _client(calls, handler))
    result = await backend.order(
        event_id="order:1",
        occurred_at="2026-11-01T10:00:00Z",
        order_id="1",
        member_id="u1",
        amount=500000,
        currency="RUB",
        personal_volume="5000",
    )

    request = calls[0]
    assert str(request.url) == "https://bridge.example/v1/order"
    assert request.headers["authorization"] == "Bearer bridge-token"
    body = json.loads(request.content)
    assert body["eventId"] == "order:1"
    assert body["personalVolume"] == "5000"
    assert "productId" not in body
    assert result.status == "accepted"
    assert result.queued is False


async def test_engine_mode_uses_engine_paths_and_key() -> None:
    calls: list[httpx.Request] = []

    backend = HttpBackend(
        _settings(bridge_url=None),
        _client(
            calls,
            lambda r: httpx.Response(
                200,
                json={"eventId": "m:1", "status": "accepted", "duplicate": False},
            ),
        ),
    )
    await backend.member(
        event_id="m:1",
        occurred_at="2026-11-01T10:00:00Z",
        member_id="u1",
        sponsor_id=None,
        placement_id=None,
        leg=None,
        status="active",
    )

    request = calls[0]
    assert str(request.url) == "https://engine.example/v1/members"
    assert request.headers["x-api-key"] == "tenant-key"
    assert "authorization" not in request.headers


async def test_claim_reports_a_pending_binding() -> None:
    backend = HttpBackend(
        _settings(),
        _client(
            [],
            lambda r: httpx.Response(
                202, json={"status": "pending", "eventId": "claim:IRON:u1"}
            ),
        ),
    )

    result = await backend.claim(code="IRON", external_account_id="u1")

    assert result.status == "pending"
    assert result.event_id == "claim:IRON:u1"
    assert result.member_id is None


async def test_reads_go_to_the_engine_with_the_key() -> None:
    calls: list[httpx.Request] = []
    backend = HttpBackend(
        _settings(),
        _client(
            calls,
            lambda r: httpx.Response(200, json={"profile": {"memberId": "u1"}}),
        ),
    )

    await backend.dashboard(member_id="u1")
    await backend.payouts(member_id="u1")
    await backend.referral_status(external_account_id="u1")

    assert str(calls[0].url) == "https://engine.example/v1/portal/partners/u1"
    assert str(calls[1].url) == "https://engine.example/v1/portal/partners/u1/payouts"
    assert calls[2].url.params["externalAccountId"] == "u1"
    assert all(c.headers["x-api-key"] == "tenant-key" for c in calls)


async def test_service_errors_keep_the_detail_and_never_the_key() -> None:
    backend = HttpBackend(
        _settings(),
        _client(
            [],
            lambda r: httpx.Response(409, json={"detail": "клиент уже привязан"}),
        ),
    )

    with pytest.raises(BackendError) as caught:
        await backend.claim(code="IRON", external_account_id="u1")

    assert caught.value.status == 409
    assert "уже привязан" in caught.value.detail
    assert "tenant-key" not in str(caught.value)


async def test_unreachable_service_is_reported_as_502() -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route")

    backend = HttpBackend(_settings(), _client([], boom))

    with pytest.raises(BackendError) as caught:
        await backend.status()

    assert caught.value.status == 502


async def test_status_tells_where_facts_go() -> None:
    backend = HttpBackend(
        _settings(), _client([], lambda r: httpx.Response(200, json={"status": "ok"}))
    )

    info = await backend.status()

    assert info["factsMode"] == "bridge"
    assert info["facts"] is True
    assert info["readsAvailable"] is True
    assert info["keyConfigured"] is True
    assert "bridge-token" not in json.dumps(info)
