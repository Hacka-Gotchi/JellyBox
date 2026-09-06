"""Nmap scan page.

Fast port scan of a target. TARGET is set with the IP editor; ARGS (the nmap
flags) are edited with the on-screen keyboard, so scans are fully customizable
(port ranges, service detection, etc.). Reuses the async command pattern (BACK
cancels). Args persist in settings.
"""
from __future__ import annotations

from enum import Enum, auto

from hardware.buttons import Button, ButtonEvent
from hardware.display import Display
from network.interfaces import default_route
from network.nmap import DEFAULT_ARGS, Port, build_nmap_command, host_is_up, parse_open_ports, scan_error
from ui.components.header import draw_header
from ui.components.ip_editor import IpEditor
from ui.components.keyboard import Keyboard
from ui.components.menu import Menu
from ui.components.scroll_view import ScrollView
from ui.page_manager import Page
from ui.renderer import CONTENT_TOP, PADDING_X, SCREEN_W, truncate


class _Mode(Enum):
    MENU = auto()
    EDIT_TARGET = auto()
    EDIT_ARGS = auto()
    RUNNING = auto()
    RESULT = auto()
    ERROR = auto()


class NmapScanPage(Page):
    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        gateway, _ = default_route()
        self.target = gateway or "192.168.1.1"
        self.mode = _Mode.MENU
        self.menu = Menu(["TARGET", "ARGS", "START"], wrap=True)
        self.editor = IpEditor(self.target)
        self.keyboard: Keyboard | None = None
        self.ports: list[Port] = []
        self.host_up = False
        self.result_view = ScrollView()
        self.task = None
        self.error_msg = ""
        self._saved = ""

    def _args(self) -> str:
        return str(self.ctx.settings.get("nmap_args", DEFAULT_ARGS)) or DEFAULT_ARGS

    def on_exit(self) -> None:
        self._cancel()

    def _cancel(self) -> None:
        if self.task is not None and not self.task.finished:
            self.task.cancel()
        self.task = None

    def handle_input(self, event: ButtonEvent) -> None:
        btn = event.button
        if self.mode is _Mode.MENU:
            if btn is Button.UP:
                self.menu.up()
            elif btn is Button.DOWN:
                self.menu.down()
            elif btn is Button.BACK:
                self.ctx.pages.pop()
            elif btn is Button.CENTER:
                choice = self.menu.current
                if choice == "TARGET":
                    self.editor.set(self.target)
                    self.mode = _Mode.EDIT_TARGET
                elif choice == "ARGS":
                    self.keyboard = Keyboard(self._args())
                    self.mode = _Mode.EDIT_ARGS
                else:
                    self._start()

        elif self.mode is _Mode.EDIT_TARGET:
            if btn is Button.LEFT:
                self.editor.left()
            elif btn is Button.RIGHT:
                self.editor.right()
            elif btn is Button.UP:
                self.editor.inc()
            elif btn is Button.DOWN:
                self.editor.dec()
            elif btn is Button.CENTER:
                self.target = self.editor.value()
                self.mode = _Mode.MENU
            elif btn is Button.BACK:
                self.mode = _Mode.MENU

        elif self.mode is _Mode.EDIT_ARGS:
            kb = self.keyboard
            if kb is None:
                self.mode = _Mode.MENU
                return
            status = kb.handle(btn)
            if status == "cancel":
                self.mode = _Mode.MENU
            elif status == "done":
                self.ctx.settings.set("nmap_args", kb.value() or DEFAULT_ARGS)
                self.ctx.settings.save()
                self.mode = _Mode.MENU

        elif self.mode is _Mode.RUNNING:
            if btn is Button.BACK:
                self._cancel()
                self.mode = _Mode.MENU

        elif self.mode in (_Mode.RESULT, _Mode.ERROR):
            if btn is Button.BACK:
                self.mode = _Mode.MENU
            elif btn is Button.CENTER and self.mode is _Mode.RESULT:
                self._start()
            elif self.mode is _Mode.RESULT and btn is Button.UP:
                self.result_view.up()
            elif self.mode is _Mode.RESULT and btn is Button.DOWN:
                self.result_view.down()
            elif self.mode is _Mode.RESULT and btn is Button.LEFT:
                from system.scanstore import save_scan
                try:
                    name = save_scan("nmap", self.target, self.result_view.lines)
                    self._saved = "SAVED " + name.split("_")[0]
                except Exception:
                    self._saved = "SAVE FAILED"

    def _start(self) -> None:
        if not self.ctx.deps.has("nmap"):
            self.error_msg = "NMAP NOT FOUND"
            self.mode = _Mode.ERROR
            return
        self.ports = []
        self.host_up = False
        self._saved = ""
        self.task = self.ctx.commands.run_async(build_nmap_command(self.target, self._args()))
        self.mode = _Mode.RUNNING

    def update(self) -> None:
        if self.mode is not _Mode.RUNNING or self.task is None:
            return
        if self.task.finished:
            result = self.task.result
            self.task = None
            text = result.stdout if result else ""
            if result is not None and result.error:
                self.error_msg = "NMAP ERROR"
                self.mode = _Mode.ERROR
                return
            err = scan_error(text, result.returncode if result else None)
            if err:
                self.error_msg = err
                self.mode = _Mode.ERROR
                return
            self.ports = parse_open_ports(text)
            self.host_up = host_is_up(text)
            lines = [self.target]
            if not self.ports:
                lines.append("NO OPEN PORTS" if self.host_up else "HOST DOWN?")
            else:
                lines += [f"{p.number}/{p.proto} {p.service}".rstrip() for p in self.ports]
            self.result_view.set_lines(lines)
            self.mode = _Mode.RESULT

    def draw(self, display: Display) -> None:
        theme = self.ctx.theme
        fg = theme.foreground
        if self.mode is _Mode.EDIT_ARGS and self.keyboard is not None:
            display.text(PADDING_X, 2, "ARGS", fg)
            display.hline(14, fg)
            self.keyboard.draw(display, theme, 18)
            return

        draw_header(display, theme, "NMAP",
                    wifi=self.ctx.wifi.status if self.ctx.wifi else None)

        if self.mode is _Mode.MENU:
            char_w = max(1, display.measure("0")[0])
            y = CONTENT_TOP
            line_h = display.line_height + 2
            for i, label in enumerate(["TARGET", "ARGS"]):
                sel = self.menu.selected == i
                display.text(PADDING_X, y, ("> " if sel else "  ") + label, fg)
                val = self.target if label == "TARGET" else self._args()
                display.text(52, y, truncate(val, (SCREEN_W - 52) // char_w), fg)
                y += line_h
            sel = self.menu.selected == 2
            display.text(PADDING_X, y + 2, ("> " if sel else "  ") + "START", fg)
        elif self.mode is _Mode.EDIT_TARGET:
            display.text_center(CONTENT_TOP, "SET TARGET", fg)
            self.editor.draw(display, theme, CONTENT_TOP + 18)
            display.text_center(display.HEIGHT - 22, "UP/DN LR", fg)
            display.text_center(display.HEIGHT - 10, "OK=SET", fg)
        elif self.mode is _Mode.RUNNING:
            display.text(PADDING_X, CONTENT_TOP, self.target, fg)
            display.text_center(CONTENT_TOP + 24, "SCANNING...", fg)
            display.text(PADDING_X, display.HEIGHT - 10, "BACK CANCEL", fg)
        elif self.mode is _Mode.RESULT:
            self._draw_result(display, fg)
        elif self.mode is _Mode.ERROR:
            display.text(PADDING_X, CONTENT_TOP + 6, self.error_msg, fg)
            if "ARG" in self.error_msg:
                display.text(PADDING_X, CONTENT_TOP + 20, "CHECK ARGS", fg)
            elif self.error_msg == "BAD HOST":
                display.text(PADDING_X, CONTENT_TOP + 20, "CHECK TARGET", fg)
            display.text(PADDING_X, display.HEIGHT - 10, "BACK", fg)

    def _draw_result(self, display: Display, fg) -> None:
        footer_y = display.HEIGHT - 10
        self.result_view.draw(display, self.ctx.theme, CONTENT_TOP, footer_y)
        if self._saved:
            display.text_center(footer_y, self._saved, fg)
        else:
            display.text(PADDING_X, footer_y, "L=SAVE OK=RESCAN", fg)
