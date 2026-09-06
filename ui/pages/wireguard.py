"""WireGuard page (TOOLS).

Lists the tunnels configured in /etc/wireguard, shows which are up, and toggles
the selected one up/down. Config files are created over SSH; this just controls
them, through the root helper (scripts/jellybox-wg).
"""
from __future__ import annotations

from enum import Enum, auto

from hardware.buttons import Button, ButtonEvent
from hardware.display import Display
from system.wireguard import parse_active_interfaces, parse_handshake, parse_tunnel_list
from ui.components.header import draw_header
from ui.page_manager import Page
from ui.renderer import CONTENT_TOP, PADDING_X, SCREEN_W, truncate

_HELPER = "/usr/local/sbin/jellybox-wg"
_ROW_H = 12


class _Mode(Enum):
    LIST = auto()
    WORKING = auto()
    EMPTY = auto()
    ERROR = auto()


class WireGuardPage(Page):
    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self.tunnels: list[str] = []
        self.active: set[str] = set()
        self._status_text = ""
        self._cursor = 0
        self.mode = _Mode.LIST
        self.task = None
        self.error_msg = ""

    def on_enter(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        lst = self.ctx.commands.run(["sudo", "-n", _HELPER, "list"], timeout=4)
        if not lst.ok:
            self.error_msg = "SETUP NEEDED (SSH)"
            self.mode = _Mode.ERROR
            return
        self.tunnels = parse_tunnel_list(lst.stdout)
        st = self.ctx.commands.run(["sudo", "-n", _HELPER, "status"], timeout=4)
        self._status_text = st.stdout if st.ok else ""
        self.active = parse_active_interfaces(self._status_text)
        self._cursor = min(self._cursor, max(0, len(self.tunnels) - 1))
        self.mode = _Mode.LIST if self.tunnels else _Mode.EMPTY

    def handle_input(self, event: ButtonEvent) -> None:
        btn = event.button
        if self.mode is _Mode.WORKING:
            return
        if btn is Button.BACK:
            self.ctx.pages.pop()
        elif self.mode is _Mode.LIST:
            if btn is Button.DOWN:
                self._cursor = min(self._cursor + 1, len(self.tunnels) - 1)
            elif btn is Button.UP:
                self._cursor = max(self._cursor - 1, 0)
            elif btn is Button.CENTER:
                self._toggle(self.tunnels[self._cursor])
        elif self.mode in (_Mode.EMPTY, _Mode.ERROR):
            if btn is Button.CENTER:
                self._refresh()

    def _toggle(self, name: str) -> None:
        op = "down" if name in self.active else "up"
        self.task = self.ctx.commands.run_async(["sudo", "-n", _HELPER, op, name])
        self.mode = _Mode.WORKING

    def update(self) -> None:
        if self.task is None or not self.task.finished:
            return
        self.task = None
        self._refresh()  # re-read list + status after the toggle

    def draw(self, display: Display) -> None:
        theme = self.ctx.theme
        fg = theme.foreground
        draw_header(display, theme, "WIREGUARD",
                    wifi=self.ctx.wifi.status if self.ctx.wifi else None)

        if self.mode is _Mode.ERROR:
            display.text(PADDING_X, CONTENT_TOP + 10, self.error_msg, fg)
            display.text(PADDING_X, display.HEIGHT - 10, "BACK", fg)
            return
        if self.mode is _Mode.EMPTY:
            display.text_center(CONTENT_TOP + 16, "NO TUNNELS", fg)
            display.text_center(CONTENT_TOP + 30, "add /etc/wireguard", fg)
            display.text(PADDING_X, display.HEIGHT - 10, "BACK", fg)
            return
        if self.mode is _Mode.WORKING:
            display.text_center(CONTENT_TOP + 24, "WORKING...", fg)
            return

        char_w = max(1, display.measure("0")[0])
        name_chars = (SCREEN_W - PADDING_X - 5 * char_w) // char_w
        y = CONTENT_TOP
        for i, name in enumerate(self.tunnels):
            cursor = ">" if i == self._cursor else " "
            up = name in self.active
            state = "UP" if up else "--"
            display.text(PADDING_X, y, cursor + truncate(name, name_chars), fg)
            display.text_right(SCREEN_W - PADDING_X, y, state, fg)
            y += _ROW_H

        sel = self.tunnels[self._cursor]
        if sel in self.active:
            hs = parse_handshake(self._status_text, sel)
            if hs:
                display.text(PADDING_X, display.HEIGHT - 22, truncate("HS " + hs, 20), fg)
        display.text(PADDING_X, display.HEIGHT - 10, "OK=TOGGLE", fg)
        display.text_right(SCREEN_W - PADDING_X, display.HEIGHT - 10, "BACK", fg)
