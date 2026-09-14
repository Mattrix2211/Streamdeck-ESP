"""Transport-neutral protocol session built on DevicePort and RequestTracker."""

from __future__ import annotations

from .device import DevicePort
from .protocol import MessageType, ProtocolMessage
from .protocol_session import PendingRequest, RequestTracker, RetryPolicy


class ProtocolSession:
    """Coordinate protocol delivery/retries through a concrete DevicePort."""

    def __init__(
        self,
        port: DevicePort,
        *,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.port = port
        self.tracker = RequestTracker(retry_policy)

    def send(self, message: ProtocolMessage, *, expect_response: bool = True) -> None:
        self.port.send(message)
        if expect_response and message.type not in (MessageType.ACK, MessageType.ERROR):
            self.tracker.track(message)

    def receive(self, message: ProtocolMessage) -> PendingRequest | None:
        """Resolve an incoming ACK/ERROR against the pending request set."""
        return self.tracker.resolve(message)

    def retry_due(self) -> tuple[ProtocolMessage, ...]:
        """Resend requests whose timeout elapsed and return the resent messages."""
        messages = self.tracker.due_retries()
        for message in messages:
            self.port.send(message)
        return messages

    def clear(self) -> None:
        self.tracker.clear()
