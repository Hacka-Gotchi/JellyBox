"""JACK TEST page.

Plug JellyBox's Ethernet port into an unknown jack and run one test: it collects
link, speed/duplex, IP/gateway/DHCP, LLDP switch name/port, and observed VLAN
IDs, and shows them on one screen. Collection runs on a background thread with
short timeouts so the UI stays responsive; it is strictly read-only.
"""
from __future__ import annotations

import threading
import time
from enum import Enum, auto

from hardware.buttons import Button, ButtonEvent
from hardware.display import Display
from network.interfaces import default_route, local_ipv4
from network.jacktest import (
    JackResult,
    build_device_show_command,
    build_lldp_command,
    build_vlan_command,
    dhcp_status,
    format_speed,
    lldp_switch_info,
    read_duplex,
    read_link,
    read_speed,
    summary_line,
    wired_interface,
)
from network.vlan import parse_vlan_ids
from ui.components.header import draw_header
from ui.components.keyboard import Keyboard
from ui.components.scroll_view import ScrollView
from ui.page_manager import Page
from ui.renderer import CONTENT_TOP, PADDING_X, SCREEN_W


class _Mode(Enum):
    RUNNING = auto()
    RESULT = auto()
    LABEL = auto()


class JackTestPage(Page):
    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self.mode = _Mode.RUNNING
        self.view = ScrollView()
        self._result: JackResult | None = None
        self._thread: threading.Thread | None = None
        self._start_time = 0.0
        self._saved = ""
        self.keyboard: Keyboard | None = None

    def on_enter(self) -> None:
        self._start()

    def _start(self) -> None:
        self.mode = _Mode.RUNNING
        self._result = None
        self._saved = ""
        self._start_time = time.monotonic()
        self._thread = threading.Thread(target=self._collect, daemon=True)
        self._thread.start()

    def _collect(self) -> None:
        result = JackResult()
        interface = wired_interface()
        result.interface = interface

        if interface:
            result.link = read_link(interface)
            if result.link:
                result.speed_mbps = read_speed(interface)
                result.duplex = read_duplex(interface)

        # IP / gateway / DHCP: prefer nmcli for the specific interface so the
        # answer is about the wired jack, not whatever holds the default route.
        if interface and self.ctx.deps.has("nmcli"):
            res = self.ctx.commands.run(build_device_show_command(interface), timeout=2)
            if res.ok:
                from network.jacktest import parse_nmcli_device
                info = parse_nmcli_device(res.stdout)
                result.ip = info["ip"]
                result.gateway = info["gateway"]
                result.dhcp = dhcp_status(info["ip"], info["dhcp"])
        if result.ip is None:  # fallback if nmcli is unavailable
            gateway, route_iface = default_route()
            if route_iface == interface:
                result.ip = local_ipv4()
                result.gateway = gateway

        if result.link and self.ctx.deps.has("lldpctl"):
            res = self.ctx.commands.run(build_lldp_command(), timeout=3)
            if res.ok:
                result.switch_name, result.switch_port = lldp_switch_info(
                    res.stdout, interface)

        if interface and result.link and self.ctx.deps.has("tcpdump"):
            res = self.ctx.commands.run(build_vlan_command(interface), timeout=12)
            if res.ok:
                result.vlans = parse_vlan_ids(res.stdout)

        self._result = result

    def update(self) -> None:
        if self.mode is _Mode.RUNNING and self._result is not None:
            self.view.set_lines(self._build_lines(self._result))
            self.mode = _Mode.RESULT

    @staticmethod
    def _build_lines(r: JackResult) -> list[str]:
        lines = [f"LINK   {'UP' if r.link else 'DOWN'}"]
        lines.append(f"IFACE  {r.interface or '-'}")
        if not r.link:
            return lines
        speed = format_speed(r.speed_mbps)
        duplex = (r.duplex or "").upper()
        lines.append(f"SPEED  {speed} {duplex}".rstrip())
        lines.append(f"DHCP   {r.dhcp}")
        lines.append(f"IP     {r.ip or '-'}")
        lines.append(f"GW     {r.gateway or '-'}")
        lines.append(f"VLAN   {','.join(map(str, r.vlans)) if r.vlans else 'NOT OBSERVED'}")
        lines.append(f"SWITCH {r.switch_name or 'NOT DETECTED'}")
        lines.append(f"PORT   {r.switch_port or 'NOT DETECTED'}")
        return lines

    def handle_input(self, event: ButtonEvent) -> None:
        if self.mode is _Mode.LABEL:
            self._label_input(event.button)
            return
        if self.mode is _Mode.RESULT:
            if event.button is Button.BACK:
                self.ctx.pages.pop()
            elif event.button is Button.CENTER:
                self._start()
            elif event.button is Button.LEFT:
                self.keyboard = Keyboard("")
                self._saved = ""
                self.mode = _Mode.LABEL
            elif event.button is Button.DOWN:
                self.view.down()
            elif event.button is Button.UP:
                self.view.up()
        elif event.button is Button.BACK:  # allow leaving mid-test
            self.ctx.pages.pop()

    def _label_input(self, btn: Button) -> None:
        kb = self.keyboard
        if kb is None:
            self.mode = _Mode.RESULT
            return
        status = kb.handle(btn)
        if status == "cancel":
            self.mode = _Mode.RESULT
        elif status == "done":
            self._save(kb.value().strip())
            self.mode = _Mode.RESULT

    def _save(self, label: str = "") -> None:
        if self._result is None:
            return
        from system.scanstore import save_scan
        # The summary line lets a saved jack be identified at a glance in RESULTS.
        lines = [summary_line(self._result, label), ""] + self._build_lines(self._result)
        try:
            name = save_scan("jack", label or (self._result.interface or "eth"), lines)
            self._saved = "SAVED " + name.split("_")[0]
        except Exception:
            self._saved = "SAVE FAILED"

    def draw(self, display: Display) -> None:
        theme = self.ctx.theme
        fg = theme.foreground
        if self.mode is _Mode.LABEL and self.keyboard is not None:
            display.text(PADDING_X, 2, "LABEL", fg)
            display.hline(14, fg)
            self.keyboard.draw(display, theme, 18)
            return

        draw_header(display, theme, "JACK TEST",
                    wifi=self.ctx.wifi.status if self.ctx.wifi else None)

        if self.mode is _Mode.RUNNING:
            dots = "." * (1 + int((time.monotonic() - self._start_time) * 3) % 3)
            display.text_center(CONTENT_TOP + 24, "TESTING" + dots, fg)
            display.text(PADDING_X, display.HEIGHT - 10, "BACK", fg)
            return

        self.view.draw(display, theme, CONTENT_TOP, display.HEIGHT - 10)
        if self._saved:
            display.text_center(display.HEIGHT - 10, self._saved, fg)
        else:
            display.text(PADDING_X, display.HEIGHT - 10, "L=SAVE OK=RETEST", fg)
