"""Сборка MCP-сервера: инструменты, ресурсы и запуск по stdio."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from .config import Settings
from .http_backend import BackendError, HttpBackend
from .tools import Tools

INSTRUCTIONS = """Партнёрская программа Partna: привязка клиентов к коду партнёра,
участники, заказы, возвраты, ссылки и чтение сводки.

Порядок работы:
1. status — проверить, что сервис доступен и ключ задан.
2. partner_link — получить ссылку партнёра.
3. claim — привязать клиента, когда он зарегистрировался.
4. order и refund — сообщать об оплатах и возвратах.

eventId у каждой записи уникален навсегда: повтор с тем же eventId не должен
приводить к повторному начислению. У пишущих инструментов есть dry_run: он
показывает тело запроса и ничего не отправляет.
"""

RESOURCES = {
    "partna://contract/facts": (
        "Контракт фактов v1",
        "Пять операций записи: claim, member, order, refund, partner-link. "
        "Схема: https://github.com/partna-dev/partna-bridge/blob/main/spec/README.md",
    ),
    "partna://contract/levels": (
        "Уровни интеграции",
        "Четыре уровня: готовая ссылка, своя регистрация, свой граф, свои экраны. "
        "Описание: https://github.com/partna-dev/partna-bridge/blob/main/docs/integrations/README.md",
    ),
}


def build_server(api: Any, settings: Settings) -> MCPServer:
    tools = Tools(api, settings)
    server = MCPServer(
        name="partna",
        title="Partna partner network",
        version="0.1.0",
        instructions=INSTRUCTIONS,
    )

    async def guard(call):  # type: ignore[no-untyped-def]
        try:
            return await call
        except BackendError as error:
            raise ToolError(f"сервис ответил {error.status}: {error.detail}") from None

    @server.tool(description="Доступность сервиса, режим и наличие ключа")
    async def status() -> dict[str, Any]:
        return await guard(tools.status())

    @server.tool(
        description=(
            "Привязать клиента к коду партнёра. Клиент уже зарегистрирован "
            "у владельца; external_account_id — его идентификатор там"
        )
    )
    async def claim(
        code: str, external_account_id: str, dry_run: bool = False
    ) -> dict[str, Any]:
        return await guard(
            tools.claim(
                code=code,
                external_account_id=external_account_id,
                dry_run=dry_run,
            )
        )

    @server.tool(
        description="Участник программы и от кого он пришёл. eventId уникален навсегда"
    )
    async def member(
        event_id: str,
        occurred_at: str,
        member_id: str,
        sponsor_id: str | None = None,
        placement_id: str | None = None,
        leg: str | None = None,
        status: str = "active",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        return await guard(
            tools.member(
                event_id=event_id,
                occurred_at=occurred_at,
                member_id=member_id,
                sponsor_id=sponsor_id,
                placement_id=placement_id,
                leg=leg,
                status=status,
                dry_run=dry_run,
            )
        )

    @server.tool(
        description=(
            "Клиент оплатил. amount — в минорных единицах (500000 = 5000.00), "
            "personalVolume — объём для расчёта плана"
        )
    )
    async def order(
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
        return await guard(
            tools.order(
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
                dry_run=dry_run,
            )
        )

    @server.tool(description="Клиенту вернули деньги: ядро откатит начисление")
    async def refund(
        event_id: str,
        occurred_at: str,
        refund_id: str,
        order_id: str,
        amount: int,
        currency: str,
        member_id: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        return await guard(
            tools.refund(
                event_id=event_id,
                occurred_at=occurred_at,
                refund_id=refund_id,
                order_id=order_id,
                amount=amount,
                currency=currency,
                member_id=member_id,
                dry_run=dry_run,
            )
        )

    @server.tool(description="Ссылка партнёра: по ней приходят его клиенты")
    async def partner_link(
        external_account_id: str,
        destination_url: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        return await guard(
            tools.partner_link(
                external_account_id=external_account_id,
                destination_url=destination_url,
                dry_run=dry_run,
            )
        )

    @server.tool(description="Привязан ли клиент и к какому коду")
    async def referral_status(external_account_id: str) -> dict[str, Any]:
        return await guard(tools.referral_status(external_account_id))

    @server.tool(
        description="Сводка партнёра: начислено, выплачено, доступно, приглашённые"
    )
    async def dashboard(member_id: str) -> dict[str, Any]:
        return await guard(tools.dashboard(member_id))

    @server.tool(description="История выплат партнёра")
    async def payouts(member_id: str) -> dict[str, Any]:
        return await guard(tools.payouts(member_id))

    for uri, (title, description) in RESOURCES.items():

        def make(uri: str = uri, title: str = title, description: str = description):
            async def reader() -> str:
                return f"{title}\n\n{description}"

            return reader

        server.resource(
            uri,
            name=title,
            description=description,
            mime_type="text/plain",
        )(make())

    return server


def backend_from(settings: Settings) -> HttpBackend:
    if settings.backend != "http":
        raise ToolError(
            "локальный адаптер ставится отдельно в закрытом репозитории; "
            "для HTTP задайте PARTNA_BACKEND=http"
        )
    return HttpBackend(settings)
