from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from .state import StateStore, StateValue


class StateProvider(Protocol):
    @property
    def provider_id(self) -> str: ...

    def refresh(self) -> Iterable[StateValue]: ...


class ProviderManager:
    def __init__(self, store: StateStore) -> None:
        self.store = store
        self._providers: dict[str, StateProvider] = {}

    def register(self, provider: StateProvider) -> None:
        if not provider.provider_id:
            raise ValueError("provider_id cannot be empty")
        if provider.provider_id in self._providers:
            raise ValueError(f"provider already registered: {provider.provider_id!r}")
        self._providers[provider.provider_id] = provider

    def unregister(self, provider_id: str) -> None:
        self._providers.pop(provider_id, None)

    def refresh(self, provider_id: str | None = None) -> tuple[StateValue, ...]:
        providers = (
            (self._providers[provider_id],)
            if provider_id is not None and provider_id in self._providers
            else tuple(self._providers.values()) if provider_id is None else ()
        )
        if provider_id is not None and not providers:
            raise KeyError(provider_id)
        values: list[StateValue] = []
        for provider in providers:
            for state in provider.refresh():
                self.store.set(state)
                values.append(state)
        return tuple(values)

    def list(self) -> tuple[StateProvider, ...]:
        return tuple(self._providers.values())
