"""Tests for dependency detection, ping helpers, and interface parsing."""
import unittest

from core.dependencies import Dependencies
from network.interfaces import local_ipv4, parse_proc_net_route
from network.ping import PingStats, build_ping_command, parse_rtt, parse_summary


class TestDependencies(unittest.TestCase):
    def test_known_missing_is_false(self):
        deps = Dependencies(tools=("definitely-not-real-xyz",))
        self.assertFalse(deps.has("definitely-not-real-xyz"))
        self.assertIn("definitely-not-real-xyz", deps.missing())

    def test_real_binary_true(self):
        deps = Dependencies(tools=("echo",))
        # echo exists as a binary on essentially every POSIX system
        self.assertTrue(deps.has("echo"))
        self.assertIsInstance(deps.as_dict(), dict)


class TestPingParsing(unittest.TestCase):
    def test_parse_rtt(self):
        self.assertAlmostEqual(parse_rtt("64 bytes from 1.1.1.1: icmp_seq=1 ttl=57 time=12.3 ms"), 12.3)
        self.assertAlmostEqual(parse_rtt("Reply from 1.1.1.1: bytes=32 time<1ms TTL=57"), 1.0)
        self.assertIsNone(parse_rtt("PING 1.1.1.1 (1.1.1.1) 56 data bytes"))

    def test_parse_summary(self):
        line = "3 packets transmitted, 2 received, 33% packet loss, time 2003ms"
        self.assertEqual(parse_summary(line), (3, 2, 33.0))
        self.assertIsNone(parse_summary("not a summary"))

    def test_build_command_has_target(self):
        cmd = build_ping_command("192.168.1.1", count=4)
        self.assertEqual(cmd[0], "ping")
        self.assertEqual(cmd[-1], "192.168.1.1")
        self.assertIn("4", cmd)

    def test_stats_loss_and_avg(self):
        s = PingStats("x")
        for rtt in (10.0, 20.0, 30.0):
            s.add_reply(rtt)
        s.apply_summary(transmitted=4, received=3)
        self.assertEqual(s.loss_pct, 25)
        self.assertEqual(s.avg_ms, 20.0)
        self.assertEqual(s.last_ms, 30.0)

    def test_stats_loss_without_summary(self):
        s = PingStats("x")
        s.add_reply(5.0)
        self.assertEqual(s.loss_pct, 0)


class TestInterfaces(unittest.TestCase):
    SAMPLE = (
        "Iface\tDestination\tGateway\tFlags\tRefCnt\tUse\tMetric\tMask\tMTU\tWindow\tIRTT\n"
        "eth0\t00000000\t010200C0\t0003\t0\t0\t0\t00000000\t0\t0\t0\n"
        "eth0\t000200C0\t00000000\t0001\t0\t0\t0\t00FFFFFF\t0\t0\t0\n"
    )

    def test_parse_default_route(self):
        gw, iface = parse_proc_net_route(self.SAMPLE)
        self.assertEqual(gw, "192.0.2.1")
        self.assertEqual(iface, "eth0")

    def test_parse_no_default_route(self):
        text = "Iface\tDestination\tGateway\tFlags\n" "eth0\t000200C0\t00000000\t0001\n"
        self.assertEqual(parse_proc_net_route(text), (None, None))

    def test_local_ipv4_type(self):
        ip = local_ipv4()  # may be None in a sandbox with no route
        self.assertTrue(ip is None or isinstance(ip, str))


if __name__ == "__main__":
    unittest.main()
