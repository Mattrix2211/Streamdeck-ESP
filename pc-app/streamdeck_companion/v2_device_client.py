"""Progressive V2 runtime wrapper around the historical DeviceClient.

The existing DeviceClient remains the hardware/ESPHome implementation during
P0. This subclass narrows the migration surface to two already-tested V2
adapters: generic event/action resolution and centralized connection state.
All special UI behavior, Home Assistant effects and firmware compatibility stay
in the historical implementation.
"""

from __future__ import annotations

from .device_client import ACTION_EVENT_ENTITY, ENCODER_EVENT_ENTITIES, DeviceClient
from .device_event_runtime import resolve_esphome_action
from .runtime_state import STATE_STORE
from .state_adapters import update_device_connection


class V2DeviceClient(DeviceClient):
    """DeviceClient using V2 adapters without changing the ESPHome transport."""

    @property
    def connected(self) -> bool:
        return getattr(self, "_v2_connected", False)

    @connected.setter
    def connected(self, value: bool) -> None:
        connected = bool(value)
        self._v2_connected = connected
        update_device_connection(STATE_STORE, connected)

    def _resolve_action(self, entity_name: str, event_type: str) -> dict | None:
        """Resolve current config through ESPHome -> Core -> legacy bridge."""
        return resolve_esphome_action(
            self._active_profile(),
            entity_name,
            event_type,
            action_entity_name=ACTION_EVENT_ENTITY,
            encoder_entity_names=ENCODER_EVENT_ENTITIES,
        )
