"""GPIO button input for the Waveshare 1.44" LCD HAT.

Maps the HAT's joystick and keys to the six logical buttons using gpiozero,
which gives hardware debounce (``bounce_time``) and hold detection
(``hold_time``) for free. Callbacks fire on a background thread and push events
into a thread-safe queue; :meth:`poll` drains that queue each frame, matching
the app's frame-based event model.

Short vs long press: a long press fires once when the hold
crosses the threshold; a short press fires on release if no long press fired.
"""
from __future__ import annotations

import logging
import queue

from hardware.buttons import (
    LONG_PRESS_SECONDS,
    Button,
    ButtonEvent,
    InputSource,
    PressKind,
)
from hardware.pi import pins

log = logging.getLogger(__name__)

# BCM pin -> logical button (see pins.py for the rationale).
PIN_MAP: dict[int, Button] = {
    pins.JOY_UP: Button.UP,
    pins.JOY_DOWN: Button.DOWN,
    pins.JOY_LEFT: Button.LEFT,
    pins.JOY_RIGHT: Button.RIGHT,
    pins.JOY_PRESS: Button.CENTER,
    pins.KEY1: Button.BACK,
    pins.KEY2: Button.KEY2,   # Space while typing
    pins.KEY3: Button.KEY3,   # Delete while typing
}


class GpioButtons(InputSource):
    def __init__(self) -> None:
        from gpiozero import Button as GpioButton

        self._queue: "queue.Queue[ButtonEvent]" = queue.Queue()
        self._long_fired: set[int] = set()
        self._buttons = []
        for pin, logical in PIN_MAP.items():
            btn = GpioButton(
                pin, pull_up=True, bounce_time=0.02, hold_time=LONG_PRESS_SECONDS
            )
            # default-argument binding captures the current pin/logical values
            btn.when_held = lambda p=pin, b=logical: self._on_held(p, b)
            btn.when_released = lambda p=pin, b=logical: self._on_released(p, b)
            self._buttons.append(btn)
        log.info("GPIO buttons initialised (%d inputs)", len(self._buttons))

    def _on_held(self, pin: int, logical: Button) -> None:
        self._long_fired.add(pin)
        self._queue.put(ButtonEvent(logical, PressKind.LONG))

    def _on_released(self, pin: int, logical: Button) -> None:
        if pin in self._long_fired:
            self._long_fired.discard(pin)
        else:
            self._queue.put(ButtonEvent(logical, PressKind.SHORT))

    def poll(self) -> list[ButtonEvent]:
        events: list[ButtonEvent] = []
        try:
            while True:
                events.append(self._queue.get_nowait())
        except queue.Empty:
            pass
        return events

    def should_quit(self) -> bool:
        return False  # a real device quits via the power menu, not a window close

    def close(self) -> None:
        for btn in self._buttons:
            try:
                btn.close()
            except Exception:
                pass
        self._buttons = []
