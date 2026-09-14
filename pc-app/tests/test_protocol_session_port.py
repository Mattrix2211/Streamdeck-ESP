from __future__ import annotations

import unittest

from streamdeck_companion.core.device import DeviceCapability, DeviceDescriptor
from streamdeck_companion.core.protocol import MessageType, ProtocolMessage
from streamdeck_companion.core.protocol_session import RetryPolicy
from streamdeck_companion.core.session import ProtocolSession


class FakePort:
    def __init__(self) -> None:
        self.sent: list[ProtocolMessage] = []
        self._connected = True
        self._descriptor = DeviceDescriptor(
            id="fake",
            name="Fake Device",
            capabilities=frozenset({DeviceCapability.TOUCH}),
        )

    @property
    def descriptor(self) -> DeviceDescriptor:
        return self._descriptor

    @property
    def connected(self) -> bool:
        return self._connected

    def send(self, message: ProtocolMessage) -> None:
        self.sent.append(message)


class ProtocolSessionTests(unittest.TestCase):
    def test_send_tracks_request(self) -> None:
        port = FakePort()
        session = ProtocolSession(port)
        message = ProtocolMessage(MessageType.PING, {})
        session.send(message)
        self.assertEqual(port.sent, [message])
        self.assertEqual(session.tracker.pending()[0].message, message)

    def test_send_can_skip_tracking(self) -> None:
        port = FakePort()
        session = ProtocolSession(port)
        message = ProtocolMessage(MessageType.UPDATE_STATE, {"value": 1})
        session.send(message, expect_response=False)
        self.assertEqual(port.sent, [message])
        self.assertEqual(session.tracker.pending(), ())

    def test_receive_resolves_ack(self) -> None:
        port = FakePort()
        session = ProtocolSession(port)
        message = ProtocolMessage(MessageType.PING, {})
        session.send(message)
        pending = session.receive(message.ack())
        self.assertIsNotNone(pending)
        self.assertEqual(pending.message, message)
        self.assertEqual(session.tracker.pending(), ())

    def test_retry_due_resends_through_same_port(self) -> None:
        now = [0.0]
        port = FakePort()
        session = ProtocolSession(port, retry_policy=RetryPolicy(timeout_seconds=1.0, max_retries=1))
        session.tracker._clock = lambda: now[0]
        message = ProtocolMessage(MessageType.PING, {})
        session.send(message)
        now[0] = 1.1
        retried = session.retry_due()
        self.assertEqual(retried, (message,))
        self.assertEqual(port.sent, [message, message])


if __name__ == "__main__":
    unittest.main()
