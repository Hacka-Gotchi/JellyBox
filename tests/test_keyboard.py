"""Tests for the on-screen keyboard component."""
import unittest

from ui.components.keyboard import Keyboard, _ROWS


def _goto(kb: Keyboard, ch: str) -> None:
    for r, row in enumerate(_ROWS):
        if ch in row:
            kb.row, kb.col = r, row.index(ch)
            kb.press()
            return
    raise AssertionError(f"key {ch!r} not on keyboard")


def _goto_special(kb: Keyboard, name: str) -> None:
    for r, row in enumerate(_ROWS):
        if name in row:
            kb.row, kb.col = r, row.index(name)
            return
    raise AssertionError(f"special {name!r} not on keyboard")


class TestKeyboard(unittest.TestCase):
    def test_symbols_available(self):
        kb = Keyboard()
        for ch in "1,2":
            _goto(kb, ch)
        self.assertEqual(kb.value(), "1,2")

    def test_type_word(self):
        kb = Keyboard()
        for ch in "pi":
            _goto(kb, ch)
        self.assertEqual(kb.value(), "pi")

    def test_shift_uppercases(self):
        kb = Keyboard()
        _goto_special(kb, "SHIFT")
        kb.press()
        _goto(kb, "a")
        self.assertEqual(kb.value(), "A")

    def test_backspace(self):
        kb = Keyboard("abc")
        _goto_special(kb, "DEL")
        kb.press()
        self.assertEqual(kb.value(), "ab")

    def test_space(self):
        kb = Keyboard("a")
        _goto_special(kb, "SPC")
        kb.press()
        self.assertEqual(kb.value(), "a ")

    def test_ok_sets_done(self):
        kb = Keyboard("x")
        _goto_special(kb, "OK")
        kb.press()
        self.assertTrue(kb.done)

    def test_navigation_wraps_within_row(self):
        kb = Keyboard()
        kb.row, kb.col = 0, 0
        kb.move_h(-1)
        self.assertEqual(kb.col, len(_ROWS[0]) - 1)

    def test_vertical_clamps_col(self):
        kb = Keyboard()
        kb.row, kb.col = 0, 9
        kb.move_v(4)
        self.assertLess(kb.col, len(_ROWS[kb.row]))


if __name__ == "__main__":
    unittest.main()
