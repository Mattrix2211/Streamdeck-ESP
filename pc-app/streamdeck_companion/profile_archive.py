from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

ARCHIVE_FORMAT = "streamdeck-esp-profile"
ARCHIVE_VERSION = 1
MANIFEST_NAME = "manifest.json"
PROFILE_NAME = "profile.json"
ASSET_PREFIX = "assets/"


class ProfileArchiveError(ValueError):
    pass


def export_profile(
    profile: Mapping[str, Any],
    destination: str | Path,
    *,
    assets: Mapping[str, bytes] | None = None,
) -> Path:
    path = Path(destination)
    if path.suffix != ".streamdeck":
        path = path.with_suffix(".streamdeck")
    manifest = {
        "format": ARCHIVE_FORMAT,
        "version": ARCHIVE_VERSION,
        "profile_name": str(profile.get("name") or "Profile"),
        "assets": sorted((assets or {}).keys()),
    }
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(MANIFEST_NAME, json.dumps(manifest, ensure_ascii=False, indent=2))
        archive.writestr(PROFILE_NAME, json.dumps(dict(profile), ensure_ascii=False, indent=2))
        for name, content in (assets or {}).items():
            safe_name = _safe_asset_name(name)
            archive.writestr(f"{ASSET_PREFIX}{safe_name}", content)
    return path


def import_profile(source: str | Path) -> tuple[dict[str, Any], dict[str, bytes]]:
    try:
        with ZipFile(Path(source), "r") as archive:
            names = set(archive.namelist())
            if MANIFEST_NAME not in names or PROFILE_NAME not in names:
                raise ProfileArchiveError("archive is missing manifest.json or profile.json")
            manifest = json.loads(archive.read(MANIFEST_NAME).decode("utf-8"))
            _validate_manifest(manifest)
            profile = json.loads(archive.read(PROFILE_NAME).decode("utf-8"))
            if not isinstance(profile, dict):
                raise ProfileArchiveError("profile.json must contain an object")
            assets: dict[str, bytes] = {}
            for name in names:
                if not name.startswith(ASSET_PREFIX) or name.endswith("/"):
                    continue
                relative = name[len(ASSET_PREFIX) :]
                safe_name = _safe_asset_name(relative)
                assets[safe_name] = archive.read(name)
            return profile, assets
    except (BadZipFile, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ProfileArchiveError("invalid .streamdeck archive") from exc


def _validate_manifest(manifest: object) -> None:
    if not isinstance(manifest, dict):
        raise ProfileArchiveError("manifest must be an object")
    if manifest.get("format") != ARCHIVE_FORMAT:
        raise ProfileArchiveError("unsupported archive format")
    if manifest.get("version") != ARCHIVE_VERSION:
        raise ProfileArchiveError(f"unsupported archive version: {manifest.get('version')!r}")


def _safe_asset_name(name: str) -> str:
    path = PurePosixPath(name.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ProfileArchiveError(f"unsafe asset path: {name!r}")
    normalized = str(path)
    if normalized in {".", ""}:
        raise ProfileArchiveError(f"unsafe asset path: {name!r}")
    return normalized
