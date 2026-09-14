"""Read-only adapter from current profile dictionaries to the V2 Core model."""

from __future__ import annotations

import re
from typing import Any, Mapping

from .core import GridRect, Page, Placement, Profile


def profile_from_legacy(profile: Mapping[str, Any], *, fallback_index: int = 0) -> Profile:
    """Project one current profile into the V2 model without mutating config.

    The current application has one visible grid per profile. During the
    migration that grid becomes the profile home page. Folder/page data will
    be added later while the existing YAML remains readable.
    """
    name = str(profile.get("name") or f"Profil {fallback_index + 1}")
    profile_id = str(profile.get("id") or f"profile-{_stable_fragment(name, fallback_index)}")
    home_page_id = f"{profile_id}:home"

    placements: list[Placement] = []
    for index, slot in enumerate(profile.get("slots") or []):
        library_id = slot.get("library_id")
        if not library_id:
            continue
        grid = slot.get("grid") or {}
        placements.append(
            Placement(
                id=f"{home_page_id}:slot-{index + 1}",
                content_id=str(library_id),
                grid=GridRect(
                    col=int(grid.get("col", 0)),
                    row=int(grid.get("row", 0)),
                    colspan=int(grid.get("colspan", 1)),
                    rowspan=int(grid.get("rowspan", 1)),
                ),
                metadata={"legacy_slot_index": index},
            )
        )

    home_page = Page(
        id=home_page_id,
        name="Accueil",
        placements=tuple(placements),
        metadata={"legacy_single_page": True},
    )
    return Profile(
        id=profile_id,
        name=name,
        pages=(home_page,),
        home_page_id=home_page_id,
        trigger=profile.get("trigger"),
        metadata={"legacy_adapter": True},
    )


def _stable_fragment(name: str, fallback_index: int) -> str:
    fragment = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return fragment or str(fallback_index + 1)
