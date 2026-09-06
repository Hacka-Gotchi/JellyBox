"""Saved scans viewer (TOOLS -> SCANS).

Lists scans saved from the Nmap screen and opens one in a scrollable view.
"""
from __future__ import annotations

from enum import Enum, auto

from hardware.buttons import Button, ButtonEvent
from hardware.display import Display
from system.scanstore import list_scans, read_scan
from ui.components.header import draw_header
from ui.components.scroll_view import ScrollView
from ui.page_manager import Page
from ui.renderer import CONTENT_TOP, PADDING_X, SCREEN_W, truncate

_ROW_H = 12


class _Mode(Enum):
    LIST = auto()
    VIEW = auto()


class SavedScansPage(Page):
    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self.files: list[str] = []
        self._cursor = 0
        self._scroll = 0
        self.mode = _Mode.LIST
        self.view = ScrollView()

    def on_enter(self) -> None:
        self.files = list_scans()
        self._cursor = min(self._cursor, max(0, len(self.files) - 1))

    def handle_input(self, event: ButtonEvent) -> None:
        btn = event.button
        if self.mode is _Mode.VIEW:
            if btn is Button.BACK:
                self.mode = _Mode.LIST
            elif btn is Button.UP:
                self.view.up()
            elif btn is Button.DOWN:
                self.view.down()
            return
        if btn is Button.BACK:
            self.ctx.pages.pop()
        elif btn is Button.DOWN and self.files:
            self._cursor = min(self._cursor + 1, len(self.files) - 1)
        elif btn is Button.UP:
            self._cursor = max(self._cursor - 1, 0)
        elif btn is Button.CENTER and self.files:
            self.view.set_lines(read_scan(self.files[self._cursor]))
            self.mode = _Mode.VIEW

    def draw(self, display: Display) -> None:
        theme = self.ctx.theme
        fg = theme.foreground
        title = "RESULT" if self.mode is _Mode.VIEW else "RESULTS"
        draw_header(display, theme, title,
                    wifi=self.ctx.wifi.status if self.ctx.wifi else None)

        if self.mode is _Mode.VIEW:
            self.view.draw(display, theme, CONTENT_TOP, display.HEIGHT - 10)
            display.text(PADDING_X, display.HEIGHT - 10, "BACK", fg)
            return

        if not self.files:
            display.text_center(CONTENT_TOP + 24, "NO SAVED SCANS", fg)
            display.text(PADDING_X, display.HEIGHT - 10, "BACK", fg)
            return

        footer_y = display.HEIGHT - 10
        rows = max(1, (footer_y - CONTENT_TOP) // _ROW_H)
        if self._cursor < self._scroll:
            self._scroll = self._cursor
        elif self._cursor >= self._scroll + rows:
            self._scroll = self._cursor - rows + 1
        char_w = max(1, display.measure("0")[0])
        max_chars = (SCREEN_W - PADDING_X) // char_w - 1

        y = CONTENT_TOP
        for i in range(self._scroll, min(self._scroll + rows, len(self.files))):
            cursor = ">" if i == self._cursor else " "
            label = self.files[i].replace(".txt", "")
            display.text(PADDING_X, y, cursor + truncate(label, max_chars), fg)
            y += _ROW_H
        display.text_right(SCREEN_W - PADDING_X, footer_y, "OK=VIEW", fg)
