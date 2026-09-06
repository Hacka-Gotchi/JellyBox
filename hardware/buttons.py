"""Button input abstraction.

The input source produces a list of :class:`ButtonEvent` objects each frame and
the page manager dispatches them, so a page reacts to a discrete press exactly
once without handling debouncing or edge detection itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Button(Enum):
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    CENTER = "CENTER"  # OK / select
    BACK = "BACK"
    KEY2 = "KEY2"      # aux key (Space while typing)
    KEY3 = "KEY3"      # aux key (Delete while typing)


class PressKind(Enum):
    SHORT = "short"
    LONG = "long"


@dataclass(frozen=True)
class ButtonEvent:
    button: Button
    kind: PressKind = PressKind.SHORT

    @property
    def is_long(self) -> bool:
        return self.kind is PressKind.LONG


# Long-press threshold, seconds. Concrete input sources use this to
# decide short vs long.
LONG_PRESS_SECONDS = 0.5


class InputSource:
    """Abstract source of button events.

    The application loop only knows this interface, so the GPIO button driver
    is decoupled from the UI.
    """

    def poll(self) -> list[ButtonEvent]:
        """Return button events since the last call (may be empty)."""
        raise NotImplementedError

    def should_quit(self) -> bool:
        """Return True when the input backend requests application shutdown."""
        return False

    def close(self) -> None:  # pragma: no cover - trivial
        """Release any resources. Safe to call more than once."""
