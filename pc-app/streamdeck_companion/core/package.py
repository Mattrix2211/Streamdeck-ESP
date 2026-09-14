from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


PACKAGE_FORMAT = "streamdeck-esp"
PACKAGE_VERSION = 1


class PackageValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ProfilePackage:
    profile: Mapping[str, Any]
    pages: tuple[Mapping[str, Any], ...] = ()
    folders: tuple[Mapping[str, Any], ...] = ()
    actions: tuple[Mapping[str, Any], ...] = ()
    widgets: tuple[Mapping[str, Any], ...] = ()
    assets: Mapping[str, str] = field(default_factory=dict)
    settings: Mapping[str, Any] = field(default_factory=dict)
    format: str = PACKAGE_FORMAT
    version: int = PACKAGE_VERSION

    def __post_init__(self) -> None:
        if self.format != PACKAGE_FORMAT:
            raise PackageValidationError(f"unsupported package format: {self.format!r}")
        if self.version != PACKAGE_VERSION:
            raise PackageValidationError(f"unsupported package version: {self.version!r}")
        if not self.profile:
            raise PackageValidationError("profile payload cannot be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": self.format,
            "version": self.version,
            "profile": dict(self.profile),
            "pages": [dict(item) for item in self.pages],
            "folders": [dict(item) for item in self.folders],
            "actions": [dict(item) for item in self.actions],
            "widgets": [dict(item) for item in self.widgets],
            "assets": dict(self.assets),
            "settings": dict(self.settings),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProfilePackage":
        if data.get("format") != PACKAGE_FORMAT:
            raise PackageValidationError("invalid .streamdeck package format")
        if data.get("version") != PACKAGE_VERSION:
            raise PackageValidationError("unsupported .streamdeck package version")
        profile = data.get("profile")
        if not isinstance(profile, Mapping):
            raise PackageValidationError("profile must be a mapping")
        return cls(
            profile=profile,
            pages=_mapping_tuple(data.get("pages"), "pages"),
            folders=_mapping_tuple(data.get("folders"), "folders"),
            actions=_mapping_tuple(data.get("actions"), "actions"),
            widgets=_mapping_tuple(data.get("widgets"), "widgets"),
            assets=_mapping(data.get("assets"), "assets"),
            settings=_mapping(data.get("settings"), "settings"),
        )


def _mapping_tuple(value: object, field_name: str) -> tuple[Mapping[str, Any], ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise PackageValidationError(f"{field_name} must be a list")
    if not all(isinstance(item, Mapping) for item in value):
        raise PackageValidationError(f"{field_name} items must be mappings")
    return tuple(value)


def _mapping(value: object, field_name: str) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise PackageValidationError(f"{field_name} must be a mapping")
    return value
