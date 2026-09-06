"""Tests for device discovery, action menu, and interface persistence."""
import tempfile
import unittest
from pathlib import Path

from core.settings import Settings
from hardware.buttons import Button, ButtonEvent, InputSource, PressKind
from system.devices import (
    NetIface,
    UsbDevice,
    classify_iface,
    list_network_interfaces,
    list_usb_devices,
    mode_from_arphrd,
)
from ui.pages.device_actions import DeviceActionPage
from ui.theme import Theme
from tests.mocks import make_context


class TestClassifyIface(unittest.TestCase):
    def test_loopback(self):
        self.assertEqual(classify_iface("lo", False, False), "loopback")

    def test_wifi(self):
        self.assertEqual(classify_iface("wlan1", True, True), "wifi")

    def test_ethernet(self):
        self.assertEqual(classify_iface("eth0", False, True), "ethernet")

    def test_other(self):
        self.assertEqual(classify_iface("veth0", False, False), "other")


class TestModeMapping(unittest.TestCase):
    def test_monitor(self):
        self.assertEqual(mode_from_arphrd("803"), "monitor")

    def test_managed(self):
        self.assertEqual(mode_from_arphrd("1"), "managed")
        self.assertEqual(mode_from_arphrd(" 1 "), "managed")


class TestListing(unittest.TestCase):
    def test_interfaces_runs(self):
        ifaces = list_network_interfaces()
        self.assertTrue(all(i.kind != "loopback" for i in ifaces))

    def test_usb_runs(self):
        self.assertIsInstance(list_usb_devices(), list)


class TestInterfacePersistence(unittest.TestCase):
    def test_wifi_interface_survives_reload(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "settings.json"
            s = Settings.load(path)
            s.set("wifi_interface", "wlan1")
            s.save()
            self.assertEqual(Settings.load(path).get("wifi_interface"), "wlan1")


def _ctx():
    return make_context()


class TestDeviceActions(unittest.TestCase):
    def test_wifi_iface_actions(self):
        ctx = _ctx()
        iface = NetIface("wlan1", "wifi", "down", "00:c0:ca:b9:a9:fc")
        page = DeviceActionPage(ctx, "iface", iface)
        labels = [a[0] for a in page._actions]
        self.assertIn("USE FOR SCAN", labels)
        self.assertIn("SCAN NOW", labels)
        self.assertIn("DETAILS", labels)
        self.assertTrue(any(l.startswith("MONITOR") for l in labels))

    def test_ethernet_actions_details_only(self):
        ctx = _ctx()
        page = DeviceActionPage(ctx, "iface", NetIface("eth0", "ethernet", "up", None))
        self.assertEqual([a[0] for a in page._actions], ["DETAILS"])

    def test_usb_actions_details_only(self):
        ctx = _ctx()
        page = DeviceActionPage(ctx, "usb", UsbDevice("802.11ac NIC", "0bda", "a811"))
        self.assertEqual([a[0] for a in page._actions], ["DETAILS"])

    def test_use_for_scan_toggles_and_relabels(self):
        ctx = _ctx()
        iface = NetIface("wlan1", "wifi", "down", None)
        page = DeviceActionPage(ctx, "iface", iface)
        page._toggle_scan()
        self.assertEqual(ctx.settings.get("wifi_interface"), "wlan1")
        self.assertIn("UNSELECT", [a[0] for a in page._actions])
        page._toggle_scan()
        self.assertIsNone(ctx.settings.get("wifi_interface"))

    def test_details_mode_toggles(self):
        ctx = _ctx()
        page = DeviceActionPage(ctx, "usb", UsbDevice("Hub", "05e3", "0610"))
        # select the DETAILS action (only one) and press CENTER
        page.handle_input(ButtonEvent(Button.CENTER, PressKind.SHORT))
        self.assertEqual(len(page._detail_lines()), 3)


if __name__ == "__main__":
    unittest.main()

