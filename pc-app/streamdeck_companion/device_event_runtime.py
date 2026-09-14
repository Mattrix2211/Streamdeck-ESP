"""Runtime adapters between current ESPHome events and V2 Core events/actions.

This module is deliberately kept outside ``core``: it knows the historical
profile representation and ``profiles.resolve_slot``. ``DeviceClient`` can
therefore migrate to generic ``InputEvent`` objects without forcing an
immediate dashboard_config.yaml migration.
"""

from __future__ import annotations

from collections.abc import Sequence

from .core import InputEvent, InputKind
from . import profiles as profile_utils
from .device_events import legacy_encoder_direction, translate_esphome_event


def resolve_esphome_action(
    profile: dict,
    entity_name: str,
    event_type: str,
    *,
    action_entity_name: str,
    encoder_entity_names: Sequence[str],
) -> dict | None:
    """Bridge the current firmware vocabulary through the generic Core model.

    The current ESPHome event is translated once into ``InputEvent`` and then
    resolved against the existing profile structure. Special UI events that
    are not generic inputs intentionally return ``None`` and remain handled by
    ``DeviceClient`` during the compatibility phase.
    """
    event = translate_esphome_event(
        entity_name,
        event_type,
        action_entity_name=action_entity_name,
        encoder_entity_names=encoder_entity_names,
    )
    if event is None:
        return None
    return resolve_legacy_action(profile, event)


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
