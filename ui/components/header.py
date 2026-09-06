"""Shared page header: title on the left, connection icons on the right.

Drawing these here keeps them consistent across every page. The connection
icons (Ethernet plug, Wi-Fi bars) reflect the cached network status.
"""
from __future__ import annotations

from hardware.display import Display
from network.wifi_status import WifiStatus
from ui.renderer import HEADER_H, PADDING_X, SCREEN_W, truncate
from ui.theme import Theme

_WIFI_W = 12
_ETH_W = 12


def _draw_wifi_icon(display: Display, x: int, y: int, quality: int, color) -> None:
    filled = 0 if quality <= 0 else (1 if quality < 34 else (2 if quality < 67 else 3))
    bar_w, gap = 3, 1
    base = y + 12
    for i in range(3):
        height = 3 + i * 3
        bx = x + i * (bar_w + gap)
        if i < filled:
            display.rect(bx, base - height, bx + bar_w, base, color, fill=color)
        else:
            display.rect(bx, base - height, bx + bar_w, base, color)


def _draw_eth_icon(display: Display, x: int, y: int, color) -> None:
    display.rect(x, y + 2, x + 10, y + 9, color)                  # plug body
    for pin_x in (x + 2, x + 5, x + 8):
        display.line(pin_x, y + 4, pin_x, y + 6, color)
    display.rect(x + 4, y + 9, x + 6, y + 11, color, fill=color)  # locking tab


def draw_header(display: Display, theme: Theme, title: str,
                wifi: WifiStatus | None = None) -> None:
    fg = theme.foreground
    y = 2
    right = SCREEN_W - PADDING_X

    if wifi is not None and wifi.connected:
        _draw_wifi_icon(display, right - _WIFI_W, y, wifi.quality, fg)
        right -= _WIFI_W + 3
    if wifi is not None and wifi.eth:
        _draw_eth_icon(display, right - _ETH_W, y, fg)
        right -= _ETH_W + 3

    char_w = max(1, display.measure("0")[0])
    max_chars = max(1, (right - PADDING_X) // char_w)
    display.text(PADDING_X, y, truncate(title, max_chars), fg)
    display.hline(HEADER_H, fg)
