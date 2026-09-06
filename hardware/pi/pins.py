"""Pin map + panel constants for the Waveshare 1.44" LCD HAT (ST7735S).

All numbers are BCM GPIO. These match the Waveshare 1.44inch LCD HAT wiki
defaults; keep them in one place so a different wiring only touches this file.

Board reference: https://www.waveshare.com/wiki/1.44inch_LCD_HAT
"""
from __future__ import annotations

LCD_SPI_PORT = 0        # SPI0
LCD_SPI_DEVICE = 0      # CE0 (GPIO 8)
LCD_DC = 25             # data/command
LCD_RST = 27            # reset
LCD_BL = 24             # backlight (PWM-capable)
LCD_SPI_HZ = 16_000_000  # ST7735S is happy well above this; 16 MHz is smooth

# Panel geometry. The Waveshare 1.44 is a 128x128 ST7735S. Some panel batches
# need a small pixel offset and/or BGR colour order. If you see a coloured strip
# along an edge or the image is shifted, set these (commonly 1/2 or 2/1). If red
# and blue look swapped, flip LCD_BGR.
LCD_WIDTH = 128
LCD_HEIGHT = 128
LCD_ROTATE = 0          # 0..3 (90° steps)
LCD_H_OFFSET = 0
LCD_V_OFFSET = 0
LCD_BGR = True          # Waveshare panels are typically BGR
LCD_INVERSE = False

# The HAT has a 5-way joystick plus three keys. Logical mapping:
#   joystick        -> UP/DOWN/LEFT/RIGHT/CENTER
#   KEY1            -> BACK
#   KEY2            -> aux (Space while typing)
#   KEY3            -> aux (Delete while typing)
JOY_UP = 6
JOY_DOWN = 19
JOY_LEFT = 5
JOY_RIGHT = 26
JOY_PRESS = 13
KEY1 = 21
KEY2 = 20
KEY3 = 16
