"""Support code for the PyQt6 stand-in: display nodes, styles, matplotlib.

Call `install()` before importing telescope_gui. It points matplotlib's Qt
backend at `qtshim.mpl_backend` and selects the non-interactive Agg
renderer. Rendering to a real page additionally needs `qtshim.dom.install()`
(browser only); without it widgets run headless, which the parity tests use.
"""

from __future__ import annotations

import sys


def install() -> None:
    import matplotlib
    matplotlib.use("Agg")
    from qtshim import mpl_backend
    sys.modules["matplotlib.backends.backend_qtagg"] = mpl_backend
