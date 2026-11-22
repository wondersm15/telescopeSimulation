# Handoff: Telescope Simulator (telescope-simulation)

Exported 2026-11-21 by `web/tools/export_handoff.py`.

## What it is
An interactive telescope simulator: ray tracing, diffraction, seeing and
simulated eyepiece views. The page runs the author's desktop Python
application in the browser using Pyodide (WebAssembly). It is static files
only, with no server code.

- **Route:** `/apps/telescope-simulation/`
- **Entry page:** `index.html`.
- **About page:** `about.html`: credits, licences, and the desktop download.

## Source version
- **Repository:** https://github.com/wondersm15/telescopeSimulation
- **Branch:** `feature/web-app`. The browser version lives on this branch on
  purpose; it is not merged into main.
- **Commit:** `2cc5121`
- **Desktop app:** frozen at git tag `desktop-v1.0`. The browser
  runs that code unchanged.
- **Runtime:** Pyodide 314.0.8 (Python 3.14), self-hosted.

## Output
- **Folder:** `telescope-simulation/`, 34 files.
  - `index.html`, `about.html`: the pages.
  - `assets/`: the front-end script and CSS, the Python runtime (`pyodide/`),
    the app code (`py/`), the desktop source download (`downloads/`), and
    licence texts (`licenses/`).
  - `data/de421.bsp`: the JPL planetary ephemeris, 16.8 MB. It is fetched after
    the page starts.
- **Where:** `deploy/telescope-simulation/` on branch `feature/web-app`. It is committed
  as built, so no build step is needed to deploy it.
- **Paths:** every path is relative to the page, so the folder can sit at any
  base path. The page works when refreshed at `/apps/telescope-simulation/`.

## Build and preview
From the source repository root:

```sh
venv/bin/python web/tools/build_web.py         # build into web/dist/
venv/bin/python web/tools/export_handoff.py    # fresh build + checks + this note
python3 -m http.server -d web/dist 8000        # preview at http://localhost:8000/
node web/tools/browser_check.mjs --root deploy/telescope-simulation --reload   # test at /apps/telescope-simulation/
```

The build downloads its pinned inputs once and caches them in `web/vendor/`.
Every file is sha256-checked against the Pyodide lock file or PyPI.

## Validation
Run automatically for this export:

- PASS: Layout: index.html at root, plus assets/ and data/. top level: about.html, assets, data, index.html
- PASS: Every file in the manifest exists. 7 paths
- PASS: Pages load only app-relative URLs (no CDN). checked index.html, about.html, assets/app.js
- PASS: No internal or development files (incl. inside the zip). 34 site files + 83 zip entries
- PASS: Cloudflare limits (25 MiB per file, 20,000 files). 34 files, 61.4 MB total; largest data/de421.bsp 16.8 MB
- PASS: Headless Chrome at /apps/telescope-simulation/: loads, no console errors, survives refresh. first load: ready in 6.4 s; refresh at same URL: ready in 6.0 s

Recorded in the source repository (`web/README.md`, `IMPLEMENTATION_LOG.md`):
- **Parity check:** the whole GUI runs under real Qt and under the web
  stand-in, and the two are identical: 178 steps, 22,611 widget states and
  605 plots, with zero pixel difference.
- **Test suite:** 630 tests pass. The desktop download also passes its own
  620 tests from a clean `pip install`.
- **Layout:** compared by eye against screenshots of the desktop app in all
  four modes.

## Distribution approval
- **App code:** MIT licence, © 2026 Marc Wonders.
- **Textures:**
  - Moon: NASA LROC, public domain.
  - Jupiter and Saturn: Solar System Scope, CC BY 4.0. They are credited on
    `about.html`, which every page links to.
- **Ephemeris:** JPL DE421, a NASA/JPL product, freely redistributed.
- **Software:** Pyodide (MPL 2.0), CPython (PSF), and numpy, scipy,
  matplotlib, Pillow, skyfield and their dependencies (BSD, MIT, PSF-style,
  Apache 2.0 and MPL 2.0). The licence texts are inside each wheel, and CPython's
  is in `assets/licenses/`.
- **Excluded:** internal notes (plans, logs, AI-assistant instructions,
  development history) are not in the folder or in the desktop zip, and the
  export checks enforce this.
- **Status: owner approval pending.** Marc to confirm before publishing.

## External services and headers
- **At runtime:** no external services. Every request goes to the same
  origin. The about page links to outside sites (NASA, Pyodide, Solar
  System Scope, licence texts) only as ordinary links.
- **The desktop download** contacts JPL once, on the user's own computer, to
  fetch the ephemeris. The website does not.
- **Required headers:** none special. COOP/COEP isolation is not needed.
  - `.wasm` must be served as `application/wasm`; Cloudflare's default does this.
- **If the site sets a Content-Security-Policy:**
  - `script-src` needs `'wasm-unsafe-eval'`;
  - Pyodide may also need `'unsafe-eval'`, so test with the CSP enabled;
  - `connect-src 'self'` is enough.
- **Caching:** the files under `assets/pyodide/`, `assets/py/wheels/` and
  `data/` never change within a version, so a long cache lifetime is safe.
  `index.html` should revalidate.
- **Size:**
  - first visit: about 43 MB, before compression;
  - the ephemeris: 16.8 MB more, fetched in the background;
  - repeat visits use the browser cache.
