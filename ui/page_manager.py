"""Page base class and the navigation stack.

A ``Page`` is one screen. The ``PageManager`` keeps a stack of them: ``push``
opens a sub-screen, ``pop`` (usually bound to BACK) returns to the previous one,
and ``replace`` swaps the current screen without growing the stack. Only the top
page is updated, drawn, and given input.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoid import cycles / hardware deps at type-check time only
    from hardware.buttons import ButtonEvent
    from hardware.display import Display
    from core.app import AppContext

log = logging.getLogger(__name__)


class Page:
    """Base class for every screen.

    Subclasses get a reference to the shared application context (``ctx``) which
    exposes the theme, settings, network status, and the page manager itself.
    """

    def __init__(self, ctx: "AppContext") -> None:
        self.ctx = ctx

    def on_enter(self) -> None:
        """Called when this page becomes the active one."""

    def on_exit(self) -> None:
        """Called when this page is left (popped or covered)."""

    def update(self) -> None:
        """Advance any per-frame state (timers, animations). Non-blocking."""

    def draw(self, display: "Display") -> None:
        """Render this page onto ``display``."""
        raise NotImplementedError

    def handle_input(self, event: "ButtonEvent") -> None:
        """React to a single button event."""


class PageManager:
    def __init__(self) -> None:
        self._stack: list[Page] = []

    @property
    def current(self) -> Page | None:
        return self._stack[-1] if self._stack else None

    @property
    def depth(self) -> int:
        return len(self._stack)

    def push(self, page: Page) -> None:
        if self._stack:
            self._stack[-1].on_exit()
        self._stack.append(page)
        page.on_enter()
        log.debug("push %s (depth=%d)", type(page).__name__, self.depth)

    def pop(self) -> Page | None:
        if not self._stack:
            return None
        page = self._stack.pop()
        page.on_exit()
        if self._stack:
            self._stack[-1].on_enter()
        log.debug("pop %s (depth=%d)", type(page).__name__, self.depth)
        return page

    def replace(self, page: Page) -> None:
        if self._stack:
            self._stack[-1].on_exit()
            self._stack[-1] = page
        else:
            self._stack.append(page)
        page.on_enter()
        log.debug("replace -> %s (depth=%d)", type(page).__name__, self.depth)

    def handle_input(self, event: "ButtonEvent") -> None:
        if self._stack:
            self._stack[-1].handle_input(event)

    def update(self) -> None:
        if self._stack:
            self._stack[-1].update()

    def draw(self, display: "Display") -> None:
        if self._stack:
            self._stack[-1].draw(display)
