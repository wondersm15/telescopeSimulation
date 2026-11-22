# Telescope Simulator: browser version

The browser version runs the **same Python code as the desktop app**, using
[Pyodide](https://pyodide.org) (CPython compiled to WebAssembly) in a background
Web Worker. It is a set of static files with no server-side code and no CDN at
runtime, so it can be hosted on any plain static host. The target host is
Cloudflare at `/apps/telescope-simulation/`.

## The desktop app is frozen
The desktop app (`telescope_sim/`, `telescope_gui/`, `main.py`, `gui.py`,
`requirements.txt`) is frozen at git tag `desktop-v1.0`. The web build copies
those packages, unchanged, into `dist/py/app.zip`.
`tests/test_desktop_freeze.py` fails on any edit to them. Everything specific to
the browser lives here, in `web/`.

## Build and check (from the repo root)

```sh
venv/bin/python web/tools/build_web.py          # → web/dist/ (fetches runtime into web/vendor/, cached)
node web/tools/smoke_node.mjs                   # run all tutorial scenarios in Pyodide (Node)
MPLBACKEND=Agg venv/bin/python web/tools/compare_desktop.py   # browser vs desktop, numerically
node web/tools/browser_check.mjs --reload       # headless Chrome at /apps/telescope-simulation/
```

## Layout

| Path | What |
|---|---|
| `static/` | front-end (HTML, JS, worker), copied into `dist/` |
| `tools/build_web.py` | fetches the pinned Pyodide runtime and wheels (sha256-verified) and assembles `dist/` |
| `tools/smoke_node.mjs` | headless run of every scenario; writes `web/smoke/*.npz` |
| `tools/compare_desktop.py` | compares those results with native desktop renders (tolerance 1e-3 relative) |
| `tools/fig_arrays.py` | figure → data arrays; used by both sides of the comparison |
| `tools/browser_check.mjs` | real-browser check under the production base path |
| `vendor/`, `dist/`, `smoke/` | generated; git-ignored |

## Pinned versions
- **Runtime:** Pyodide 314.0.8 (Python 3.14.2).
- **Pyodide packages:** numpy 2.4.6, scipy 1.18.0, matplotlib 3.10.8, Pillow 12.2.0.
- **PyPI wheels:** skyfield 1.54, jplephem 2.24 and sgp4 2.25, the same versions as the desktop.
- **Ephemeris:** JPL DE421, 16.8 MB, in `dist/data/`.
