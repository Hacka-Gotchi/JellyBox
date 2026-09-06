"""Tests for Wi-Fi nmcli parsing."""
import unittest

from network.wifi import (
    parse_active,
    parse_scan_output,
    parse_wifi_line,
    split_terse,
)

# Realistic `nmcli -t -f IN-USE,SSID,SIGNAL,SECURITY device wifi list` output.
SAMPLE = (
    "*:HomeNet:82:WPA2\n"
    ":Neighbour\\: Wifi:47:WPA1 WPA2\n"      # escaped colon inside the SSID
    ":CoffeeShop:63:\n"                        # open network (empty security)
    ":HomeNet:40:WPA2\n"                       # weaker duplicate of HomeNet
    ":: 12:WPA2\n"                             # hidden / empty SSID -> skipped
)


class TestSplitTerse(unittest.TestCase):
    def test_unescapes_colon(self):
        self.assertEqual(split_terse("a:b\\:c:d"), ["a", "b:c", "d"])


class TestParseLine(unittest.TestCase):
    def test_secured_in_use(self):
        n = parse_wifi_line("*:HomeNet:82:WPA2")
        self.assertEqual(n.ssid, "HomeNet")
        self.assertEqual(n.signal, 82)
        self.assertTrue(n.in_use)
        self.assertTrue(n.secured)

    def test_open_network(self):
        n = parse_wifi_line(":CoffeeShop:63:")
        self.assertFalse(n.secured)
        self.assertFalse(n.in_use)


class TestParseScan(unittest.TestCase):
    def setUp(self):
        self.nets = parse_scan_output(SAMPLE)

    def test_dedup_keeps_strongest(self):
        home = [n for n in self.nets if n.ssid == "HomeNet"]
        self.assertEqual(len(home), 1)
        self.assertEqual(home[0].signal, 82)

    def test_sorted_by_signal(self):
        signals = [n.signal for n in self.nets]
        self.assertEqual(signals, sorted(signals, reverse=True))

    def test_hidden_skipped(self):
        self.assertTrue(all(n.ssid for n in self.nets))

    def test_escaped_ssid_preserved(self):
        self.assertIn("Neighbour: Wifi", [n.ssid for n in self.nets])


class TestParseActive(unittest.TestCase):
    def test_finds_in_use(self):
        self.assertEqual(parse_active(SAMPLE), ("HomeNet", 82))

    def test_none_when_no_active(self):
        self.assertEqual(parse_active(":Foo:50:WPA2\n"), (None, None))


if __name__ == "__main__":
    unittest.main()
