"""Runtime adapter from generic Core input events to current profile actions.

This module is deliberately kept outside ``core``: it knows the historical
profile representation and ``profiles.resolve_slot``.  ``DeviceClient`` can
therefore migrate to generic ``InputEvent`` objects without forcing an
immediate dashboard_config.yaml migration.
"""

from __future__ import annotations

from .core import InputEvent, InputKind
from . import profiles as profile_utils
from .device_events import legacy_encoder_direction


def resolve_legacy_action(profile: dict, event: InputEvent) -> dict | None:
    """Resolve the configured legacy action for a generic input event.

    Button events use ``slot_index`` metadata produced by ``device_events``.
    Encoder events use ``encoder_index`` plus the Core trigger converted back
    to the current encoder direction key during the compatibility phase.
    Unknown/incomplete events simply resolve to ``None``.
    """
    if event.kind == InputKind.BUTTON:
        index = _metadata_index(event, "slot_index")
        if index is None or not (0 <= index < profile_utils.SLOT_COUNT):
            return None
        return profile_utils.resolve_slot(profile, index).get("action")

    if event.kind == InputKind.ENCODER:
        index = _metadata_index(event, "encoder_index")
        direction = legacy_encoder_direction(event.trigger)
        if index is None or direction is None:
            return None
        encoders = profile.get("encoders") or []
        if not (0 <= index < len(encoders)):
            return None
        return (encoders[index] or {}).get(direction)

    return None


def _metadata_index(event: InputEvent, key: str) -> int | None:
    value = event.metadata.get(key)
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
