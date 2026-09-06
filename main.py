#!/usr/bin/env python3
"""JellyBox entry point.

Runs the handheld application on the Raspberry Pi hardware:

    python main.py

The LCD, buttons, and network status are all real hardware.
"""
from __future__ import annotations

import argparse
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = BASE_DIR / "config" / "settings.json"
LOG_FILE = BASE_DIR / "logs" / "jellybox.log"


def setup_logging(verbose: bool) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    root.handlers.clear()

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    # Rotate so the log can't fill the SD card.
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=512_000, backupCount=3)
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="jellybox", description="JellyBox")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG),
                        help="path to settings.json")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    return parser.parse_args(argv)


def build_app(args: argparse.Namespace):
    from core.app import App, AppContext
    from core.command_runner import CommandRunner
    from core.dependencies import Dependencies
    from core.settings import Settings
    from network.wifi_status import SysfsWifiProvider, WifiManager
    from ui.page_manager import PageManager
    from ui.theme import Theme

    settings = Settings.load(args.config)
    theme = Theme(name=settings.get("theme", "green"))

    # The Pi drivers import luma/gpiozero lazily, so a missing library or a
    # hardware fault both surface here with an actionable message.
    try:
        from hardware.pi.buttons_gpio import GpioButtons
        from hardware.pi.display_st7735 import St7735Display

        display = St7735Display(fps=20, brightness=settings.get("brightness", 70))
        buttons = GpioButtons()
    except ImportError as exc:
        print(f"Pi hardware libraries missing: {exc}", file=sys.stderr)
        print("Install them with:  pip install -r requirements-pi.txt", file=sys.stderr)
        raise SystemExit(2)
    except Exception as exc:
        print(f"Failed to initialise the display/buttons: {exc}", file=sys.stderr)
        print("Check SPI is enabled (sudo raspi-config) and the HAT is seated.",
              file=sys.stderr)
        raise SystemExit(2)

    ctx = AppContext(
        settings=settings,
        theme=theme,
        buttons=buttons,
        pages=PageManager(),
        commands=CommandRunner(),
        deps=Dependencies(),
        wifi=WifiManager(SysfsWifiProvider()),
    )
    return App(ctx, display, fps=20)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    setup_logging(args.verbose)
    log = logging.getLogger("main")

    log.info("starting JellyBox")
    build_app(args).run()
    log.info("JellyBox exited")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
