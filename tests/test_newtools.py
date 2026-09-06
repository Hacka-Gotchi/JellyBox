"""Tests for the new TOOLS parsers (traceroute/lldp/vlan/connections)."""
import unittest

from network.connections import build_delete_connection_command, parse_wifi_connections
from network.lldp import parse_lldp
from network.traceroute import build_traceroute_command
from network.vlan import parse_vlan_ids


class TestTraceroute(unittest.TestCase):
    def test_build(self):
        cmd = build_traceroute_command("8.8.8.8")
        self.assertEqual(cmd[0], "traceroute")
        self.assertEqual(cmd[-1], "8.8.8.8")
        self.assertIn("-n", cmd)


class TestLldp(unittest.TestCase):
    SAMPLE = (
        "lldp.eth0.chassis.name=core-switch\n"
        "lldp.eth0.port.descr=GigabitEthernet0/1\n"
        "lldp.eth0.vlan.vlan-id=100\n"
        "lldp.eth0.chassis.mgmt-ip=10.0.0.1\n"
    )

    def test_parse(self):
        n = parse_lldp(self.SAMPLE)
        self.assertEqual(len(n), 1)
        self.assertEqual(n[0]["name"], "core-switch")
        self.assertEqual(n[0]["vlan"], "100")
        self.assertEqual(n[0]["mgmt"], "10.0.0.1")
        self.assertIn("Gigabit", n[0]["port"])

    def test_empty(self):
        self.assertEqual(parse_lldp(""), [])


class TestVlan(unittest.TestCase):
    def test_parse_ids(self):
        text = ("12:00 aa > bb, 802.1Q vlan 100, p 0, ethertype IPv4\n"
                "12:01 cc > dd, 802.1Q vlan 200, p 0, ethertype ARP\n"
                "12:02 ee > ff, 802.1Q vlan 100, ...\n")
        self.assertEqual(parse_vlan_ids(text), [100, 200])

    def test_none(self):
        self.assertEqual(parse_vlan_ids("no tags here"), [])


class TestConnections(unittest.TestCase):
    def test_parse_wifi(self):
        text = ("Wired connection 1:802-3-ethernet\n"
                "homeland:802-11-wireless\n"
                "cafe\\:wifi:802-11-wireless\n")
        self.assertEqual(parse_wifi_connections(text), ["homeland", "cafe:wifi"])

    def test_delete_cmd(self):
        cmd = build_delete_connection_command("homeland")
        self.assertEqual(cmd, ["nmcli", "connection", "delete", "homeland"])


if __name__ == "__main__":
    unittest.main()
