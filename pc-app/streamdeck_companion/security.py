"""Host-side security helpers. Secrets never belong in the Core or firmware."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Protocol


REDACTED = "***"
SENSITIVE_KEYS = frozenset({"token", "password", "secret", "api_key", "access_token", "refresh_token"})


class SecretStore(Protocol):
    def get(self, key: str) -> str | None: ...


class EnvironmentSecretStore:
    """Read secrets from process environment without persisting plaintext."""

    def __init__(self, *, prefix: str = "STREAMDECK_") -> None:
        self.prefix = prefix

    def get(self, key: str) -> str | None:
        if not key:
            raise ValueError("secret key cannot be empty")
        env_key = self.prefix + key.upper().replace(".", "_").replace("-", "_")
        return os.getenv(env_key)


def redact_mapping(values: Mapping[str, object]) -> dict[str, object]:
    """Return a logging-safe copy with common secret fields recursively redacted."""

    result: dict[str, object] = {}
    for key, value in values.items():
        normalized = key.casefold()
        if normalized in SENSITIVE_KEYS or normalized.endswith("_token") or normalized.endswith("_password"):
            result[key] = REDACTED
        elif isinstance(value, Mapping):
            result[key] = redact_mapping(value)
        elif isinstance(value, list):
            result[key] = [redact_mapping(item) if isinstance(item, Mapping) else item for item in value]
        else:
            result[key] = value
    return result


def require_secret(store: SecretStore, key: str) -> str:
    value = store.get(key)
    if not value:
        raise RuntimeError(f"required secret is not configured: {key}")
    return value
