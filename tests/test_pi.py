"""Tests for Pi pin-map wiring (no hardware libraries required)."""
import unittest

from hardware.buttons import Button
from hardware.pi import pins
from hardware.pi.buttons_gpio import PIN_MAP


class TestButtonPinMap(unittest.TestCase):
    def test_core_buttons_mapped(self):
        mapped = set(PIN_MAP.values())
        for required in (Button.UP, Button.DOWN, Button.LEFT, Button.RIGHT,
                         Button.CENTER, Button.BACK):
            self.assertIn(required, mapped)

    def test_pins_are_unique(self):
        pin_numbers = list(PIN_MAP.keys())
        self.assertEqual(len(pin_numbers), len(set(pin_numbers)))

    def test_display_pins_distinct_from_buttons(self):
        button_pins = set(PIN_MAP.keys())
        display_pins = {pins.LCD_DC, pins.LCD_RST, pins.LCD_BL}
        self.assertEqual(button_pins & display_pins, set())


if __name__ == "__main__":
    unittest.main()
