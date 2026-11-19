"""Golden-кейсы: общий эталон для HTTP- и локального адаптера.

Файлы лежат в пакете, чтобы закрытый репозиторий гонял те же примеры, что и
открытый, и расхождение двух реализаций ловилось тестом, а не клиентом.
"""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

Case = dict[str, Any]


def load_cases() -> list[Case]:
    root = resources.files(__name__)
    cases = []
    for path in sorted(root.iterdir()):
        if path.name.endswith(".json"):
            cases.append(json.loads(path.read_text(encoding="utf-8")))
    return cases


async def run_case(api: Any, case: Case) -> dict[str, Any]:
    operation = getattr(api, case["operation"])
    return await operation(**case["input"])
