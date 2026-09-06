"""Saved Networks page (SETTINGS -> NETWORKS).

Lists saved Wi-Fi connections (NetworkManager) and lets you forget one. Uses
nmcli, authorized by the same polkit rule as Wi-Fi connect.
"""
from __future__ import annotations

from enum import Enum, auto

from hardware.buttons import Button, ButtonEvent
from hardware.display import Display
from network.connections import (
    build_delete_connection_command,
    build_list_connections_command,
    parse_wifi_connections,
)
from ui.components.header import draw_header
from ui.page_manager import Page
from ui.renderer import CONTENT_TOP, PADDING_X, SCREEN_W, truncate

_ROW_H = 12


class _Mode(Enum):
    LIST = auto()
    CONFIRM = auto()
    WORKING = auto()
    EMPTY = auto()


class SavedNetworksPage(Page):
    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self.names: list[str] = []
        self._cursor = 0
        self._scroll = 0
        self.mode = _Mode.LIST
        self.task = None

    def on_enter(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        res = self.ctx.commands.run(build_list_connections_command(), timeout=4)
        self.names = parse_wifi_connections(res.stdout) if res.ok else []
        self._cursor = min(self._cursor, max(0, len(self.names) - 1))
        self.mode = _Mode.LIST if self.names else _Mode.EMPTY

    def handle_input(self, event: ButtonEvent) -> None:
        btn = event.button
        if self.mode is _Mode.WORKING:
            return
        if self.mode is _Mode.EMPTY:
            if btn is Button.BACK:
                self.ctx.pages.pop()
            return
        if self.mode is _Mode.CONFIRM:
            if btn is Button.CENTER:
                self._delete(self.names[self._cursor])
            elif btn is Button.BACK:
                self.mode = _Mode.LIST
            return
        if btn is Button.BACK:
            self.ctx.pages.pop()
        elif btn is Button.DOWN:
            self._cursor = min(self._cursor + 1, len(self.names) - 1)
        elif btn is Button.UP:
            self._cursor = max(self._cursor - 1, 0)
        elif btn is Button.CENTER:
            self.mode = _Mode.CONFIRM

    def _delete(self, name: str) -> None:
        self.task = self.ctx.commands.run_async(build_delete_connection_command(name))
        self.mode = _Mode.WORKING

    def update(self) -> None:
        if self.task is not None and self.task.finished:
            self.task = None
            self._refresh()

    def draw(self, display: Display) -> None:
        theme = self.ctx.theme
        fg = theme.foreground
        draw_header(display, theme, "NETWORKS",
                    wifi=self.ctx.wifi.status if self.ctx.wifi else None)

        if self.mode is _Mode.EMPTY:
            display.text_center(CONTENT_TOP + 24, "NO SAVED NETWORKS", fg)
            display.text(PADDING_X, display.HEIGHT - 10, "BACK", fg)
            return
        if self.mode is _Mode.WORKING:
            display.text_center(CONTENT_TOP + 24, "FORGETTING...", fg)
            return
        if self.mode is _Mode.CONFIRM:
            name = self.names[self._cursor]
            display.text_center(CONTENT_TOP + 12, "FORGET", fg)
            display.text_center(CONTENT_TOP + 26, truncate(name, 18), fg)
            display.text(PADDING_X, display.HEIGHT - 10, "OK=YES", fg)
            display.text_right(SCREEN_W - PADDING_X, display.HEIGHT - 10, "BACK=NO", fg)
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
        for i in range(self._scroll, min(self._scroll + rows, len(self.names))):
            cursor = ">" if i == self._cursor else " "
            display.text(PADDING_X, y, cursor + truncate(self.names[i], max_chars), fg)
            y += _ROW_H
        display.text_right(SCREEN_W - PADDING_X, footer_y, "OK=FORGET", fg)
