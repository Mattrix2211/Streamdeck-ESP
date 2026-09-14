"""Portable, versioned profile bundles for Streamdeck-ESP.

The format is deliberately independent from Flask and ESPHome so profiles can
be shared, backed up and migrated without coupling the Core to the UI or
hardware. Files use the ``.streamdeck`` extension and contain UTF-8 JSON.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

FORMAT_NAME = "streamdeck-esp-profile"
FORMAT_VERSION = 1


class ProfileTransferError(ValueError):
    """Raised when a portable profile bundle is malformed or unsupported."""


@dataclass(frozen=True, slots=True)
class ProfileBundle:
    profile: dict[str, Any]
    format_version: int = FORMAT_VERSION
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": FORMAT_NAME,
            "format_version": self.format_version,
            "profile": deepcopy(self.profile),
            "metadata": deepcopy(self.metadata or {}),
        }


def export_profile(profile: Mapping[str, Any], *, metadata: Mapping[str, Any] | None = None) -> str:
    """Serialize one profile into the portable .streamdeck JSON format."""
    normalized = _validate_profile(profile)
    bundle = ProfileBundle(normalized, metadata=dict(metadata or {}))
    return json.dumps(bundle.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


def export_profile_file(
    profile: Mapping[str, Any],
    path: str | Path,
    *,
    metadata: Mapping[str, Any] | None = None,
) -> Path:
    target = Path(path)
    if target.suffix.lower() != ".streamdeck":
        target = target.with_suffix(".streamdeck")
    target.write_text(export_profile(profile, metadata=metadata), encoding="utf-8")
    return target


def import_profile(raw: str | bytes | Mapping[str, Any]) -> dict[str, Any]:
    """Load and migrate a portable bundle to the current profile dictionary."""
    if isinstance(raw, Mapping):
        data = dict(raw)
    else:
        try:
            data = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProfileTransferError("invalid .streamdeck JSON") from exc
    migrated = migrate_bundle(data)
    return _validate_profile(migrated["profile"])


def import_profile_file(path: str | Path) -> dict[str, Any]:
    return import_profile(Path(path).read_text(encoding="utf-8"))


def migrate_bundle(data: Mapping[str, Any]) -> dict[str, Any]:
    """Migrate an older portable bundle without mutating its source mapping."""
    if data.get("format") != FORMAT_NAME:
        raise ProfileTransferError("unsupported profile bundle format")
    try:
        version = int(data.get("format_version", 0))
    except (TypeError, ValueError) as exc:
        raise ProfileTransferError("invalid format_version") from exc
    if version <= 0:
        raise ProfileTransferError("format_version must be positive")
    if version > FORMAT_VERSION:
        raise ProfileTransferError(
            f"bundle version {version} is newer than supported version {FORMAT_VERSION}"
        )
    current = deepcopy(dict(data))
    # Version 1 is the first public format. Future migrations are intentionally
    # chained here (v1 -> v2 -> v3) so old exports remain importable.
    current["format_version"] = FORMAT_VERSION
    current.setdefault("metadata", {})
    return current


def merge_imported_profile(
    profiles: list[dict[str, Any]],
    imported: Mapping[str, Any],
    *,
    replace_existing: bool = False,
) -> list[dict[str, Any]]:
    """Return a new profile list with deterministic collision handling."""
    result = deepcopy(profiles)
    profile = _validate_profile(imported)
    name = str(profile["name"])
    for index, existing in enumerate(result):
        if str(existing.get("name") or "") != name:
            continue
        if replace_existing:
            result[index] = profile
            return result
        profile["name"] = _unique_name(name, {str(item.get("name") or "") for item in result})
        break
    result.append(profile)
    return result


def _unique_name(base: str, existing: set[str]) -> str:
    suffix = 2
    candidate = f"{base} ({suffix})"
    while candidate in existing:
        suffix += 1
        candidate = f"{base} ({suffix})"
    return candidate


def _validate_profile(profile: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(profile, Mapping):
        raise ProfileTransferError("profile must be an object")
    normalized = deepcopy(dict(profile))
    name = str(normalized.get("name") or "").strip()
    if not name:
        raise ProfileTransferError("profile name cannot be empty")
    normalized["name"] = name
    for key in ("slots", "library", "pages", "folders", "encoders"):
        value = normalized.get(key)
        if value is not None and not isinstance(value, list):
            raise ProfileTransferError(f"profile field {key!r} must be a list")
    return normalized
