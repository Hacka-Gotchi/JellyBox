"""Tests for WireGuard parsers."""
import unittest

from system.wireguard import parse_active_interfaces, parse_handshake, parse_tunnel_list


class TestWireGuard(unittest.TestCase):
    STATUS = (
        "interface: wg0\n"
        "  public key: abc=\n"
        "  listening port: 51820\n"
        "peer: def=\n"
        "  endpoint: 1.2.3.4:51820\n"
        "  latest handshake: 42 seconds ago\n"
        "  transfer: 1.20 MiB received, 3.40 MiB sent\n"
        "interface: home\n"
        "  public key: ghi=\n"
    )

    def test_parse_list(self):
        self.assertEqual(parse_tunnel_list("wg0\nhome\n\n"), ["home", "wg0"])

    def test_active_interfaces(self):
        self.assertEqual(parse_active_interfaces(self.STATUS), {"wg0", "home"})

    def test_active_empty(self):
        self.assertEqual(parse_active_interfaces(""), set())

    def test_handshake(self):
        self.assertEqual(parse_handshake(self.STATUS, "wg0"), "42 seconds ago")
        self.assertIsNone(parse_handshake(self.STATUS, "home"))  # no handshake line


if __name__ == "__main__":
    unittest.main()
