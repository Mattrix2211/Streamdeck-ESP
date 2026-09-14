"""Resolve current profile actions from framework-independent input events.

This adapter keeps the existing profile/configuration shape untouched while
letting the device runtime use ``InputEvent`` as its internal vocabulary.
It belongs to the application compatibility layer, not the Core.
"""

from __future__ import annotations

from . import profiles as profile_utils
from .core import InputEvent, InputKind
from .device_events import legacy_encoder_direction


def resolve_legacy_action(profile: dict, event: InputEvent) -> dict | None:
    """Return the current ``{type, target}`` action bound to ``event``.

    The function intentionally reads the existing profile representation so
    no user configuration migration is required during P0.
    """
    if event.kind == InputKind.BUTTON:
        index = event.metadata.get("slot_index")
        if not isinstance(index, int):
            return None
        if not (0 <= index < profile_utils.SLOT_COUNT):
            return None
        return profile_utils.resolve_slot(profile, index).get("action")

    if event.kind == InputKind.ENCODER:
        index = event.metadata.get("encoder_index")
        if not isinstance(index, int):
            return None
        direction = legacy_encoder_direction(event.trigger)
        if direction is None:
            return None
        encoders = profile.get("encoders") or []
        if not (0 <= index < len(encoders)):
            return None
        return (encoders[index] or {}).get(direction)

    return None
