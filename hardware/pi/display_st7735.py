"""ST7735S display driver for the Waveshare 1.44" LCD HAT.

Uses luma.lcd to drive the panel over SPI and a gpiozero PWM output for real
backlight brightness. It subclasses the base :class:`Display`, so all the
drawing lives in the base class -- only ``show`` (push the
buffer to the panel) and brightness (drive the backlight) differ.

luma and gpiozero are only imported here, so the rest of the app -- and the
desktop build -- never needs them.
"""
from __future__ import annotations

import logging
import time

from hardware.display import Display
from hardware.pi import pins

log = logging.getLogger(__name__)


class St7735Display(Display):
    def __init__(self, fps: int = 20, brightness: int = 70) -> None:
        super().__init__()
        # Imported lazily so a missing library gives a clear message rather than
        # breaking module import on non-Pi machines.
        from luma.core.interface.serial import spi
        from luma.lcd.device import st7735
        from gpiozero import PWMLED

        serial = spi(
            port=pins.LCD_SPI_PORT,
            device=pins.LCD_SPI_DEVICE,
            gpio_DC=pins.LCD_DC,
            gpio_RST=pins.LCD_RST,
            bus_speed_hz=pins.LCD_SPI_HZ,
        )
        self._device = st7735(
            serial,
            width=pins.LCD_WIDTH,
            height=pins.LCD_HEIGHT,
            rotate=pins.LCD_ROTATE,
            h_offset=pins.LCD_H_OFFSET,
            v_offset=pins.LCD_V_OFFSET,
            bgr=pins.LCD_BGR,
            inverse=pins.LCD_INVERSE,
        )
        # Backlight on its own PWM pin so brightness is continuous.
        self._backlight = PWMLED(pins.LCD_BL)
        self.set_brightness(brightness)

        self._min_frame = 1.0 / max(1, fps)
        self._last_show = 0.0
        log.info("ST7735S display initialised (%dx%d)", self.WIDTH, self.HEIGHT)

    def set_brightness(self, value: int) -> None:
        super().set_brightness(value)  # keep the stored value in sync
        try:
            self._backlight.value = self.brightness / 100.0
        except Exception:
            log.exception("failed to set backlight")

    def show(self) -> None:
        # Push the raw buffer; the backlight (not pixel dimming) sets brightness.
        try:
            self._device.display(self.buffer)
        except Exception:
            log.exception("display update failed")

        # Cap the frame rate so the loop doesn't spin the CPU.
        now = time.monotonic()
        wait = self._min_frame - (now - self._last_show)
        if wait > 0:
            time.sleep(wait)
        self._last_show = time.monotonic()

    def close(self) -> None:
        try:
            self._backlight.value = 0
            self._backlight.close()
        except Exception:
            pass
        try:
            self._device.cleanup()  # clears panel and releases GPIO
        except Exception:
            pass
