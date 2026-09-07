"""Tests for JACK TEST parsers and helpers."""
import unittest

from network.jacktest import (
    JackResult,
    build_device_show_command,
    build_lldp_command,
    build_vlan_command,
    dhcp_status,
    format_speed,
    lldp_switch_info,
    parse_nmcli_device,
    summary_line,
)


class TestFormatSpeed(unittest.TestCase):
    def test_values(self):
        self.assertEqual(format_speed(10), "10M")
        self.assertEqual(format_speed(100), "100M")
        self.assertEqual(format_speed(1000), "1G")
        self.assertEqual(format_speed(2500), "2.5G")

    def test_unknown(self):
        self.assertEqual(format_speed(None), "?")
        self.assertEqual(format_speed(-1), "?")


class TestNmcliDevice(unittest.TestCase):
    DHCP = (
        "IP4.ADDRESS[1]:10.20.4.57/24\n"
        "IP4.GATEWAY:10.20.4.1\n"
        "DHCP4.OPTION[1]:requested_subnet_mask = 1\n"
        "DHCP4.OPTION[2]:ip_address = 10.20.4.57\n"
    )
    STATIC = "IP4.ADDRESS[1]:192.168.1.5/24\nIP4.GATEWAY:192.168.1.1\n"

    def test_dhcp_lease(self):
        info = parse_nmcli_device(self.DHCP)
        self.assertEqual(info["ip"], "10.20.4.57")
        self.assertEqual(info["gateway"], "10.20.4.1")
        self.assertTrue(info["dhcp"])
        self.assertEqual(dhcp_status(info["ip"], info["dhcp"]), "YES")

    def test_static(self):
        info = parse_nmcli_device(self.STATIC)
        self.assertEqual(info["ip"], "192.168.1.5")
        self.assertFalse(info["dhcp"])
        self.assertEqual(dhcp_status(info["ip"], info["dhcp"]), "STATIC")

    def test_no_address(self):
        info = parse_nmcli_device("")
        self.assertIsNone(info["ip"])
        self.assertEqual(dhcp_status(info["ip"], info["dhcp"]), "NONE")


class TestLldpSwitchInfo(unittest.TestCase):
    SAMPLE = (
        "lldp.eth0.chassis.name=SW-F3-02\n"
        "lldp.eth0.port.descr=Gi1/0/24\n"
        "lldp.eth0.vlan.vlan-id=120\n"
    )

    def test_matches_interface(self):
        name, port = lldp_switch_info(self.SAMPLE, "eth0")
        self.assertEqual(name, "SW-F3-02")
        self.assertEqual(port, "Gi1/0/24")

    def test_no_neighbors(self):
        self.assertEqual(lldp_switch_info("", "eth0"), (None, None))

    def test_falls_back_to_first_neighbor(self):
        name, port = lldp_switch_info(self.SAMPLE, "eth99")
        self.assertEqual(name, "SW-F3-02")


class TestCommandBuilders(unittest.TestCase):
    def test_device_show(self):
        cmd = build_device_show_command("eth0")
        self.assertEqual(cmd[0], "nmcli")
        self.assertEqual(cmd[-1], "eth0")
        self.assertIn("DHCP4.OPTION", ",".join(cmd))

    def test_lldp(self):
        self.assertEqual(build_lldp_command(), ["lldpctl", "-f", "keyvalue"])

    def test_vlan_uses_sniff_helper(self):
        cmd = build_vlan_command("eth0")
        self.assertEqual(cmd[:3], ["sudo", "-n", "/usr/local/sbin/jellybox-sniff"])
        self.assertEqual(cmd[-2:], ["vlan", "eth0"])


class TestSummaryLine(unittest.TestCase):
    def test_full_switch_port_vlan(self):
        r = JackResult(link=True, switch_name="SW-03", switch_port="Gi1/0/17",
                       vlans=[120])
        self.assertEqual(summary_line(r), "SW-03 / Gi1/0/17 / VLAN 120")

    def test_multiple_vlans(self):
        r = JackResult(link=True, switch_name="SW-03", vlans=[10, 20])
        self.assertEqual(summary_line(r), "SW-03 / VLAN 10,20")

    def test_falls_back_to_ip_without_lldp(self):
        r = JackResult(link=True, ip="10.20.4.57")
        self.assertEqual(summary_line(r), "10.20.4.57")

    def test_link_only(self):
        self.assertEqual(summary_line(JackResult(link=True)), "LINK UP")
        self.assertEqual(summary_line(JackResult(link=False)), "LINK DOWN")

    def test_with_location_label(self):
        r = JackResult(link=True, switch_name="SW-03", switch_port="Gi1/0/17",
                       vlans=[120])
        self.assertEqual(summary_line(r, "Room 205"),
                         "Room 205 / SW-03 / Gi1/0/17 / VLAN 120")


if __name__ == "__main__":
    unittest.main()
