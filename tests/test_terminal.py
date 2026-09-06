"""Tests for the terminal command console."""
import time
import unittest

from tests.mocks import make_context
from ui.pages.terminal import TerminalPage, _Mode


def _ctx():
    return make_context()


class TestTerminal(unittest.TestCase):
    def test_scrollback_capped(self):
        page = TerminalPage(_ctx())
        for i in range(900):
            page._push(f"line {i}")
        self.assertLessEqual(len(page.lines), 400)
        self.assertEqual(page.lines[-1], "line 899")

    def test_run_command_captures_output(self):
        page = TerminalPage(_ctx())
        page._run("echo hello-term")
        self.assertEqual(page.mode, _Mode.RUNNING)
        for _ in range(200):
            page.update()
            if page.mode is _Mode.VIEW:
                break
            time.sleep(0.01)
        self.assertEqual(page.mode, _Mode.VIEW)
        self.assertIn("$ echo hello-term", page.lines)
        self.assertTrue(any("hello-term" in ln for ln in page.lines))

    def test_failed_command_shows_exit_code(self):
        page = TerminalPage(_ctx())
        page._run("exit 3")
        for _ in range(200):
            page.update()
            if page.mode is _Mode.VIEW:
                break
            time.sleep(0.01)
        self.assertIn("[exit 3]", page.lines)


if __name__ == "__main__":
    unittest.main()
