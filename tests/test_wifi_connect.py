"""Tests for WiFi connect + status parsing."""
import unittest

from network.wifi import build_connect_command, connect_ok
from network.wifi_status import WifiManager, is_wired_link, parse_proc_wireless
from tests.mocks import FakeWifiProvider


class TestConnectCommand(unittest.TestCase):
    def test_secured(self):
        cmd = build_connect_command("HomeNet", "s3cret", "wlan0")
        self.assertEqual(cmd[:5], ["nmcli", "device", "wifi", "connect", "HomeNet"])
        self.assertIn("password", cmd)
        self.assertIn("s3cret", cmd)
        self.assertIn("ifname", cmd)
        self.assertIn("wlan0", cmd)

    def test_open_no_password(self):
        cmd = build_connect_command("CoffeeShop")
        self.assertNotIn("password", cmd)

    def test_connect_ok(self):
        self.assertTrue(connect_ok("Device 'wlan0' successfully activated with 'x'."))
        self.assertFalse(connect_ok("Error: Secrets were required but not provided."))


class TestWirelessStatus(unittest.TestCase):
    SAMPLE = (
        "Inter-| sta-|   Quality        |   Discarded packets\n"
        " face | sta | link level noise |  nwid  crypt\n"
        " wlan0: 0000   65.  -45.  -256        0      0\n"
    )

    def test_parse_connected(self):
        st = parse_proc_wireless(self.SAMPLE)
        self.assertTrue(st.connected)
        self.assertTrue(0 < st.quality <= 100)
        self.assertEqual(st.iface, "wlan0")

    def test_parse_no_wifi(self):
        st = parse_proc_wireless("Inter-|\n face |\n")
        self.assertFalse(st.connected)

    def test_eth_status_field(self):
        mgr = WifiManager(FakeWifiProvider(connected=False, eth=True))
        self.assertTrue(mgr.status.eth)
        self.assertFalse(mgr.status.connected)

    def test_manager_caches(self):
        mgr = WifiManager(FakeWifiProvider(connected=True, quality=70))
        self.assertTrue(mgr.status.connected)
        self.assertEqual(mgr.status.quality, 70)


class TestWiredLink(unittest.TestCase):
    def test_physical_link_with_carrier_is_wired(self):
        self.assertTrue(is_wired_link(has_wireless=False, has_device=True, carrier="1"))

    def test_wireless_interface_is_not_wired(self):
        self.assertFalse(is_wired_link(has_wireless=True, has_device=True, carrier="1"))

    def test_virtual_interface_without_device_is_not_wired(self):
        self.assertFalse(is_wired_link(has_wireless=False, has_device=False, carrier="1"))

    def test_no_carrier_is_not_wired(self):
        self.assertFalse(is_wired_link(has_wireless=False, has_device=True, carrier="0"))


if __name__ == "__main__":
    unittest.main()
