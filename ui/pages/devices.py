"""Devices page (hardware inventory + interface selection).

Shows what's connected: network interfaces (Wi-Fi / Ethernet) and USB devices.
The actionable part is selecting the active **Wi-Fi interface** -- press CENTER
on a Wi-Fi interface (e.g. an external adapter) and the Wi-Fi scan will use it.
The choice persists in settings. Non-Wi-Fi rows are informational.
"""
from __future__ import annotations

from hardware.buttons import Button, ButtonEvent
from hardware.display import Display
from system.devices import NetIface, UsbDevice, list_network_interfaces, list_usb_devices
from ui.components.header import draw_header
from ui.page_manager import Page
from ui.renderer import CONTENT_TOP, PADDING_X, SCREEN_W, truncate

_ROW_H = 12


class DevicesPage(Page):
    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self._ifaces: list[NetIface] = []
        self._usb: list[UsbDevice] = []
        self._entries: list = []   # flat list of (kind, obj) for cursor movement
        self._cursor = 0
        self._scroll = 0

    def on_enter(self) -> None:
        # Re-enumerate on first entry; on return from the action menu, keep the
        # cursor but re-read so a newly-selected interface's marker updates.
        keep = self._cursor
        self._refresh()
        self._cursor = min(keep, max(0, len(self._entries) - 1))

    def _refresh(self) -> None:
        self._ifaces = list_network_interfaces()
        self._usb = list_usb_devices()
        # Flat, selectable model: interface rows first, then USB rows.
        self._entries = [("iface", i) for i in self._ifaces]
        self._entries += [("usb", u) for u in self._usb]
        self._scroll = 0

    @property
    def _active_iface(self) -> str | None:
        return self.ctx.settings.get("wifi_interface")

    def handle_input(self, event: ButtonEvent) -> None:
        btn = event.button
        if btn is Button.BACK:
            self.ctx.pages.pop()
        elif btn is Button.DOWN:
            if self._entries:
                self._cursor = min(self._cursor + 1, len(self._entries) - 1)
        elif btn is Button.UP:
            self._cursor = max(self._cursor - 1, 0)
        elif btn is Button.CENTER:
            self._select_current()

    def _select_current(self) -> None:
        if not self._entries:
            return
        kind, obj = self._entries[self._cursor]
        from ui.pages.device_actions import DeviceActionPage
        self.ctx.pages.push(DeviceActionPage(self.ctx, kind, obj))

    def draw(self, display: Display) -> None:
        theme = self.ctx.theme
        draw_header(
            display, theme, "HARDWARE",
            wifi=self.ctx.wifi.status if self.ctx.wifi else None,
        )
        fg = theme.foreground
        if not self._entries:
            display.text_center(CONTENT_TOP + 24, "NONE FOUND", fg)
            return

        footer_y = display.HEIGHT - 10
        rows = max(1, (footer_y - CONTENT_TOP) // _ROW_H)
        if self._cursor < self._scroll:
            self._scroll = self._cursor
        elif self._cursor >= self._scroll + rows:
            self._scroll = self._cursor - rows + 1

        char_w = max(1, display.measure("0")[0])
        max_chars = (SCREEN_W - PADDING_X) // char_w - 2

        y = CONTENT_TOP
        for idx in range(self._scroll, min(self._scroll + rows, len(self._entries))):
            kind, obj = self._entries[idx]
            marker = "> " if idx == self._cursor else "  "
            if kind == "iface":
                active = obj.is_wifi and self._active_iface == obj.name
                tag = "*" if active else ("+" if obj.is_wifi else " ")
                label = f"{tag}{obj.name} {obj.kind[:4]} {obj.state[:4]}"
            else:
                label = f" USB {obj.name}"
            display.text(PADDING_X, y, marker + truncate(label, max_chars), fg)
            y += _ROW_H

        display.text(PADDING_X, footer_y, "OK=ACTIONS", fg)
