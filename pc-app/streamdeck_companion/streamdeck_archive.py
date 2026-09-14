from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from .core.package import ProfilePackage


MANIFEST_NAME = "manifest.json"


class StreamdeckArchiveError(ValueError):
    pass


def export_streamdeck(package: ProfilePackage, destination: str | Path) -> Path:
    path = Path(destination)
    if path.suffix != ".streamdeck":
        path = path.with_suffix(".streamdeck")
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(
            MANIFEST_NAME,
            json.dumps(package.to_dict(), ensure_ascii=False, indent=2),
        )
    return path


def import_streamdeck(source: str | Path) -> ProfilePackage:
    path = Path(source)
    try:
        with ZipFile(path, "r") as archive:
            names = set(archive.namelist())
            if MANIFEST_NAME not in names:
                raise StreamdeckArchiveError("missing manifest.json")
            raw = archive.read(MANIFEST_NAME)
    except (BadZipFile, OSError) as exc:
        raise StreamdeckArchiveError(str(exc)) from exc
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StreamdeckArchiveError("invalid manifest.json") from exc
    if not isinstance(payload, dict):
        raise StreamdeckArchiveError("manifest root must be an object")
    return ProfilePackage.from_dict(payload)
