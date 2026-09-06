"""Device action menu.

Opened when a device is selected on the Devices page; the action set is built
per device type in :meth:`_build_actions`.

  Wi-Fi interface : USE FOR SCAN (toggle active), SCAN NOW, MONITOR on/off, DETAILS
  other interface : DETAILS
  USB device      : DETAILS

Toggling monitor mode changes the interface type and needs root, so it goes
through the jellybox-iface helper; the rest are read-only.
"""
from __future__ import annotations

from enum import Enum, auto
import shutil

from hardware.buttons import Button, ButtonEvent
from hardware.display import Display
from system.devices import NetIface, UsbDevice, iface_driver, iface_mode
from ui.components.header import draw_header
from ui.page_manager import Page
from ui.renderer import CONTENT_TOP, PADDING_X, SCREEN_W, truncate

_ROW_H = 13
_HELPER = "/usr/local/sbin/jellybox-iface"


class _Mode(Enum):
    MENU = auto()
    DETAILS = auto()


class DeviceActionPage(Page):
    def __init__(self, ctx, kind: str, obj) -> None:
        super().__init__(ctx)
        self.kind = kind          # "iface" | "usb"
        self.obj = obj
        self.mode = _Mode.MENU
        self._selected = 0
        self._task = None         # in-flight monitor-mode toggle
        self._status = ""         # transient status line
        self._actions = self._build_actions()

    def _build_actions(self) -> list[tuple[str, object]]:
        actions: list[tuple[str, object]] = []
        if self.kind == "iface" and isinstance(self.obj, NetIface) and self.obj.is_wifi:
            active = self.ctx.settings.get("wifi_interface") == self.obj.name
            actions.append(("UNSELECT" if active else "USE FOR SCAN", self._toggle_scan))
            actions.append(("SCAN NOW", self._scan_now))
            monitor = iface_mode(self.obj.name) == "monitor"
            actions.append(("MONITOR OFF" if monitor else "MONITOR ON",
                            self._toggle_monitor))
        actions.append(("DETAILS", self._show_details))
        return actions

    def _toggle_scan(self) -> None:
        cur = self.ctx.settings.get("wifi_interface")
        self.ctx.settings.set("wifi_interface",
                              None if cur == self.obj.name else self.obj.name)
        self.ctx.settings.save()
        self._actions = self._build_actions()

    def _scan_now(self) -> None:
        from ui.pages.wifi_scan import WifiScanPage
        self.ctx.settings.set("wifi_interface", self.obj.name)
        self.ctx.settings.save()
        self.ctx.pages.pop()                  # leave this menu
        self.ctx.pages.push(WifiScanPage(self.ctx))

    def _show_details(self) -> None:
        self.mode = _Mode.DETAILS

    def _toggle_monitor(self) -> None:
        if self._task is not None:
            return  # already switching
        if not shutil.which("sudo"):
            self._status = "NO SUDO"
            return
        target = "managed" if iface_mode(self.obj.name) == "monitor" else "monitor"
        cmd = ["sudo", "-n", _HELPER, self.obj.name, target]
        self._status = "SWITCHING..."
        self._task = self.ctx.commands.run_async(cmd)

    def update(self) -> None:
        if self._task is None or not self._task.finished:
            return
        result = self._task.result
        self._task = None
        if result is not None and result.ok:
            self._status = f"NOW {iface_mode(self.obj.name).upper()}"
        else:
            # Most likely passwordless sudo isn't set up yet.
            self._status = "NEED SETUP (SSH)"
        self._actions = self._build_actions()

    def _detail_lines(self) -> list[tuple[str, str]]:
        if self.kind == "iface" and isinstance(self.obj, NetIface):
            lines = [
                ("NAME", self.obj.name),
                ("KIND", self.obj.kind),
                ("STATE", self.obj.state),
                ("MAC", self.obj.mac or "-"),
                ("DRIVER", iface_driver(self.obj.name) or "-"),
            ]
            if self.obj.is_wifi:
                lines.append(("TYPE", iface_mode(self.obj.name)))
            return lines
        if isinstance(self.obj, UsbDevice):
            return [
                ("NAME", self.obj.name),
                ("VID", self.obj.vid),
                ("PID", self.obj.pid),
            ]
        return []

    def handle_input(self, event: ButtonEvent) -> None:
        btn = event.button
        if self.mode is _Mode.DETAILS:
            if btn is Button.BACK:
                self.mode = _Mode.MENU
            return
        if btn is Button.BACK:
            self.ctx.pages.pop()
        elif btn is Button.UP:
            self._selected = (self._selected - 1) % len(self._actions)
        elif btn is Button.DOWN:
            self._selected = (self._selected + 1) % len(self._actions)
        elif btn is Button.CENTER:
            if self._task is None:
                self._actions[self._selected][1]()

    def _title(self) -> str:
        return getattr(self.obj, "name", "DEVICE")

    def draw(self, display: Display) -> None:
        theme = self.ctx.theme
        draw_header(
            display, theme, truncate(self._title(), 16),
            wifi=self.ctx.wifi.status if self.ctx.wifi else None,
        )
        fg = theme.foreground
        if self.mode is _Mode.DETAILS:
            self._draw_details(display, fg)
            return

        y = CONTENT_TOP + 2
        for i, (label, _) in enumerate(self._actions):
            prefix = "> " if i == self._selected else "  "
            display.text(PADDING_X, y, prefix + label, fg)
            y += _ROW_H
        if self._status:
            display.text_center(display.HEIGHT - 22, self._status, fg)
        display.text(PADDING_X, display.HEIGHT - 10, "OK=DO", fg)
        display.text_right(SCREEN_W - PADDING_X, display.HEIGHT - 10, "BACK", fg)

    def _draw_details(self, display: Display, fg) -> None:
        char_w = max(1, display.measure("0")[0])
        y = CONTENT_TOP
        for label, value in self._detail_lines():
            display.text(PADDING_X, y, label, fg)
            max_chars = (SCREEN_W - PADDING_X - 42) // char_w
            display.text(42, y, truncate(value, max_chars), fg)
            y += _ROW_H
        display.text(PADDING_X, display.HEIGHT - 10, "BACK", fg)
