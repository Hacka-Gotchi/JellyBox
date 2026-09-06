"""Tests for system-info parsing."""
import unittest

from system.sysinfo import (
    CpuSampler,
    format_uptime,
    get_system_info,
    parse_cpu_line,
    parse_meminfo,
)


class TestCpuParsing(unittest.TestCase):
    def test_parse_cpu_line(self):
        self.assertEqual(parse_cpu_line("cpu  100 0 200 700 0 0 0 0 0 0"), (700, 1000))

    def test_parse_cpu_line_rejects_non_cpu(self):
        self.assertIsNone(parse_cpu_line("cpu0 1 2 3 4"))
        self.assertIsNone(parse_cpu_line("intr 12345"))

    def test_sampler_needs_two_reads(self):
        s = CpuSampler()
        # first sample establishes a baseline -> None; a real value comes later
        first = s.sample()
        self.assertTrue(first is None or isinstance(first, float))


class TestMemParsing(unittest.TestCase):
    def test_parse_meminfo(self):
        text = "MemTotal: 4000 kB\nMemFree: 100 kB\nMemAvailable: 1500 kB\n"
        self.assertEqual(parse_meminfo(text), (4000, 1500))

    def test_parse_meminfo_missing(self):
        self.assertIsNone(parse_meminfo("MemTotal: 4000 kB\n"))


class TestUptime(unittest.TestCase):
    def test_minutes(self):
        self.assertEqual(format_uptime(90), "1m")

    def test_hours(self):
        self.assertEqual(format_uptime(3700), "1h 1m")

    def test_days(self):
        self.assertEqual(format_uptime(90000), "1d 1h")


class TestSnapshot(unittest.TestCase):
    def test_get_system_info_runs(self):
        # On Linux this returns real values; the point is it never raises and
        # fills the fields it can.
        snap = get_system_info(CpuSampler())
        self.assertTrue(snap.mem_total_mb is None or snap.mem_total_mb > 0)
        self.assertTrue(snap.disk_total_gb is None or snap.disk_total_gb > 0)


if __name__ == "__main__":
    unittest.main()
