from __future__ import annotations

import unittest

from streamdeck_companion.core.protocol import MessageType, ProtocolMessage
from streamdeck_companion.esphome_port_runtime import (
    RuntimePayloadError,
    build_esphome_device_port,
)


class FakeRuntime:
    connected = True

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def schedule_set_active_profile(self, name: str, timeout: float = 5.0) -> None:
        self.calls.append(("profile", name, timeout))

    def schedule_push(self, timeout: float = 5.0) -> None:
        self.calls.append(("sync", timeout))

    def schedule_navigation(
        self,
        command: str,
        target: str | None = None,
        timeout: float = 5.0,
    ) -> str:
        self.calls.append(("navigation", command, target, timeout))
        return target or command


class ESPHomePortRuntimeTests(unittest.TestCase):
    def test_set_profile_routes_to_thread_safe_runtime(self) -> None:
        runtime = FakeRuntime()
        port = build_esphome_device_port(runtime)
        port.send(ProtocolMessage(MessageType.SET_PROFILE, {"profile_name": "Gaming"}))
        self.assertEqual(runtime.calls, [("profile", "Gaming", 5.0)])

    def test_set_profile_accepts_profile_id_for_progressive_compatibility(self) -> None:
        runtime = FakeRuntime()
        port = build_esphome_device_port(runtime)
        port.send(ProtocolMessage(MessageType.SET_PROFILE, {"profile_id": "Bureau"}))
        self.assertEqual(runtime.calls[0][:2], ("profile", "Bureau"))

    def test_set_page_routes_to_v2_navigation(self) -> None:
        runtime = FakeRuntime()
        port = build_esphome_device_port(runtime)
        port.send(ProtocolMessage(MessageType.SET_PAGE, {"page_id": "media"}))
        self.assertEqual(runtime.calls, [("navigation", "go_to", "media", 5.0)])

    def test_sync_reuses_existing_full_push(self) -> None:
        runtime = FakeRuntime()
        port = build_esphome_device_port(runtime)
        port.send(ProtocolMessage(MessageType.SYNC, {}))
        self.assertEqual(runtime.calls, [("sync", 5.0)])

    def test_invalid_runtime_payload_fails_explicitly(self) -> None:
        runtime = FakeRuntime()
        port = build_esphome_device_port(runtime)
        with self.assertRaises(RuntimePayloadError):
            port.send(ProtocolMessage(MessageType.SET_PAGE, {}))


if __name__ == "__main__":
    unittest.main()
