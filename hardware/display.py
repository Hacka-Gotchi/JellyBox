"""Display abstraction.

Pages never talk to a specific LCD driver. They draw onto a ``Display``, which
owns a 128x128 RGB pixel buffer (a Pillow image). ``show()`` pushes that buffer
to the physical panel; the base class is a headless no-op used by the tests, and
the Pi driver subclass sends the buffer over SPI.

This module has no GPIO/SPI dependency, so it imports on any machine and the
drawing code can be unit-tested without hardware.
"""
from __future__ import annotations

import logging

from PIL import Image, ImageDraw, ImageFont

from ui.theme import RGB, BLACK

log = logging.getLogger(__name__)

SCREEN_W = 128
SCREEN_H = 128


def _load_font() -> ImageFont.ImageFont:
    """Load a compact, non-antialiased bitmap font.

    Pillow's built-in default bitmap font is ~6px wide and crisp, which suits a
    128x128 terminal aesthetic and needs no font files shipped with the app.
    """
    try:
        return ImageFont.load_default()
    except Exception:  # pragma: no cover - extremely unlikely
        return ImageFont.load_default()


class Display:
    """A drawable 128x128 framebuffer.

    Concrete subclasses only need to override :meth:`show` (and usually
    :meth:`close`). All drawing is done here, once, for every backend.
    """

    WIDTH = SCREEN_W
    HEIGHT = SCREEN_H

    def __init__(self) -> None:
        self._img = Image.new("RGB", (self.WIDTH, self.HEIGHT), BLACK)
        self._draw = ImageDraw.Draw(self._img)
        self._font = _load_font()
        self._brightness = 100
        try:
            ascent, descent = self._font.getmetrics()
            self._line_h = ascent + descent
        except Exception:
            self._line_h = 11

    @property
    def line_height(self) -> int:
        return self._line_h

    def measure(self, text: str) -> tuple[int, int]:
        """Return the (width, height) of ``text`` in pixels."""
        try:
            w = int(self._draw.textlength(text, font=self._font))
        except Exception:
            w = len(text) * 6
        return w, self._line_h

    def clear(self, color: RGB = BLACK) -> None:
        self._draw.rectangle((0, 0, self.WIDTH, self.HEIGHT), fill=color)

    def text(self, x: int, y: int, text: str, color: RGB) -> None:
        self._draw.text((x, y), text, fill=color, font=self._font)

    def text_right(self, x_right: int, y: int, text: str, color: RGB) -> None:
        """Draw ``text`` so its right edge sits at ``x_right``."""
        w, _ = self.measure(text)
        self._draw.text((x_right - w, y), text, fill=color, font=self._font)

    def text_center(self, y: int, text: str, color: RGB) -> None:
        w, _ = self.measure(text)
        self._draw.text(((self.WIDTH - w) // 2, y), text, fill=color, font=self._font)

    def line(self, x1: int, y1: int, x2: int, y2: int, color: RGB, width: int = 1) -> None:
        self._draw.line((x1, y1, x2, y2), fill=color, width=width)

    def hline(self, y: int, color: RGB, x0: int = 0, x1: int | None = None) -> None:
        self._draw.line((x0, y, self.WIDTH if x1 is None else x1, y), fill=color)

    def rect(self, x1: int, y1: int, x2: int, y2: int, color: RGB,
             fill: RGB | None = None, width: int = 1) -> None:
        self._draw.rectangle((x1, y1, x2, y2), outline=color, fill=fill, width=width)

    def set_brightness(self, value: int) -> None:
        """Set brightness 0-100. Applied when the frame is shown."""
        self._brightness = max(0, min(100, int(value)))

    @property
    def brightness(self) -> int:
        return self._brightness

    @property
    def buffer(self) -> Image.Image:
        """The 128x128 RGB frame. The Pi driver pushes this over SPI and sets
        brightness with the backlight, so pixel values aren't dimmed here."""
        return self._img

    def show(self) -> None:
        """Push the current buffer to the panel. Base class does nothing."""

    def close(self) -> None:  # pragma: no cover - trivial
        """Release the panel. Safe to call more than once."""
