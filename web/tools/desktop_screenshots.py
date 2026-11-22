"""Screenshot the real desktop app (PyQt6, offscreen) in each mode.

Reference images for judging the browser layout by eye:

    venv/bin/python web/tools/desktop_screenshots.py OUT_DIR [WIDTH HEIGHT]

Writes OUT_DIR/desktop-<mode>.png for single, comparison, reference and
tutorial (tutorial with its first scenario loaded).
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PyQt6.QtWidgets import QApplication  # noqa: E402

from telescope_gui.main_window import MainWindow  # noqa: E402


def main() -> None:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    width, height = (int(v) for v in sys.argv[2:4]) if len(sys.argv) > 3 else (1400, 870)
    app = QApplication([])
    window = MainWindow()
    window.resize(width, height)
    window.show()
    for mode in ("single", "comparison", "reference", "tutorial"):
        getattr(window, f"{mode}_mode_radio").click()
        app.processEvents()
        if mode == "tutorial":
            tab = window.tab_widget.widget(0)
            next(iter(tab.sidebar._buttons.values())).click()
        for _ in range(5):
            app.processEvents()
        window.grab().save(str(out / f"desktop-{mode}.png"))
        print(out / f"desktop-{mode}.png")


if __name__ == "__main__":
    main()
