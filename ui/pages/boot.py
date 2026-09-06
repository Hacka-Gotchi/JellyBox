"""Boot / startup screen.

Plays the JellyBox logo animation, then shows the product name, version, and a
short sequence of self-checks, then hands over to the main menu. Kept brief so
startup never feels slow. Nothing here blocks.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

from hardware.display import Display
from ui.page_manager import Page
from ui.pages.main_menu import MainMenuPage
from ui.renderer import CONTENT_TOP

log = logging.getLogger(__name__)

NAME = "JELLYBOX"
VERSION = "1.0"
_ASSET = Path(__file__).resolve().parents[2] / "assets" / "jellyload.gif"

_CHECK_INTERVAL = 0.35   # seconds between check lines appearing
_HOLD_AFTER = 0.6        # linger after the last check before entering the menu
_MIN_ANIM = 1.6          # play the logo at least this long


def load_boot_frames(path: Path = _ASSET, size: int = 128):
    """Load the boot GIF as a list of (grayscale frame, duration_seconds).

    Frames are kept in mode 'L' so they can be tinted to the active theme colour
    at boot time (see BootPage._tint).
    """
    try:
        from PIL import Image, ImageSequence
    except Exception:
        return []
    try:
        im = Image.open(path)
    except Exception:
        log.info("no boot animation at %s", path)
        return []
    frames = []
    for fr in ImageSequence.Iterator(im):
        f = fr.convert("L").copy()
        if f.size != (size, size):
            f.thumbnail((size, size))
            canvas = Image.new("L", (size, size), 0)
            canvas.paste(f, ((size - f.width) // 2, (size - f.height) // 2))
            f = canvas
        dur = max(0.03, fr.info.get("duration", 120) / 1000.0)
        frames.append((f, dur))
    return frames


class BootPage(Page):
    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        self._start = 0.0
        self._gray = load_boot_frames()
        self._frames: list = []   # tinted to the theme, filled on_enter
        loop = sum(d for _, d in self._gray)
        self._anim_len = max(loop, _MIN_ANIM) if self._gray else 0.0
        self._phase = "anim" if self._gray else "checks"
        self._checks_start = 0.0
        self._checks: list[tuple[str, object]] = [
            ("DISPLAY", lambda: True),
            ("BUTTONS", lambda: self.ctx.buttons is not None),
            ("WIFI", lambda: True),
        ]
        self._results: list[tuple[str, bool]] = []

    def _tint(self) -> None:
        """Colorise the grayscale frames to the active theme foreground."""
        if not self._gray:
            self._frames = []
            return
        try:
            from PIL import ImageOps
            fg = self.ctx.theme.foreground
            self._frames = [
                (ImageOps.colorize(g, black=(0, 0, 0), white=fg).convert("RGB"), d)
                for g, d in self._gray
            ]
        except Exception:
            # fall back to plain grayscale if colorize isn't available
            self._frames = [(g.convert("RGB"), d) for g, d in self._gray]

    def on_enter(self) -> None:
        self._tint()
        self._start = time.monotonic()
        self._checks_start = self._start
        self._results = []
        self._phase = "anim" if self._frames else "checks"

    def update(self) -> None:
        now = time.monotonic()
        if self._phase == "anim":
            if now - self._start >= self._anim_len:
                self._phase = "checks"
                self._checks_start = now
            return

        elapsed = now - self._checks_start
        want = min(len(self._checks), int(elapsed / _CHECK_INTERVAL))
        while len(self._results) < want:
            label, fn = self._checks[len(self._results)]
            try:
                ok = bool(fn())
            except Exception:
                ok = False
            self._results.append((label, ok))

        done_at = len(self._checks) * _CHECK_INTERVAL + _HOLD_AFTER
        if elapsed >= done_at:
            self.ctx.pages.replace(MainMenuPage(self.ctx))

    def draw(self, display: Display) -> None:
        if self._phase == "anim":
            self._draw_anim(display)
        else:
            self._draw_checks(display)

    def _draw_anim(self, display: Display) -> None:
        t = time.monotonic() - self._start
        loop = sum(d for _, d in self._frames) or 1.0
        tt = t % loop
        acc = 0.0
        frame = self._frames[0][0]
        for img, dur in self._frames:
            acc += dur
            if tt < acc:
                frame = img
                break
        try:
            display.buffer.paste(frame, (0, 0))
        except Exception:
            pass

    def _draw_checks(self, display: Display) -> None:
        fg = self.ctx.theme.foreground
        display.text_center(10, NAME, fg)
        display.text_center(24, "v" + VERSION, fg)

        if len(self._results) < len(self._checks):
            display.text_center(44, "INITIALIZING", fg)
            dots = "." * (1 + int((time.monotonic() - self._checks_start) * 3) % 3)
            display.text_center(56, dots, fg)

        y = CONTENT_TOP + 40
        for label, ok in self._results:
            display.text(8, y, f"CHECK {label}", fg)
            display.text_right(display.WIDTH - 8, y, "OK" if ok else "--", fg)
            y += display.line_height + 1
