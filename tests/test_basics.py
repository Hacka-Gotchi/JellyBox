"""Basic logic unit tests.

These cover logic that needs no hardware: settings
load/save, menu scrolling, and text truncation. Run with:


"""
import tempfile
import unittest
from pathlib import Path

from core.settings import DEFAULTS, Settings
from ui.components.menu import Menu
from ui.renderer import truncate, wrap



class TestSettings(unittest.TestCase):
    def test_defaults_when_missing(self):
        with tempfile.TemporaryDirectory() as d:
            s = Settings.load(Path(d) / "nope.json")
            self.assertEqual(s.get("theme"), DEFAULTS["theme"])
            self.assertEqual(s.get("brightness"), DEFAULTS["brightness"])

    def test_roundtrip_survives_reload(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "settings.json"
            s = Settings.load(path)
            s.set("theme", "red")
            s.set("brightness", 30)
            s.save()
            reloaded = Settings.load(path)
            self.assertEqual(reloaded.get("theme"), "red")
            self.assertEqual(reloaded.get("brightness"), 30)

    def test_unknown_keys_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "settings.json"
            path.write_text('{"theme": "cyan", "bogus": 123}')
            s = Settings.load(path)
            self.assertEqual(s.get("theme"), "cyan")
            self.assertIsNone(s.get("bogus"))

    def test_corrupt_file_falls_back(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "settings.json"
            path.write_text("{ not valid json")
            s = Settings.load(path)
            self.assertEqual(s.get("theme"), DEFAULTS["theme"])


class TestMenuScrolling(unittest.TestCase):
    def setUp(self):
        self.items = [f"ITEM {i}" for i in range(8)]

    def test_wrap_navigation(self):
        m = Menu(self.items, wrap=True)
        m.up()
        self.assertEqual(m.selected, len(self.items) - 1)
        m.down()
        self.assertEqual(m.selected, 0)

    def test_no_wrap_clamps(self):
        m = Menu(self.items, wrap=False)
        m.up()
        self.assertEqual(m.selected, 0)
        for _ in range(20):
            m.down()
        self.assertEqual(m.selected, len(self.items) - 1)

    def test_viewport_follows_selection(self):
        m = Menu(self.items, wrap=False)
        top, rows = m.visible_slice(4)
        self.assertEqual(top, 0)
        self.assertEqual(len(rows), 4)
        for _ in range(5):
            m.down()  # selected = 5
        top, rows = m.visible_slice(4)
        self.assertTrue(top <= 5 < top + 4)
        self.assertEqual(rows[m.selected - top], "ITEM 5")

    def test_empty_menu_safe(self):
        m = Menu([])
        m.up(); m.down()
        self.assertIsNone(m.current)
        self.assertEqual(m.visible_slice(4), (0, []))


class TestTextHelpers(unittest.TestCase):
    def test_truncate_short_unchanged(self):
        self.assertEqual(truncate("WIFI", 10), "WIFI")

    def test_truncate_adds_ellipsis(self):
        out = truncate("VERY_LONG_NETWORK_NAME", 12)
        self.assertEqual(len(out), 12)
        self.assertTrue(out.endswith("\u2026"))

    def test_wrap_splits_on_words(self):
        lines = wrap("CONNECT POWER NOW PLEASE", 12)
        self.assertTrue(all(len(l) <= 12 for l in lines))
        self.assertEqual(" ".join(lines), "CONNECT POWER NOW PLEASE")

    def test_wrap_hard_splits_long_word(self):
        lines = wrap("AAAAAAAAAAAAAAAAAAAA", 6)
        self.assertTrue(all(len(l) <= 6 for l in lines))


if __name__ == "__main__":
    unittest.main()
