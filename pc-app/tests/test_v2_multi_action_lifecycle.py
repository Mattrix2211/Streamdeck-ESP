from __future__ import annotations

import unittest

from streamdeck_companion.device_client import DeviceClient
from streamdeck_companion.v2_device_client import V2DeviceClient


class V2MultiActionLifecycleTests(unittest.TestCase):
    def test_reconnect_loop_keeps_deviceclient_run_forever_lifecycle(self) -> None:
        """A reconnect must not shut down the V2 Multi Action worker pool.

        The tray reuses the same V2DeviceClient instance after run_forever()
        returns. Keeping the inherited lifecycle prevents a per-disconnect
        shutdown from making later Multi Actions unusable.
        """
        self.assertIs(V2DeviceClient.run_forever, DeviceClient.run_forever)


if __name__ == "__main__":
    unittest.main()
