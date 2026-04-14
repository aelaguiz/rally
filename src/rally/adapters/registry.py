from __future__ import annotations

from rally.errors import RallyConfigError

from rally.adapters.base import RallyAdapter
from rally.adapters.claude_code.adapter import CLAUDE_CODE_ADAPTER
from rally.adapters.codex.adapter import CODEX_ADAPTER

_ADAPTERS: dict[str, RallyAdapter] = {
    CODEX_ADAPTER.name: CODEX_ADAPTER,
    CLAUDE_CODE_ADAPTER.name: CLAUDE_CODE_ADAPTER,
}


def get_adapter(name: str) -> RallyAdapter:
    adapter = _ADAPTERS.get(name)
    if adapter is None:
        supported = ", ".join(f"`{item}`" for item in sorted(_ADAPTERS))
        raise RallyConfigError(f"Unsupported `runtime.adapter` value `{name}`. Supported values: {supported}.")
    return adapter


def supported_adapter_names() -> tuple[str, ...]:
    return tuple(sorted(_ADAPTERS))
