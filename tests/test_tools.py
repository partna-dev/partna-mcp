from __future__ import annotations

import inspect
import json
from typing import Any

from partna_mcp.config import Settings
from partna_mcp.port import ClaimResult, FactResult, LinkResult
from partna_mcp.server import build_server
from partna_mcp.tools import Tools


class FakeApi:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def status(self) -> dict[str, Any]:
        self.calls.append(("status", {}))
        return {"facts": True, "keyConfigured": True}

    async def claim(self, **kwargs: Any) -> ClaimResult:
        self.calls.append(("claim", kwargs))
        return ClaimResult(status="claimed", member_id="u1", sponsor_id="p1")

    async def member(self, **kwargs: Any) -> FactResult:
        self.calls.append(("member", kwargs))
        return FactResult(event_id=kwargs["event_id"], queued=False, status="accepted")

    async def order(self, **kwargs: Any) -> FactResult:
        self.calls.append(("order", kwargs))
        return FactResult(event_id=kwargs["event_id"], queued=True, status=None)

    async def refund(self, **kwargs: Any) -> FactResult:
        self.calls.append(("refund", kwargs))
        return FactResult(event_id=kwargs["event_id"], queued=False)

    async def partner_link(self, **kwargs: Any) -> LinkResult:
        self.calls.append(("partner_link", kwargs))
        return LinkResult(code="IRON", url="https://shop.example/r/IRON")

    async def referral_status(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("referral_status", kwargs))
        return {"claimed": True, "memberId": "u1"}

    async def dashboard(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("dashboard", kwargs))
        return {"summary": {"availableMinor": 1000}}

    async def payouts(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("payouts", kwargs))
        return {"payouts": []}


def _settings() -> Settings:
    return Settings(bridge_url="https://bridge.example")


async def test_dry_run_shows_the_body_and_sends_nothing() -> None:
    api = FakeApi()
    tools = Tools(api, _settings())

    preview = await tools.order(
        event_id="order:1",
        occurred_at="2026-11-01T10:00:00Z",
        order_id="1",
        member_id="u1",
        amount=500000,
        currency="RUB",
        personal_volume="5000",
        dry_run=True,
    )

    assert api.calls == []
    assert preview["dryRun"] is True
    assert preview["path"] == "/v1/order"
    assert preview["body"]["amount"] == 500000
    assert preview["body"]["eventId"] == "order:1"


async def test_dry_run_follows_the_engine_path_in_engine_mode() -> None:
    tools = Tools(FakeApi(), Settings(engine_url="https://engine.example"))

    preview = await tools.claim(code="IRON", external_account_id="u1", dry_run=True)

    assert preview["path"] == "/v1/referrals/claim"


async def test_server_exposes_the_tools_and_reads_them_back() -> None:
    api = FakeApi()
    server = build_server(api, _settings())

    tools = await server.list_tools()
    names = [tool.name for tool in tools]

    assert names == [
        "status",
        "claim",
        "member",
        "order",
        "refund",
        "partner_link",
        "referral_status",
        "dashboard",
        "payouts",
    ]

    result = await server.call_tool(
        "claim", {"code": "IRON", "external_account_id": "u1"}
    )
    text = result.content[0].text
    assert json.loads(text)["memberId"] == "u1"
    assert api.calls[-1][0] == "claim"


async def test_resources_point_at_the_contract() -> None:
    server = build_server(FakeApi(), _settings())

    resources = await server.list_resources()

    assert {str(item.uri) for item in resources} == {
        "partna://contract/facts",
        "partna://contract/levels",
    }


async def test_no_secret_reaches_the_tool_output() -> None:
    settings = Settings(
        bridge_url="https://bridge.example",
        engine_url="https://engine.example",
        api_key="tenant-key",
        bridge_token="bridge-token",
    )
    server = build_server(FakeApi(), settings)

    result = await server.call_tool("status", {})
    text = result.content[0].text

    assert "tenant-key" not in text
    assert "bridge-token" not in text


async def test_tools_run_against_a_fake_api_without_network() -> None:
    api = FakeApi()
    tools = Tools(api, _settings())

    claim = await tools.claim(code="IRON", external_account_id="u1")

    assert inspect.iscoroutinefunction(tools.claim)
    assert claim["status"] == "claimed"
