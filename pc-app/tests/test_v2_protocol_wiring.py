from __future__ import annotations

from pathlib import Path
import unittest


class V2ProtocolWiringTests(unittest.TestCase):
    def test_v2_device_client_owns_live_port_and_protocol_session(self) -> None:
        source = (
            Path(__file__).parents[1]
            / "streamdeck_companion"
            / "v2_device_client.py"
        ).read_text(encoding="utf-8")

        self.assertIn("self.device_port = build_esphome_device_port(self)", source)
        self.assertIn("self.protocol_session = ProtocolSession(self.device_port)", source)
        self.assertIn("def send_protocol", source)
        self.assertIn("expect_response: bool = False", source)


if __name__ == "__main__":
    unittest.main()
