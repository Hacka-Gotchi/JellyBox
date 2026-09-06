"""WiFi page: scan, then connect.

Scans for networks (async), lists them strongest-first with signal bars and a
lock marker. Select one and press OK to connect: secured networks prompt for a
password on the on-screen keyboard, then join via nmcli. Reachable from the main
menu and from Settings.
"""
from __future__ import annotations

from enum import Enum, auto

from hardware.buttons import Button, ButtonEvent
from hardware.display import Display
from network.wifi import (
    WifiNetwork,
    build_connect_command,
    build_scan_command,
    connect_ok,
    parse_scan_output,
)
from ui.components.header import draw_header
from ui.components.keyboard import Keyboard
from ui.page_manager import Page
from ui.renderer import CONTENT_TOP, PADDING_X, SCREEN_W, truncate

_ROW_H = 12


class _Mode(Enum):
    SCANNING = auto()
    LIST = auto()
    PASSWORD = auto()
    CONNECTING = auto()
    RESULT = auto()
    EMPTY = auto()
    ERROR = auto()


class WifiScanPage(Page):
    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self.networks: list[WifiNetwork] = []
        self.task = None
        self._cursor = 0
        self._scroll = 0
        self.mode = _Mode.SCANNING
        self.error_msg = ""
        self.keyboard: Keyboard | None = None
        self._pending: WifiNetwork | None = None
        self._result_msg = ""

    def on_enter(self) -> None:
        self._start_scan()

    def on_exit(self) -> None:
        self._cancel()

    def _cancel(self) -> None:
        if self.task is not None and not self.task.finished:
            self.task.cancel()
        self.task = None

    def _iface(self):
        return self.ctx.settings.get("wifi_interface")

    def _start_scan(self) -> None:
        if not self.ctx.deps.has("nmcli"):
            self.error_msg = "NMCLI NOT FOUND"
            self.mode = _Mode.ERROR
            return
        self.networks = []
        self._cursor = 0
        self._scroll = 0
        self.mode = _Mode.SCANNING
        self.task = self.ctx.commands.run_async(build_scan_command(rescan=True, iface=self._iface()))

    def update(self) -> None:
        if self.task is None:
            return
        if self.mode is _Mode.SCANNING and self.task.finished:
            result = self.task.result
            self.task = None
            if result is not None and result.error:
                self.error_msg = "SCAN FAILED"
                self.mode = _Mode.ERROR
                return
            self.networks = parse_scan_output(result.stdout if result else "")
            self.mode = _Mode.LIST if self.networks else _Mode.EMPTY
        elif self.mode is _Mode.CONNECTING and self.task.finished:
            result = self.task.result
            self.task = None
            text = result.stdout if result else ""
            ok = result is not None and (result.ok or connect_ok(text))
            self._result_msg = "CONNECTED" if ok else "FAILED"
            self.mode = _Mode.RESULT

    def handle_input(self, event: ButtonEvent) -> None:
        m = self.mode
        if m is _Mode.LIST:
            self._list_input(event.button)
        elif m is _Mode.PASSWORD:
            self._password_input(event.button)
        elif m is _Mode.CONNECTING:
            if event.button is Button.BACK:
                self._cancel()
                self.mode = _Mode.LIST
        elif m in (_Mode.RESULT, _Mode.EMPTY, _Mode.ERROR):
            if event.button is Button.BACK:
                self.ctx.pages.pop()
            elif event.button is Button.CENTER:
                self._start_scan()
        elif m is _Mode.SCANNING:
            if event.button is Button.BACK:
                self._cancel()
                self.ctx.pages.pop()

    def _list_input(self, btn: Button) -> None:
        if btn is Button.BACK:
            self.ctx.pages.pop()
        elif btn is Button.DOWN:
            self._cursor = min(self._cursor + 1, len(self.networks) - 1)
        elif btn is Button.UP:
            self._cursor = max(self._cursor - 1, 0)
        elif btn is Button.CENTER:
            self._begin_connect(self.networks[self._cursor])

    def _begin_connect(self, net: WifiNetwork) -> None:
        self._pending = net
        if net.secured:
            self.keyboard = Keyboard("")
            self.mode = _Mode.PASSWORD
        else:
            self._do_connect(net, None)

    def _password_input(self, btn: Button) -> None:
        kb = self.keyboard
        if kb is None:
            self.mode = _Mode.LIST
            return
        status = kb.handle(btn)
        if status == "cancel":
            self.mode = _Mode.LIST
        elif status == "done":
            self._do_connect(self._pending, kb.value())

    def _do_connect(self, net: WifiNetwork, password: str | None) -> None:
        self.task = self.ctx.commands.run_async(
            build_connect_command(net.ssid, password, self._iface()))
        self.mode = _Mode.CONNECTING

    def draw(self, display: Display) -> None:
        theme = self.ctx.theme
        fg = theme.foreground
        if self.mode is _Mode.PASSWORD and self.keyboard is not None:
            ssid = self._pending.ssid if self._pending else ""
            display.text(PADDING_X, 2, truncate("PW " + ssid, 20), fg)
            display.hline(14, fg)
            self.keyboard.draw(display, theme, 18)
            return

        draw_header(display, theme, "WIFI",
                    wifi=self.ctx.wifi.status if self.ctx.wifi else None)

        if self.mode is _Mode.SCANNING:
            display.text_center(CONTENT_TOP + 24, "SCANNING...", fg)
        elif self.mode is _Mode.EMPTY:
            display.text_center(CONTENT_TOP + 24, "NO NETWORKS", fg)
            display.text_right(SCREEN_W - PADDING_X, display.HEIGHT - 10, "OK=RESCAN", fg)
        elif self.mode is _Mode.ERROR:
            display.text(PADDING_X, CONTENT_TOP + 10, self.error_msg, fg)
            display.text(PADDING_X, display.HEIGHT - 10, "BACK", fg)
        elif self.mode is _Mode.CONNECTING:
            ssid = self._pending.ssid if self._pending else ""
            display.text(PADDING_X, CONTENT_TOP, truncate(ssid, 20), fg)
            display.text_center(CONTENT_TOP + 24, "CONNECTING...", fg)
            display.text(PADDING_X, display.HEIGHT - 10, "BACK CANCEL", fg)
        elif self.mode is _Mode.RESULT:
            ssid = self._pending.ssid if self._pending else ""
            display.text(PADDING_X, CONTENT_TOP, truncate(ssid, 20), fg)
            display.text_center(CONTENT_TOP + 24, self._result_msg, fg)
            display.text(PADDING_X, display.HEIGHT - 10, "OK=RESCAN", fg)
            display.text_right(SCREEN_W - PADDING_X, display.HEIGHT - 10, "BACK", fg)
        elif self.mode is _Mode.LIST:
            self._draw_list(display, fg)

    def _draw_list(self, display: Display, fg) -> None:
        footer_y = display.HEIGHT - 10
        rows = max(1, (footer_y - CONTENT_TOP) // _ROW_H)
        if self._cursor < self._scroll:
            self._scroll = self._cursor
        elif self._cursor >= self._scroll + rows:
            self._scroll = self._cursor - rows + 1

        char_w = max(1, display.measure("0")[0])
        bar_w, pct_w = 22, 4 * char_w
        name_chars = (SCREEN_W - PADDING_X - bar_w - pct_w - 10) // char_w

        y = CONTENT_TOP
        for idx in range(self._scroll, min(self._scroll + rows, len(self.networks))):
            net = self.networks[idx]
            cursor = ">" if idx == self._cursor else " "
            lock = "*" if net.secured else " "
            display.text(PADDING_X, y, cursor + lock + truncate(net.ssid, name_chars), fg)
            bx1 = SCREEN_W - PADDING_X - pct_w - 2
            bx0 = bx1 - bar_w
            display.rect(bx0, y + 1, bx1, y + display.line_height - 2, fg)
            fill = int((bar_w - 2) * max(0, min(100, net.signal)) / 100)
            if fill > 0:
                display.rect(bx0 + 1, y + 2, bx0 + 1 + fill, y + display.line_height - 3, fg, fill=fg)
            display.text_right(SCREEN_W - PADDING_X, y, f"{net.signal}", fg)
            y += _ROW_H
        display.text_right(SCREEN_W - PADDING_X, footer_y, "OK=CONNECT", fg)
