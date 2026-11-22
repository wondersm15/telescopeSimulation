"""Pull the simulated data out of a matplotlib figure, for comparison.

Shared by smoke_node.mjs (run inside Pyodide) and compare_desktop.py (run
natively), so both sides extract exactly the same things: every image shown
on any axes, and every plotted line's x/y data. Text and styling are ignored
— they are not physics.
"""

import numpy as np


def figure_arrays(fig) -> dict[str, np.ndarray]:
    arrays: dict[str, np.ndarray] = {}
    if fig is None:
        return arrays
    for a, ax in enumerate(fig.axes):
        for i, im in enumerate(ax.get_images()):
            arrays[f"ax{a}_img{i}"] = np.asarray(im.get_array(),
                                                 dtype=np.float64)
        for i, line in enumerate(ax.get_lines()):
            xy = np.asarray(line.get_xydata(), dtype=np.float64)
            if xy.size:
                arrays[f"ax{a}_line{i}"] = xy
    return arrays


def max_relative_difference(a: dict[str, np.ndarray],
                            b: dict[str, np.ndarray]) -> float:
    """Largest |Δ| across all arrays, relative to each array's own range.

    Returns inf if the two figures don't contain the same arrays.
    """
    if a.keys() != b.keys():
        return float("inf")
    worst = 0.0
    for key in a:
        x, y = a[key], b[key]
        if x.shape != y.shape:
            return float("inf")
        finite = np.isfinite(x) & np.isfinite(y)
        if not np.array_equal(np.isfinite(x), np.isfinite(y)):
            return float("inf")
        if not finite.any():
            continue
        scale = max(float(np.ptp(x[finite])), 1e-12)
        worst = max(worst, float(np.max(np.abs(x[finite] - y[finite]))) / scale)
    return worst
