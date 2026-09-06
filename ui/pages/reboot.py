"""Reboot page.

A confirm screen for rebooting the device. Reboot needs root, so it goes through
the same passwordless-sudo mechanism as the other privileged actions (whitelisted
by scripts/setup-privileges.sh). If that isn't set up, it says so instead of
silently doing nothing.
"""
from __future__ import annotations

from enum import Enum, auto

from hardware.buttons import Button, ButtonEvent
from hardware.display import Display
from ui.components.header import draw_header
from ui.page_manager import Page
from ui.renderer import CONTENT_TOP, PADDING_X, SCREEN_W


class _Mode(Enum):
    CONFIRM = auto()
    WORKING = auto()
    ERROR = auto()


class RebootPage(Page):
    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self.mode = _Mode.CONFIRM
        self.task = None

    def handle_input(self, event: ButtonEvent) -> None:
        btn = event.button
        if self.mode is _Mode.CONFIRM:
            if btn is Button.CENTER:
                self._reboot()
            elif btn is Button.BACK:
                self.ctx.pages.pop()
        elif self.mode is _Mode.ERROR:
            if btn is Button.BACK:
                self.ctx.pages.pop()

    def _reboot(self) -> None:
        self.task = self.ctx.commands.run_async(["sudo", "-n", "systemctl", "reboot"])
        self.mode = _Mode.WORKING

    def update(self) -> None:
        # If the reboot succeeds the process is killed mid-shutdown; if we get
        # here with a finished task, it failed (usually: sudo rule not installed).
        if self.task is not None and self.task.finished:
            self.task = None
            self.mode = _Mode.ERROR

    def draw(self, display: Display) -> None:
        theme = self.ctx.theme
        fg = theme.foreground
        draw_header(display, theme, "REBOOT",
                    wifi=self.ctx.wifi.status if self.ctx.wifi else None)

        if self.mode is _Mode.CONFIRM:
            display.text_center(CONTENT_TOP + 20, "REBOOT DEVICE?", fg)
            display.text(PADDING_X, display.HEIGHT - 10, "OK=YES", fg)
            display.text_right(SCREEN_W - PADDING_X, display.HEIGHT - 10, "BACK=NO", fg)
        elif self.mode is _Mode.WORKING:
            display.text_center(CONTENT_TOP + 24, "REBOOTING...", fg)
        elif self.mode is _Mode.ERROR:
            display.text_center(CONTENT_TOP + 14, "REBOOT FAILED", fg)
            display.text_center(CONTENT_TOP + 28, "RUN SETUP (SSH)", fg)
            display.text(PADDING_X, display.HEIGHT - 10, "BACK", fg)
