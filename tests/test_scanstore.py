"""Tests for saved-scan storage."""
import unittest
from pathlib import Path

import system.scanstore as ss


class TestScanStore(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._orig = ss.SCANS_DIR
        ss.SCANS_DIR = Path(tempfile.mkdtemp())

    def tearDown(self):
        ss.SCANS_DIR = self._orig

    def test_save_list_read_roundtrip(self):
        name = ss.save_scan("nmap", "192.168.1.1", ["22/tcp ssh", "80/tcp http"])
        self.assertIn(name, ss.list_scans())
        text = ss.read_scan(name)
        self.assertTrue(any("22/tcp ssh" in l for l in text))
        self.assertTrue(any("192.168.1.1" in l for l in text))

    def test_target_is_sanitised(self):
        name = ss.save_scan("nmap", "../../etc/passwd", ["x"])
        self.assertNotIn("/", name)
        self.assertTrue(name.endswith(".txt"))

    def test_read_rejects_traversal(self):
        self.assertEqual(ss.read_scan("../secret.txt"), [])

    def test_list_newest_first(self):
        import time
        a = ss.save_scan("nmap", "a", ["1"]); time.sleep(0.02)
        b = ss.save_scan("nmap", "b", ["2"])
        files = ss.list_scans()
        # filenames are timestamped; newest (b) should sort first
        self.assertEqual(files[0], max(a, b))


if __name__ == "__main__":
    unittest.main()
