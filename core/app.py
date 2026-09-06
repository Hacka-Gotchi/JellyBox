"""Application context and main loop.

``AppContext`` bundles the shared services (settings, theme, buttons, page
manager, command runner, dependency detection, network status) so a page never
reaches for a global. ``App`` owns the render loop: poll input, dispatch it to
the active page, update, draw, and present. Nothing in the loop blocks -- slow
work runs on background workers via the command runner.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from hardware.buttons import InputSource
from hardware.display import Display
from ui.page_manager import PageManager
from ui.theme import Theme

log = logging.getLogger(__name__)


@dataclass
class AppContext:
    """Shared services handed to every page."""

    settings: "Settings"
    theme: Theme
    buttons: InputSource
    pages: PageManager
    commands: "CommandRunner"
    deps: "Dependencies"
    wifi: "WifiManager"


class App:
    """Owns the main loop and the hardware handles."""

    def __init__(self, ctx: AppContext, display: Display, fps: int = 20,
                 max_frames: int | None = None) -> None:
        self.ctx = ctx
        self.display = display
        self.fps = max(1, fps)
        self.max_frames = max_frames
        self._running = False

    def run(self) -> None:
        from ui.pages.boot import BootPage  # local import avoids an import cycle

        self._running = True
        self.ctx.pages.push(BootPage(self.ctx))
        self.display.set_brightness(self.ctx.settings.get("brightness", 70))

        frames = 0
        buttons = self.ctx.buttons
        try:
            while self._running:
                for event in buttons.poll():
                    self.ctx.pages.handle_input(event)

                if buttons.should_quit() or self.ctx.pages.depth == 0:
                    break

                self.ctx.pages.update()

                self.display.clear(self.ctx.theme.background)
                self.ctx.pages.draw(self.display)
                self.display.show()  # the display backend throttles to the frame rate

                frames += 1
                if self.max_frames is not None and frames >= self.max_frames:
                    break
        except KeyboardInterrupt:
            log.info("interrupted; shutting down")
        finally:
            self.shutdown()

    def stop(self) -> None:
        self._running = False

    def shutdown(self) -> None:
        self._running = False
        try:
            # Cancel any running background command so no subprocess is orphaned.
            self.ctx.commands.shutdown()
        except Exception:
            log.exception("error cancelling commands during shutdown")
        try:
            self.ctx.buttons.close()
        finally:
            self.display.close()
        logging.shutdown()


# Late imports for the annotations above; resolved lazily thanks to
# `from __future__ import annotations`.
from core.settings import Settings  # noqa: E402
from core.command_runner import CommandRunner  # noqa: E402
from core.dependencies import Dependencies  # noqa: E402
from network.wifi_status import WifiManager  # noqa: E402
