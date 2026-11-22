# Telescope Simulator: browser version

The browser version runs the **desktop application itself** (the same physics
code and the same GUI code) using [Pyodide](https://pyodide.org), which is
CPython compiled to WebAssembly. It is a set of static files with no server-side
code and no CDN at runtime, so it can be hosted on any plain static host. The
target host is Cloudflare at `/apps/telescope-simulation/`.

## The desktop app is frozen
The desktop app (`telescope_sim/`, `telescope_gui/`, `main.py`, `gui.py`,
`requirements.txt`) is frozen at git tag `desktop-v1.0`. The web build copies
those packages, unchanged, into `assets/py/app.zip`.
`tests/test_desktop_freeze.py` fails on any edit to them. Everything specific to
the browser lives here, in `web/`.

## How the desktop GUI runs in a browser
PyQt6 cannot run in a browser. `py/PyQt6/` is a small stand-in for the parts of
the PyQt6 API that the GUI uses, so `telescope_gui` imports it unchanged.

- **Widgets** keep their state in Python, as Qt does. They draw through a
  *node* (`py/qtshim/nodes.py`):
  - in the browser, each node is an HTML element (`py/qtshim/dom.py`);
  - in tests, nodes do nothing (headless).
- **Layouts** map to CSS:
  - `QVBoxLayout` / `QHBoxLayout` become flexbox; grid and form layouts become CSS grid;
  - stretch factors and size policies become `flex` values.

  The styles are in `static/qtshim.css`.
- **Plots:** `py/qtshim/mpl_backend.py` replaces matplotlib's Qt canvas. Each
  plot is shown as a PNG, the same bitmap the desktop displays.
- **Qt behaviours the GUI relies on** are reproduced:
  - signal order (exclusive radio buttons; a check box's `stateChanged` before `toggled`);
  - `blockSignals`;
  - spin-box rounding and clamping;
  - the first combo-box item becoming current;
  - visibility inherited from parent widgets;
  - timers.

  `tests/test_web_qtshim.py` pins each of these.

### Parity check: real Qt vs the stand-in
`tools/qt_parity.py` runs the full GUI twice, once under real PyQt6 (offscreen)
and once under the stand-in. Both runs use the same scripted session:
- every mode and tab;
- a set of control changes on each tab;
- every tutorial scenario, plus a "Learn more" link.

It then compares every widget's state (value, text, enabled, visible, items)
and every plot's pixels.

**Last full run:** PASS. 178 steps, 22,611 widget states and 605 plots were identical, with exactly zero pixel difference.

The live sky is compared at a fixed instant (`FROZEN_NOW`), so the Moon and planets are in the same place in both runs.

### Differences from the desktop (web only, in `py/web_app.py`)
1. **Mode switch builds once.** On the desktop, a mode switch builds the new
   mode twice: once for the radio button turning off and once for the one
   turning on. The browser builds it once. The result is identical; it saves
   several seconds.
2. **Live-sky ephemeris loads later.** The 16 MB DE421 file downloads in the
   background after start-up. If live sky is used before it arrives, it is
   fetched at that moment.
3. **No menu bar.** The desktop's menus are placeholders apart from File → Exit.
4. **No plot toolbar.** Matplotlib's zoom/pan toolbar is not available. Plots
   are static images, scaled to fit, as on the desktop.
5. **Busy indicator.** Python runs on the page's main thread, so the page
   cannot repaint while a simulation computes. Each click first shows
   "Working…", then runs.

## Build and check (from the repo root)

```sh
venv/bin/python web/tools/build_web.py          # → web/dist/ (runtime cached in web/vendor/)
venv/bin/python web/tools/qt_parity.py          # real Qt vs stand-in, whole GUI (~3 min; --quick ~1 min)
venv/bin/python -m pytest tests/test_web_qtshim.py tests/test_desktop_freeze.py
node web/tools/browser_check.mjs --reload       # headless Chrome at /apps/telescope-simulation/
node web/tools/browser_check.mjs --hash tutorial --screenshot out.png   # open a mode directly
venv/bin/python web/tools/desktop_screenshots.py OUT_DIR   # desktop screenshots to compare layout by eye
venv/bin/python web/tools/export_handoff.py     # hosting export + checks + handoff note → deploy/
```

To preview locally, serve `web/dist` with any static server and open the page.
For example:

```sh
python3 -m http.server -d web/dist
```

The page then loads from `/`. `browser_check.mjs` serves it from
`/apps/telescope-simulation/`, the path used in production. Pass
`--root DIR` to check another folder, such as an export.

## Output layout, desktop download, and hosting export
The build output follows the hosting handoff format:

- **HTML pages at the root:**
  - `index.html`: the app;
  - `about.html`: credits, licences and the desktop download.
- **`assets/`:** everything the pages load.
- **`data/`:** the ephemeris.

Paths in `assets/py/manifest.json` are relative to the site root.

**Desktop download** (`assets/downloads/telescope-simulation-desktop-v1.0.zip`)
- It is read straight from git tag `desktop-v1.0`: the code, tests, user and
  technical docs, and texture credits.
- It adds `LICENSE` and the install guide `download/INSTALL.md`.
- It leaves out internal notes: CLAUDE.md, plans, logs and `docs/development/`.
- The zip is byte-reproducible.
- Verified by a clean `pip install -r requirements.txt` in a new venv, then
  its test suite: 620 passed.

**Hosting export:** `tools/export_handoff.py` does four things.
1. Builds a fresh copy into `deploy/telescope-simulation/`.
2. Checks it:
   - the layout;
   - app-relative URLs only;
   - no internal files, including inside the zip;
   - Cloudflare's 25 MiB per-file limit.
3. Runs the browser check on that exact folder.
4. Writes `deploy/HANDOFF.md` and `deploy/DEPLOY_PROMPT.md` (the message
   for the deploying agent). Both sit beside the folder, so they are never
   published.

`deploy/` is committed on this branch, `feature/web-app`. The browser
version stays on its own branch, and the deploying agent takes the built
folder straight from GitHub. Re-run the export and commit after any change
to the web version.

### Phase-1 feasibility tools
These ran the physics code alone, without the GUI, and are kept as extra checks:
- `build_web.py --dev-pages` adds `smoke.html` and `worker.js` to the build;
- `node web/tools/smoke_node.mjs` runs every tutorial scenario in Pyodide under Node;
- `MPLBACKEND=Agg venv/bin/python web/tools/compare_desktop.py` compares those results with desktop renders.

## Layout

| Path | What |
|---|---|
| `static/` | front-end, copied into `dist/`: `index.html`, `about.html`, and `assets/` (`app.js` loads Pyodide and starts the app; `qtshim.css`; licence texts) |
| `download/INSTALL.md` | install guide shipped inside the desktop zip |
| `py/PyQt6/` | stand-in for the PyQt6 API (QtCore, QtGui, QtWidgets) |
| `py/qtshim/` | display backends (headless and DOM) and the matplotlib canvas |
| `py/web_app.py` | browser entry point; the web-only differences listed above |
| `tools/build_web.py` | fetches the pinned Pyodide runtime and wheels (sha256-verified) and assembles `dist/` |
| `tools/qt_parity.py` | whole-GUI comparison, real Qt vs stand-in |
| `tools/browser_check.mjs` | real-browser check under the production base path |
| `tools/desktop_screenshots.py` | reference screenshots of the desktop app |
| `tools/export_handoff.py` | hosting export, its checks, and the handoff note |
| `tools/fig_arrays.py` | figure → data arrays; used by the comparisons |
| `vendor/`, `dist/`, `smoke/` | generated; git-ignored |
| `../deploy/` | generated by `export_handoff.py`, **committed**: the hosting export and handoff files |

## Pinned versions
- **Runtime:** Pyodide 314.0.8 (Python 3.14.2).
- **Pyodide packages:** numpy 2.4.6, scipy 1.18.0, matplotlib 3.10.8, Pillow 12.2.0.
- **PyPI wheels:** skyfield 1.54, jplephem 2.24 and sgp4 2.25, the same versions as the desktop.
- **Ephemeris:** JPL DE421, 16.8 MB, in `data/`.
