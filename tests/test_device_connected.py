"""«Подключено» in the cabinet only for a device whose key actually carried traffic."""
import unittest
from datetime import datetime, timezone

from app.web import device_connected


class DeviceConnectedTest(unittest.TestCase):
    def test_fresh_key_is_not_connected(self):
        self.assertFalse(device_connected({"panel_status": "ACTIVE"}))
        self.assertFalse(device_connected({"lifetime_traffic_bytes": 0, "used_traffic_bytes": None, "last_online_at": None}))

    def test_online_or_traffic_means_connected(self):
        now = datetime.now(timezone.utc)
        self.assertTrue(device_connected({"last_online_at": now}))
        self.assertTrue(device_connected({"legacy_last_online_at": now}))
        self.assertTrue(device_connected({"lifetime_traffic_bytes": 1024}))
        self.assertTrue(device_connected({"used_traffic_bytes": 5}))


if __name__ == "__main__":
    unittest.main()
