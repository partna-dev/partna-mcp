"""Golden-кейсы: один и тот же вход должен давать один и тот же ответ.

Файлы в `golden/` — общий эталон для HTTP-адаптера (здесь) и локального
адаптера (в закрытом репозитории). Локальная реализация должна воспроизвести
`expected` для тех же `input`, не ходя в сеть.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from partna_mcp.config import Settings
from partna_mcp.http_backend import HttpBackend
from partna_mcp.tools import Tools

GOLDEN = Path(__file__).resolve().parents[1] / "golden"


def _cases() -> list[dict[str, Any]]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(GOLDEN.glob("*.json"))
    ]


def _backend(case: dict[str, Any]) -> HttpBackend:
    server = case["server"]

    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(server["status"], json=server["body"])

    return HttpBackend(
        Settings(
            bridge_url="https://bridge.example",
            engine_url="https://engine.example",
            api_key="tenant-key",
            bridge_token="bridge-token",
        ),
        httpx.AsyncClient(transport=httpx.MockTransport(respond)),
    )


async def test_golden_cases_are_reproduced_by_the_http_backend() -> None:
    for case in _cases():
        tools = Tools(_backend(case), Settings(bridge_url="https://bridge.example"))
        result = await getattr(tools, case["operation"])(**case["input"])
        assert result == case["expected"], case["name"]
