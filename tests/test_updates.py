"""Tests for update version-compare, tag validation, and release parsing."""
import tempfile
import unittest
from pathlib import Path

from core.device_config import display_overrides, load_device_config
from core.version import read_version_file
from network.updates import (
    is_newer,
    is_valid_tag,
    parse_latest_release,
    releases_api_url,
)


class TestVersionCompare(unittest.TestCase):
    def test_newer(self):
        self.assertTrue(is_newer("v1.0.0", "v1.1.0"))
        self.assertTrue(is_newer("v1.2.9", "v1.3.0"))
        self.assertTrue(is_newer("v1.0.0", "v2.0.0"))

    def test_same_or_older(self):
        self.assertFalse(is_newer("v1.2.0", "v1.2.0"))
        self.assertFalse(is_newer("v1.3.0", "v1.2.0"))

    def test_unknown_current_treats_remote_as_newer(self):
        self.assertTrue(is_newer("unknown", "v1.0.0"))

    def test_unparseable_latest_is_not_newer(self):
        self.assertFalse(is_newer("v1.0.0", "not-a-version"))


class TestTagValidation(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(is_valid_tag("v1.2.3"))
        self.assertTrue(is_valid_tag("v10.0.99"))

    def test_invalid(self):
        for bad in ("1.2.3", "v1.2", "main", "v1.2.3; rm -rf /", "vX.Y.Z", ""):
            self.assertFalse(is_valid_tag(bad), bad)


class TestReleaseParsing(unittest.TestCase):
    def test_parse(self):
        text = '{"tag_name": "v1.3.0", "body": "Fixes and JACK TEST"}'
        release = parse_latest_release(text)
        self.assertEqual(release["tag"], "v1.3.0")
        self.assertIn("JACK TEST", release["notes"])

    def test_parse_no_tag(self):
        self.assertIsNone(parse_latest_release('{"body": "x"}'))

    def test_parse_garbage(self):
        self.assertIsNone(parse_latest_release("not json"))

    def test_api_url(self):
        self.assertEqual(releases_api_url(),
                         "https://api.github.com/repos/Hacka-Gotchi/JellyBox/releases/latest")


class TestDeviceConfig(unittest.TestCase):
    def test_display_overrides(self):
        cfg = {"display": {"x_offset": 1, "y_offset": 2, "rotate": 0}}
        self.assertEqual(display_overrides(cfg)["x_offset"], 1)

    def test_missing_display(self):
        self.assertEqual(display_overrides({}), {})

    def test_load_missing_file_returns_empty(self):
        self.assertEqual(load_device_config(Path("/no/such/device.json")), {})

    def test_load_valid_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "device.json"
            path.write_text('{"display": {"x_offset": 3}}')
            self.assertEqual(display_overrides(load_device_config(path))["x_offset"], 3)


class TestVersionFile(unittest.TestCase):
    def test_read(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "VERSION"
            path.write_text("v1.0.0\n")
            self.assertEqual(read_version_file(path), "v1.0.0")

    def test_missing(self):
        self.assertIsNone(read_version_file(Path("/no/such/VERSION")))


if __name__ == "__main__":
    unittest.main()
