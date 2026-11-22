"""Browser entry point: runs the unmodified desktop MainWindow in the page.

Called from web/static/app.js once Pyodide and the packages are loaded:

    import web_app; web_app.start(container_element, mode)

Three web-only adjustments are made here, none touching desktop code:

1. Mode switching builds the new mode once instead of twice. On the
   desktop each radio's `toggled` signal calls MainWindow.switch_mode, so a
   switch runs it for the radio turning off *and* the one turning on (both
   see the new mode checked; the first build is thrown away). In the
   browser that wasted build is several seconds, so only the radio turning
   on triggers it. The result is identical.
2. The 16 MB DE421 ephemeris (live-sky sizes) is not part of the initial
   download. app.js fetches it in the background; if live sky is used
   before it arrives, it is fetched synchronously at that point.
3. The window has no menu bar (the desktop's menus are placeholders apart
   from File → Exit).
"""

from __future__ import annotations

import os

EPHEMERIS_PATH = os.path.expanduser("~/.skyfield/de421.bsp")


def _single_build_mode_switch(window) -> None:
    radios = (window.single_mode_radio, window.comparison_mode_radio,
              window.reference_mode_radio, window.tutorial_mode_radio)
    for radio in radios:
        radio.toggled.disconnect(window.switch_mode)
        radio.toggled.connect(lambda checked: checked and window.switch_mode())


def _ephemeris_on_demand() -> None:
    import js
    from telescope_sim.source import realtime

    original = realtime._load_ephemeris

    def load():
        if not os.path.exists(EPHEMERIS_PATH):
            js.telescopeApp.loadEphemerisNow()
        return original()

    realtime._load_ephemeris = load


def start(container, mode: str | None = None):
    import qtshim
    qtshim.install()
    from qtshim import dom
    dom.install()
    _ephemeris_on_demand()

    from PyQt6.QtWidgets import QApplication
    from telescope_gui.main_window import MainWindow

    app = QApplication([])
    window = MainWindow()
    _single_build_mode_switch(window)
    window.show()
    dom.mount(window, container)
    if mode:
        radio = getattr(window, f"{mode}_mode_radio", None)
        if radio is not None:
            radio.click()
    # Keep references alive for the page's lifetime.
    start.app, start.window = app, window
    return window
