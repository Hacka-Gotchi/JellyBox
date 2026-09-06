"""Tests for the Settings page."""
import unittest

from core.settings import Settings
from hardware.buttons import Button, ButtonEvent, PressKind
from tests.mocks import make_context
from ui.pages.settings import SettingsPage


def _make_page():
    ctx = make_context()
    page = SettingsPage(ctx)
    ctx.pages.push(page)
    return page, ctx


def _press(page, btn):
    page.handle_input(ButtonEvent(btn, PressKind.SHORT))


class TestSettingsPage(unittest.TestCase):
    def test_theme_change_applies_and_persists(self):
        page, ctx = _make_page()
        start = ctx.theme.name
        _press(page, Button.RIGHT)  # row 0 is THEME
        self.assertNotEqual(ctx.theme.name, start)
        self.assertEqual(Settings.load(ctx.settings.path).get("theme"), ctx.theme.name)

    def test_brightness_clamps_and_steps(self):
        page, ctx = _make_page()
        _press(page, Button.DOWN)  # move to BRIGHT row
        for _ in range(20):
            _press(page, Button.LEFT)
        self.assertGreaterEqual(ctx.settings.get("brightness"), 10)
        for _ in range(20):
            _press(page, Button.RIGHT)
        self.assertLessEqual(ctx.settings.get("brightness"), 100)

    def test_back_pops(self):
        page, ctx = _make_page()
        self.assertEqual(ctx.pages.depth, 1)
        _press(page, Button.BACK)
        self.assertEqual(ctx.pages.depth, 0)


if __name__ == "__main__":
    unittest.main()
