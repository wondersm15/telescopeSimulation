"""Check the browser build's renders against the desktop app.

Run after web/tools/smoke_node.mjs, with the desktop venv:

    MPLBACKEND=Agg venv/bin/python web/tools/compare_desktop.py

Re-runs each tutorial scenario natively with the same arguments the smoke
test used and compares the figure data it saved (web/smoke/<key>.npz),
extracted on both sides by fig_arrays.figure_arrays. The
browser runs the same Python source, so any difference comes from library
builds (Pyodide numpy/scipy vs the desktop's) and should be at floating-point
noise level. Exits non-zero if any scenario exceeds TOLERANCE.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fig_arrays import figure_arrays, max_relative_difference  # noqa: E402

# Relative to each array's own range; 1e-3 is a quarter of one 8-bit level.
TOLERANCE = 1e-3
SMOKE_DIR = REPO_ROOT / "web" / "smoke"


def desktop_arrays(scenario) -> dict[str, np.ndarray]:
    import matplotlib.pyplot as plt
    from telescope_gui.tutorial_mode.scenario_runner import run_scenario_side

    # Must match the call in smoke_node.mjs.
    fig, _info, _err = run_scenario_side(
        scenario.after_telescope, scenario.after_source,
        scenario.plot_function,
        wavelength_nm=scenario.after_wavelength_nm,
        seeing_arcsec=scenario.after_seeing_arcsec,
        polychromatic=scenario.after_polychromatic,
        display_stretch=scenario.after_display_stretch or "linear")
    arrays = figure_arrays(fig)
    plt.close("all")
    return arrays


def main() -> int:
    from telescope_gui.tutorial_mode.scenario_registry import SCENARIOS

    items = (SCENARIOS.items() if isinstance(SCENARIOS, dict)
             else enumerate(SCENARIOS))
    failures = compared = 0
    for key, scenario in items:
        browser_file = SMOKE_DIR / f"{key}.npz"
        if not browser_file.exists():
            continue
        with np.load(browser_file) as npz:
            browser = {name: npz[name] for name in npz.files}
        diff = max_relative_difference(desktop_arrays(scenario), browser)
        compared += 1
        ok = diff <= TOLERANCE and len(browser) > 0
        failures += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {key:>3} {len(browser):3d} arrays  "
              f"max rel |Δ| {diff:.1e}  {scenario.title}")
    print(f"{compared} compared, {failures} over tolerance {TOLERANCE:g}")
    return 1 if failures or not compared else 0


if __name__ == "__main__":
    sys.exit(main())
