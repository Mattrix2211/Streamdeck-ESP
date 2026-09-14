from __future__ import annotations

import unittest

from streamdeck_companion.core.device import DeviceCapability
from streamdeck_companion.core.protocol import MessageType, ProtocolMessage
from streamdeck_companion.esphome_device_port import (
    ESPHomeDevicePort,
    STREAMDECK_ESP_DESCRIPTOR,
    UnsupportedDeviceMessageError,
)


class FakeClient:
    connected = True


class ESPHomeDevicePortTests(unittest.TestCase):
    def test_descriptor_matches_current_hardware(self) -> None:
        descriptor = STREAMDECK_ESP_DESCRIPTOR
        self.assertEqual(descriptor.display.width, 1024)
        self.assertEqual(descriptor.display.height, 600)
        self.assertEqual(descriptor.encoder_count, 3)
        self.assertTrue(descriptor.supports(DeviceCapability.TOUCH))
        self.assertTrue(descriptor.supports(DeviceCapability.ENCODERS))

    def test_connected_tracks_wrapped_client(self) -> None:
        client = FakeClient()
        port = ESPHomeDevicePort(client)
        self.assertTrue(port.connected)
        client.connected = False
        self.assertFalse(port.connected)

    def test_update_state_uses_injected_sender(self) -> None:
        sent: list[dict[str, object]] = []
        port = ESPHomeDevicePort(FakeClient(), state_sender=sent.append)
        message = ProtocolMessage(
            MessageType.UPDATE_STATE,
            {"state_id": "device:streamdeck", "value": True},
        )
        port.send(message)
        self.assertEqual(sent, [{"state_id": "device:streamdeck", "value": True}])

    def test_sync_uses_injected_sender(self) -> None:
        calls: list[str] = []
        port = ESPHomeDevicePort(FakeClient(), sync_sender=lambda: calls.append("sync"))
        port.send(ProtocolMessage(MessageType.SYNC, {}))
        self.assertEqual(calls, ["sync"])

    def test_unsupported_message_fails_explicitly(self) -> None:
        port = ESPHomeDevicePort(FakeClient())
        with self.assertRaises(UnsupportedDeviceMessageError):
            port.send(ProtocolMessage(MessageType.SET_PAGE, {"page_id": "main"}))


if __name__ == "__main__":
    unittest.main()
