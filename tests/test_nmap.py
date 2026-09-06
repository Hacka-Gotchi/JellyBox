"""Tests for the IP editor and nmap parsing."""
import unittest

from network.nmap import build_nmap_command, host_is_up, parse_open_ports, parse_port_line, scan_error
from ui.components.ip_editor import IpEditor


class TestIpEditor(unittest.TestCase):
    def test_set_and_value(self):
        e = IpEditor("10.0.0.5")
        self.assertEqual(e.value(), "10.0.0.5")

    def test_invalid_keeps_default(self):
        e = IpEditor("not.an.ip")
        self.assertEqual(e.value(), "192.168.1.1")

    def test_out_of_range_rejected(self):
        e = IpEditor("300.1.1.1")
        self.assertEqual(e.value(), "192.168.1.1")

    def test_inc_wraps(self):
        e = IpEditor("0.0.0.255")
        e.pos = 3
        e.inc()
        self.assertEqual(e.octets[3], 0)

    def test_dec_wraps(self):
        e = IpEditor("0.0.0.0")
        e.pos = 3
        e.dec()
        self.assertEqual(e.octets[3], 255)

    def test_navigation_wraps(self):
        e = IpEditor()
        e.left()
        self.assertEqual(e.pos, 3)
        e.right()
        self.assertEqual(e.pos, 0)

    def test_can_set_arbitrary_ip(self):
        # the whole point of the fix: reach an IP not in any preset list
        e = IpEditor("192.168.1.1")
        e.pos = 3
        for _ in range(41):
            e.inc()
        self.assertEqual(e.value(), "192.168.1.42")


class TestNmapParsing(unittest.TestCase):
    SAMPLE = (
        "Starting Nmap 7.93\n"
        "Nmap scan report for 192.168.1.1\n"
        "Host is up (0.0021s latency).\n"
        "PORT     STATE  SERVICE\n"
        "22/tcp   open   ssh\n"
        "80/tcp   open   http\n"
        "443/tcp  closed https\n"
        "53/tcp   open   domain\n"
    )

    def test_parse_port_line(self):
        p = parse_port_line("22/tcp   open   ssh")
        self.assertEqual((p.number, p.proto, p.state, p.service), (22, "tcp", "open", "ssh"))

    def test_parse_open_ports_sorted(self):
        ports = parse_open_ports(self.SAMPLE)
        self.assertEqual([p.number for p in ports], [22, 53, 80])  # closed 443 excluded

    def test_host_is_up(self):
        self.assertTrue(host_is_up(self.SAMPLE))
        self.assertFalse(host_is_up("Host seems down"))

    def test_scan_error_bad_arg(self):
        self.assertEqual(scan_error("nmap: unrecognized option '--zz'", 1), "ARG ERROR!")
        self.assertEqual(scan_error("Error #486: Your port specifications are illegal. QUITTING!", 1),
                         "ARG ERROR!")

    def test_scan_error_bad_host(self):
        self.assertEqual(scan_error("Failed to resolve \"nope\".", 1), "BAD HOST")

    def test_scan_error_generic(self):
        self.assertEqual(scan_error("some failure", 2), "SCAN ERROR")

    def test_scan_error_none_on_success(self):
        self.assertIsNone(scan_error(self.SAMPLE, 0))

    def test_build_command(self):
        cmd = build_nmap_command("192.168.1.1")
        self.assertEqual(cmd[0], "nmap")
        self.assertEqual(cmd[-1], "192.168.1.1")
        self.assertIn("-Pn", cmd)

    def test_build_command_custom_args(self):
        cmd = build_nmap_command("10.0.0.1", "-p 22,80 -sV")
        self.assertEqual(cmd, ["nmap", "-p", "22,80", "-sV", "10.0.0.1"])

    def test_build_command_blank_args_falls_back(self):
        cmd = build_nmap_command("10.0.0.1", "")
        self.assertIn("-Pn", cmd)
        self.assertEqual(cmd[-1], "10.0.0.1")


if __name__ == "__main__":
    unittest.main()
