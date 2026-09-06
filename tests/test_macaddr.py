"""Tests for MAC address helpers."""
import unittest

from system.macaddr import is_valid_mac, parse_ethtool_permanent, random_mac


class TestMac(unittest.TestCase):
    def test_random_mac_is_valid(self):
        for _ in range(50):
            self.assertTrue(is_valid_mac(random_mac()))

    def test_random_mac_locally_administered(self):
        # first octet must have the LA bit set and multicast bit clear
        first = int(random_mac().split(":")[0], 16)
        self.assertEqual(first & 0x03, 0x02)

    def test_valid_mac(self):
        self.assertTrue(is_valid_mac("00:c0:ca:b9:a9:fc"))
        self.assertTrue(is_valid_mac("AA:BB:CC:DD:EE:FF"))

    def test_invalid_mac(self):
        self.assertFalse(is_valid_mac("00:c0:ca:b9:a9"))     # too short
        self.assertFalse(is_valid_mac("gg:c0:ca:b9:a9:fc"))  # bad hex
        self.assertFalse(is_valid_mac("00c0cab9a9fc"))       # no colons

    def test_parse_ethtool_permanent(self):
        out = "Permanent address: 88:a2:9e:79:0e:06\n"
        self.assertEqual(parse_ethtool_permanent(out), "88:a2:9e:79:0e:06")
        self.assertIsNone(parse_ethtool_permanent("no perm here"))


if __name__ == "__main__":
    unittest.main()
