# Contributing to JellyBox

Contributions are welcome. JellyBox is a Raspberry Pi handheld, but you don't
need the hardware to work on most of it.

## Development setup

The UI, network parsers, and page logic are covered by a hardware-free test
suite. Only Pillow is required:

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests
```

Hardware is reached only through abstract interfaces (`Display`, `InputSource`),
so tests use fakes from `tests/mocks` (`FakeButtons`, `make_context()`) rather
than real drivers. Production code never imports from `tests/`.

## Architecture

Pages talk to shared services through `AppContext` (settings, theme, buttons,
page manager, command runner, dependency detection, network status) and to
hardware only through the abstractions in `hardware/`. The real drivers live in
`hardware/pi/`.

- `core/` — app loop, settings, command runner, dependency detection
- `hardware/pi/` — ST7735S display, GPIO buttons, pin map
- `network/`, `system/` — tool logic, kept pure and unit-tested
- `ui/pages/`, `ui/components/` — screens and reusable widgets
- `scripts/` — Pi install and root-owned privileged helpers

## Adding a network backend

Put the command-building and output-parsing in a `network/` (or `system/`)
module with no UI or hardware imports, and cover it with unit tests. Keeping the
parsing pure is what lets it be tested without a device or a live network.

## Adding a UI page

Create `ui/pages/<name>.py` with a `Page` subclass implementing
`handle_input`, `update`, and `draw`. Model state as an `Enum` where the page
has modes. Long-running work goes through `ctx.commands.run_async` so the UI
never blocks; anything needing root goes through a helper in `scripts/`, never
by running the app as root.

## Adding a tool to the Tools menu

Add the page, then add its label to `TOOL_ITEMS` and a factory entry in
`ui/pages/tools.py`. Check `ctx.deps.has("<binary>")` before running an external
tool so a missing dependency shows a clean message.

## Style

- Standard library first; keep dependencies minimal.
- Prefer clear names and small functions over explanatory comments. Comment
  *why* (hardware quirks, limitations, security or performance reasoning), not
  what the next line does.
- Match the existing page patterns.

## Scope

JellyBox is for network administration, diagnostics, authorized security
testing, red-team operations, and education. See [SECURITY.md](SECURITY.md).
