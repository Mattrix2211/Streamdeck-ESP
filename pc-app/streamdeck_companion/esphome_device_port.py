"""ESPHome-backed DevicePort for the current Streamdeck-ESP hardware.

This adapter exposes the existing runtime through the transport-neutral V2
DevicePort contract. It intentionally supports only the protocol messages that
can be represented safely with the current ESPHome entities; unsupported V2
messages fail explicitly instead of being silently dropped.
"""

from __future__ import annotations

from collections.abc import Callable

from .core.device import DeviceCapability, DeviceDescriptor, DevicePort, DisplaySpec
from .core.protocol import MessageType, ProtocolMessage


STREAMDECK_ESP_DESCRIPTOR = DeviceDescriptor(
    id="streamdeck-esp",
    name="Streamdeck-ESP",
    model="ESP32-P4/C6 7in",
    display=DisplaySpec(width=1024, height=600),
    encoder_count=3,
    capabilities=frozenset(
        {
            DeviceCapability.DISPLAY,
            DeviceCapability.TOUCH,
            DeviceCapability.ENCODERS,
        }
    ),
)


class UnsupportedDeviceMessageError(ValueError):
    """Raised when the legacy ESPHome transport cannot represent a V2 message."""


class ESPHomeDevicePort(DevicePort):
    """Expose a live DeviceClient through the V2 DevicePort contract."""

    def __init__(
        self,
        device_client: object,
        *,
        state_sender: Callable[[dict[str, object]], None] | None = None,
        sync_sender: Callable[[], None] | None = None,
    ) -> None:
        self._device_client = device_client
        self._state_sender = state_sender
        self._sync_sender = sync_sender

    @property
    def descriptor(self) -> DeviceDescriptor:
        return STREAMDECK_ESP_DESCRIPTOR

    @property
    def connected(self) -> bool:
        return bool(getattr(self._device_client, "connected", False))

    def send(self, message: ProtocolMessage) -> None:
        """Project supported V2 messages onto the current runtime.

        The current firmware does not yet consume a generic protocol envelope.
        During migration we only bridge the two semantics already available in
        the runtime: UPDATE_STATE and SYNC. Other message types remain explicit
        migration work and raise UnsupportedDeviceMessageError.
        """
        if message.type == MessageType.UPDATE_STATE:
            if self._state_sender is None:
                raise UnsupportedDeviceMessageError("UPDATE_STATE sender is not configured")
            self._state_sender(dict(message.payload))
            return

        if message.type == MessageType.SYNC:
            if self._sync_sender is None:
                raise UnsupportedDeviceMessageError("SYNC sender is not configured")
            self._sync_sender()
            return

        raise UnsupportedDeviceMessageError(
            f"message {message.type.value!r} is not supported by the current ESPHome transport"
        )
