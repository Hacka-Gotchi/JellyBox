"""SYSTEM UPDATE page.

Checks the latest GitHub release and, when a newer one exists, launches the
independent updater unit (jellybox-update@<tag>.service) which replaces this
running app and rolls back if the new version fails to come up. The check runs
on a background thread with a short timeout and tolerates having no internet;
startup never depends on GitHub.
"""
from __future__ import annotations

import threading
import urllib.error
import urllib.request
from enum import Enum, auto

from core.version import current_version
from hardware.buttons import Button, ButtonEvent
from hardware.display import Display
from network.updates import is_newer, is_valid_tag, parse_latest_release, releases_api_url
from ui.components.header import draw_header
from ui.components.scroll_view import ScrollView
from ui.page_manager import Page
from ui.renderer import CONTENT_TOP, PADDING_X, SCREEN_W, truncate

_TIMEOUT = 4  # seconds for the release check


class _Mode(Enum):
    CHECKING = auto()
    UP_TO_DATE = auto()
    AVAILABLE = auto()
    NOTES = auto()
    OFFLINE = auto()
    UPDATING = auto()
    ERROR = auto()


class SystemUpdatePage(Page):
    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self.current = current_version()
        self.latest: str | None = None
        self._notes = ""
        self._sel = 0  # 0 = UPDATE NOW, 1 = RELEASE NOTES
        self.mode = _Mode.CHECKING
        self.error_msg = ""
        self.view = ScrollView()
        self._thread: threading.Thread | None = None
        self._check_result: dict | None = None
        self._checked = False

    def on_enter(self) -> None:
        self._check()

    def _check(self) -> None:
        self.mode = _Mode.CHECKING
        self._checked = False
        self._check_result = None
        self._thread = threading.Thread(target=self._fetch, daemon=True)
        self._thread.start()

    def _fetch(self) -> None:
        try:
            request = urllib.request.Request(
                releases_api_url(),
                headers={"User-Agent": "JellyBox", "Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
                text = response.read().decode("utf-8", "ignore")
            self._check_result = parse_latest_release(text)
        except (urllib.error.URLError, OSError, ValueError):
            self._check_result = None
        self._checked = True

    def update(self) -> None:
        if self.mode is not _Mode.CHECKING or not self._checked:
            return
        release = self._check_result
        if release is None:
            self.mode = _Mode.OFFLINE
            return
        self.latest = release["tag"]
        self._notes = release["notes"]
        if is_newer(self.current, self.latest):
            self.mode = _Mode.AVAILABLE
        else:
            self.mode = _Mode.UP_TO_DATE

    def handle_input(self, event: ButtonEvent) -> None:
        btn = event.button
        if self.mode is _Mode.AVAILABLE:
            if btn is Button.UP:
                self._sel = (self._sel - 1) % 2
            elif btn is Button.DOWN:
                self._sel = (self._sel + 1) % 2
            elif btn is Button.CENTER:
                if self._sel == 0:
                    self._start_update()
                else:
                    self.view.set_lines((self._notes or "no release notes").splitlines())
                    self.mode = _Mode.NOTES
            elif btn is Button.BACK:
                self.ctx.pages.pop()
        elif self.mode is _Mode.NOTES:
            if btn is Button.BACK:
                self.mode = _Mode.AVAILABLE
            elif btn is Button.DOWN:
                self.view.down()
            elif btn is Button.UP:
                self.view.up()
        elif self.mode in (_Mode.OFFLINE, _Mode.ERROR):
            if btn is Button.CENTER:
                self._check()
            elif btn is Button.BACK:
                self.ctx.pages.pop()
        elif self.mode in (_Mode.UP_TO_DATE, _Mode.UPDATING):
            if btn is Button.BACK and self.mode is _Mode.UP_TO_DATE:
                self.ctx.pages.pop()

    def _start_update(self) -> None:
        # Validate the tag before it reaches systemd; the unit re-validates too.
        if not (self.latest and is_valid_tag(self.latest)):
            self.error_msg = "BAD RELEASE TAG"
            self.mode = _Mode.ERROR
            return
        unit = f"jellybox-update@{self.latest}.service"
        result = self.ctx.commands.run(["sudo", "-n", "systemctl", "start", unit], timeout=5)
        if result.ok:
            # The updater runs in its own unit and will restart this app.
            self.mode = _Mode.UPDATING
        else:
            self.error_msg = "SETUP NEEDED (SSH)"
            self.mode = _Mode.ERROR

    def draw(self, display: Display) -> None:
        theme = self.ctx.theme
        fg = theme.foreground
        draw_header(display, theme, "SYSTEM UPDATE",
                    wifi=self.ctx.wifi.status if self.ctx.wifi else None)

        if self.mode is _Mode.NOTES:
            self.view.draw(display, theme, CONTENT_TOP, display.HEIGHT - 10)
            display.text(PADDING_X, display.HEIGHT - 10, "BACK", fg)
            return

        display.text(PADDING_X, CONTENT_TOP, "CURRENT", fg)
        display.text_right(SCREEN_W - PADDING_X, CONTENT_TOP, truncate(self.current, 12), fg)

        if self.mode is _Mode.CHECKING:
            display.text_center(CONTENT_TOP + 26, "CHECKING...", fg)
        elif self.mode is _Mode.OFFLINE:
            display.text_center(CONTENT_TOP + 20, "CHECK FAILED", fg)
            display.text_center(CONTENT_TOP + 32, "NO INTERNET", fg)
            display.text(PADDING_X, display.HEIGHT - 10, "OK=RETRY", fg)
            display.text_right(SCREEN_W - PADDING_X, display.HEIGHT - 10, "BACK", fg)
        elif self.mode is _Mode.ERROR:
            display.text_center(CONTENT_TOP + 26, self.error_msg, fg)
            display.text(PADDING_X, display.HEIGHT - 10, "OK=RETRY", fg)
            display.text_right(SCREEN_W - PADDING_X, display.HEIGHT - 10, "BACK", fg)
        elif self.mode is _Mode.UP_TO_DATE:
            display.text(PADDING_X, CONTENT_TOP + 14, "LATEST", fg)
            display.text_right(SCREEN_W - PADDING_X, CONTENT_TOP + 14,
                               truncate(self.latest or "-", 12), fg)
            display.text_center(CONTENT_TOP + 34, "UP TO DATE", fg)
            display.text_right(SCREEN_W - PADDING_X, display.HEIGHT - 10, "BACK", fg)
        elif self.mode is _Mode.UPDATING:
            display.text_center(CONTENT_TOP + 20, "UPDATING...", fg)
            display.text_center(CONTENT_TOP + 32, "RESTARTING", fg)
        elif self.mode is _Mode.AVAILABLE:
            display.text(PADDING_X, CONTENT_TOP + 14, "LATEST", fg)
            display.text_right(SCREEN_W - PADDING_X, CONTENT_TOP + 14,
                               truncate(self.latest or "-", 12), fg)
            display.text(PADDING_X, CONTENT_TOP + 34,
                         ("> " if self._sel == 0 else "  ") + "UPDATE NOW", fg)
            display.text(PADDING_X, CONTENT_TOP + 46,
                         ("> " if self._sel == 1 else "  ") + "RELEASE NOTES", fg)
            display.text_right(SCREEN_W - PADDING_X, display.HEIGHT - 10, "BACK", fg)
