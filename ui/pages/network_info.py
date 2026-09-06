"""Network Info page.

Scrollable list of the current interface, IPv4, gateway, hostname, and MAC, plus
the connected Wi-Fi SSID and signal when nmcli is available. The active
interface is discovered rather than assumed. Data is refreshed on entry and on
CENTER.
"""
from __future__ import annotations

from hardware.buttons import Button, ButtonEvent
from hardware.display import Display
from network.interfaces import NetInfo, get_network_info
from network.wifi import build_active_command, parse_active
from ui.components.header import draw_header
from ui.page_manager import Page
from ui.renderer import CONTENT_TOP, PADDING_X, SCREEN_W, truncate


class NetworkInfoPage(Page):
    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self.info: NetInfo = NetInfo()
        self.ssid: str | None = None
        self.signal: int | None = None
        self._scroll = 0

    def on_enter(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        self.info = get_network_info()
        self.ssid, self.signal = None, None
        # Best-effort active Wi-Fi (SSID + signal). Quick, no forced rescan;
        # skipped entirely if nmcli isn't installed.
        if self.ctx.deps.has("nmcli"):
            res = self.ctx.commands.run(build_active_command(), timeout=2)
            if res.ok:
                self.ssid, self.signal = parse_active(res.stdout)
        self._scroll = 0

    def _fields(self) -> list[tuple[str, str]]:
        fields = self.info.as_fields()
        if self.ssid:
            fields.append(("SSID", self.ssid))
        if self.signal is not None:
            fields.append(("SIGNAL", f"{self.signal}%"))
        return fields

    def handle_input(self, event: ButtonEvent) -> None:
        btn = event.button
        fields = self._fields()
        if btn is Button.DOWN:
            self._scroll = min(self._scroll + 1, max(0, len(fields) - 1))
        elif btn is Button.UP:
            self._scroll = max(0, self._scroll - 1)
        elif btn is Button.CENTER:
            self._refresh()
        elif btn is Button.BACK:
            self.ctx.pages.pop()

    def draw(self, display: Display) -> None:
        theme = self.ctx.theme
        draw_header(
            display, theme, "NETWORK",
            wifi=self.ctx.wifi.status if self.ctx.wifi else None,
        )
        fg = theme.foreground
        fields = self._fields()

        line_h = display.line_height + 1
        pair_h = line_h * 2
        avail = display.HEIGHT - CONTENT_TOP - 10  # leave room for hint
        rows = max(1, avail // pair_h)

        char_w = max(1, display.measure("0")[0])
        max_chars = (SCREEN_W - PADDING_X) // char_w

        y = CONTENT_TOP
        for label, value in fields[self._scroll:self._scroll + rows]:
            display.text(PADDING_X, y, label, fg)
            display.text(PADDING_X, y + line_h, truncate(value, max_chars), fg)
            y += pair_h

        display.text_right(SCREEN_W - PADDING_X, display.HEIGHT - 10, "OK=REFRESH", fg)
