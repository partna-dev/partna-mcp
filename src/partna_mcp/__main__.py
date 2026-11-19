"""Запуск: partna-mcp (stdio)."""

from __future__ import annotations

import asyncio

from .config import Settings
from .server import backend_from, build_server


def main() -> None:
    settings = Settings()
    backend = backend_from(settings)
    server = build_server(backend, settings)
    asyncio.run(_serve(server))


async def _serve(server) -> None:
    await server.run_stdio_async()


if __name__ == "__main__":
    main()
