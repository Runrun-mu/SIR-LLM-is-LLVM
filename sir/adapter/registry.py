"""Adapter registry."""

from __future__ import annotations

from sir.adapter.base import Adapter
from sir.adapter.generic import GenericAdapter

_ADAPTERS: dict[str, type[Adapter]] = {
    "generic": GenericAdapter,
}


def get_adapter(name: str = "generic") -> Adapter:
    cls = _ADAPTERS.get(name)
    if cls is None:
        raise ValueError(f"Unknown adapter: {name}. Available: {list(_ADAPTERS)}")
    return cls()


def register_adapter(name: str, cls: type[Adapter]) -> None:
    _ADAPTERS[name] = cls
