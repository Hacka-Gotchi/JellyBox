"""SSH info page.

Read-only: shows how to reach THIS device over SSH -- the current username and
the device's current IP, combined as user@ip. It doesn't connect anywhere; it
tells you what to type on another machine to SSH into the JellyBox.
"""
from __future__ import annotations

import getpass
import os

from hardware.buttons import Button, ButtonEvent
from hardware.display import Display
from network.interfaces import local_ipv4
from ui.components.header import draw_header
from ui.page_manager import Page
from ui.renderer import CONTENT_TOP, PADDING_X, SCREEN_W, truncate


def current_user() -> str:
    try:
        return getpass.getuser()
    except Exception:
        return os.environ.get("USER") or os.environ.get("LOGNAME") or "?"


class SshPage(Page):
    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self.user = current_user()
        self.ip: str | None = None

    def on_enter(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        self.ip = local_ipv4()

    def _target(self) -> str:
        return f"{self.user}@{self.ip}" if self.ip else f"{self.user}@?"

    def handle_input(self, event: ButtonEvent) -> None:
        if event.button is Button.BACK:
            self.ctx.pages.pop()
        elif event.button is Button.CENTER:
            self._refresh()

    def draw(self, display: Display) -> None:
        theme = self.ctx.theme
        fg = theme.foreground
        draw_header(
            display, theme, "SSH",
            wifi=self.ctx.wifi.status if self.ctx.wifi else None,
        )
        char_w = max(1, display.measure("0")[0])
        max_chars = (SCREEN_W - PADDING_X) // char_w

        display.text(PADDING_X, CONTENT_TOP, "SSH TO THIS DEVICE", fg)
        display.text(PADDING_X, CONTENT_TOP + 14, truncate(self._target(), max_chars), fg)
        display.hline(CONTENT_TOP + 28, fg)

        y = CONTENT_TOP + 34
        line_h = display.line_height + 4
        display.text(PADDING_X, y, "USER", fg)
        display.text(52, y, truncate(self.user, (SCREEN_W - 52) // char_w), fg)
        y += line_h
        display.text(PADDING_X, y, "IP", fg)
        display.text(52, y, self.ip or "no network", fg)

        display.text_right(SCREEN_W - PADDING_X, display.HEIGHT - 10, "OK=REFRESH", fg)
