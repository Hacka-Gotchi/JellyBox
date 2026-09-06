"""Terminal page (command console).

Type a shell command with the on-screen keyboard, run it, and see the output
stream into a scrollable, word-wrapped buffer -- then run another. It's a
command console, not a full interactive terminal: each command runs to
completion (via ``bash -lc``) and BACK cancels a running one. Interactive
programs (top, vim, a password prompt) will just hang until cancelled.

Runs as the app's user on this device -- a local console on your own Pi.
"""
from __future__ import annotations

from enum import Enum, auto

from hardware.buttons import Button, ButtonEvent
from hardware.display import Display
from ui.components.header import draw_header
from ui.components.keyboard import Keyboard
from ui.components.scroll_view import ScrollView
from ui.page_manager import Page
from ui.renderer import CONTENT_TOP, PADDING_X, SCREEN_W

_MAX_LINES = 400


class _Mode(Enum):
    VIEW = auto()
    EDIT = auto()
    RUNNING = auto()


class TerminalPage(Page):
    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self.view = ScrollView(follow=True)
        self.view.set_lines(["jellybox terminal", "OK to type a command", ""])
        self.mode = _Mode.VIEW
        self.keyboard: Keyboard | None = None
        self.task = None

    @property
    def lines(self) -> list[str]:
        return self.view.lines

    def on_exit(self) -> None:
        self._cancel()

    def _cancel(self) -> None:
        if self.task is not None and not self.task.finished:
            self.task.cancel()
        self.task = None

    def _push(self, line: str) -> None:
        self.view.append(line)
        if len(self.view.lines) > _MAX_LINES:
            self.view.lines = self.view.lines[-_MAX_LINES:]
        self.view.follow = True

    def handle_input(self, event: ButtonEvent) -> None:
        btn = event.button
        if self.mode is _Mode.VIEW:
            if btn is Button.BACK:
                self.ctx.pages.pop()
            elif btn is Button.CENTER:
                self.keyboard = Keyboard("")
                self.mode = _Mode.EDIT
            elif btn is Button.UP:
                self.view.up()
            elif btn is Button.DOWN:
                self.view.down()

        elif self.mode is _Mode.EDIT:
            kb = self.keyboard
            if kb is None:
                self.mode = _Mode.VIEW
                return
            status = kb.handle(btn)
            if status == "cancel":
                self.mode = _Mode.VIEW
            elif status == "done":
                cmd = kb.value().strip()
                self.mode = _Mode.VIEW
                if cmd:
                    self._run(cmd)

        elif self.mode is _Mode.RUNNING:
            if btn is Button.BACK:
                self._cancel()
                self._push("^C")
                self.mode = _Mode.VIEW
            elif btn is Button.UP:
                self.view.up()
            elif btn is Button.DOWN:
                self.view.down()

    def _run(self, cmd: str) -> None:
        self._push("$ " + cmd)
        self.task = self.ctx.commands.run_async(["bash", "-lc", cmd])
        self.mode = _Mode.RUNNING

    def update(self) -> None:
        if self.mode is not _Mode.RUNNING or self.task is None:
            return
        for line in self.task.drain_lines():
            self._push(line)
        if self.task.finished:
            for line in self.task.drain_lines():
                self._push(line)
            result = self.task.result
            rc = result.returncode if result is not None else None
            if result is not None and result.error:
                self._push("[command not found]")
            elif rc not in (0, None):
                self._push(f"[exit {rc}]")
            self.task = None
            self.mode = _Mode.VIEW

    def draw(self, display: Display) -> None:
        theme = self.ctx.theme
        fg = theme.foreground
        if self.mode is _Mode.EDIT and self.keyboard is not None:
            display.text(PADDING_X, 2, "CMD", fg)
            display.hline(14, fg)
            self.keyboard.draw(display, theme, 18)
            return

        draw_header(display, theme, "TERM",
                    wifi=self.ctx.wifi.status if self.ctx.wifi else None)

        footer_y = display.HEIGHT - 10
        self.view.draw(display, theme, CONTENT_TOP, footer_y)

        if self.mode is _Mode.RUNNING:
            display.text(PADDING_X, footer_y, "RUN  BACK=STOP", fg)
        else:
            display.text(PADDING_X, footer_y, "OK=TYPE", fg)
            display.text_right(SCREEN_W - PADDING_X, footer_y, "BACK", fg)
