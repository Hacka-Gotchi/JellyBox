"""System Info page.

A live monitor: CPU load, SoC temperature, memory, disk, uptime, and load
average, refreshed about once a second. CPU/memory/disk get a small bar so the
level reads at a glance; the rest are plain values. Anything the hardware can't
report (e.g. no thermal sensor on a desktop) shows as ``N/A``.
"""
from __future__ import annotations

import time

from hardware.buttons import Button, ButtonEvent
from hardware.display import Display
from system.sysinfo import CpuSampler, SystemSnapshot, format_uptime, get_system_info
from ui.components.header import draw_header
from ui.page_manager import Page
from ui.renderer import CONTENT_TOP, PADDING_X, SCREEN_W, truncate

_REFRESH_S = 1.0
_ROW_H = 13
_BAR_X0 = 34
_BAR_X1 = 96


class SystemInfoPage(Page):
    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self._sampler = CpuSampler()
        self._snap = SystemSnapshot()
        self._last = 0.0

    def on_enter(self) -> None:
        self._sampler.sample()  # prime the CPU baseline
        self._refresh()

    def _refresh(self) -> None:
        self._snap = get_system_info(self._sampler)
        self._last = time.monotonic()

    def update(self) -> None:
        if time.monotonic() - self._last >= _REFRESH_S:
            self._refresh()

    def handle_input(self, event: ButtonEvent) -> None:
        if event.button is Button.BACK:
            self.ctx.pages.pop()
        elif event.button is Button.CENTER:
            self._refresh()

    def draw(self, display: Display) -> None:
        theme = self.ctx.theme
        draw_header(
            display, theme, "SYSTEM INFO",
            wifi=self.ctx.wifi.status if self.ctx.wifi else None,
        )
        fg = theme.foreground
        s = self._snap
        y = CONTENT_TOP

        y = self._bar_row(display, fg, y, "CPU", s.cpu_pct)
        y = self._bar_row(display, fg, y, "MEM", s.mem_pct)
        y = self._bar_row(display, fg, y, "DISK", s.disk_pct)
        y = self._text_row(display, fg, y, "TEMP",
                           f"{s.temp_c:g}C" if s.temp_c is not None else "N/A")
        y = self._text_row(display, fg, y, "UP",
                           format_uptime(s.uptime_s) if s.uptime_s is not None else "N/A")
        y = self._text_row(display, fg, y, "LOAD",
                           f"{s.load1:g}" if s.load1 is not None else "N/A")
        y = self._text_row(display, fg, y, "HOST", s.hostname or "-")

    def _bar_row(self, display, fg, y, label, pct):
        display.text(PADDING_X, y, label, fg)
        if pct is None:
            display.text(_BAR_X0, y, "--", fg)
        else:
            display.rect(_BAR_X0, y + 1, _BAR_X1, y + display.line_height - 1, fg)
            frac = max(0.0, min(1.0, pct / 100.0))
            fill_w = int((_BAR_X1 - _BAR_X0 - 2) * frac)
            if fill_w > 0:
                display.rect(_BAR_X0 + 1, y + 2,
                             _BAR_X0 + 1 + fill_w, y + display.line_height - 2,
                             fg, fill=fg)
            display.text_right(SCREEN_W - PADDING_X, y, f"{round(pct)}%", fg)
        return y + _ROW_H

    def _text_row(self, display, fg, y, label, value):
        display.text(PADDING_X, y, label, fg)
        char_w = max(1, display.measure("0")[0])
        max_chars = (SCREEN_W - PADDING_X - _BAR_X0) // char_w
        display.text(_BAR_X0, y, truncate(value, max_chars), fg)
        return y + _ROW_H
