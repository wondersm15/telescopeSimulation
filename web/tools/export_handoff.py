"""Export the browser version for hosting, with its handoff note.

Run from the repo root with the desktop venv:

    venv/bin/python web/tools/export_handoff.py [--out DIR]

1. Builds a fresh copy of the site into DIR/telescope-simulation/ (default
   DIR: deploy/, committed on the web branch so the deploying agent can take
   it straight from git).
2. Checks the copy before anything is handed over:
   - the handoff layout (index.html at the root, plus assets/ and data/);
   - every path is app-relative;
   - no internal or development files, including inside the desktop zip;
   - the file sizes fit Cloudflare's limits.
3. Runs the real-browser check (browser_check.mjs) on that exact folder,
   served at /apps/telescope-simulation/, including a refresh.
4. Writes the handoff note, DIR/HANDOFF.md, and the prompt for the deploying
   agent, DIR/DEPLOY_PROMPT.md, beside the folder rather than in it, so the
   published folder holds only public files.

The note records the source commit, the commands, the check results, and
what still needs the owner's approval. The script exits non-zero if any
check fails.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_web  # noqa: E402  (sibling tool)

APP_NAME = "telescope-simulation"
ROUTE = f"/apps/{APP_NAME}/"
DEFAULT_OUT = build_web.REPO_ROOT / "deploy"
OUT_REL = "deploy"            # as seen from the repository root
REPO_URL = "https://github.com/wondersm15/telescopeSimulation"
HANDOFF_DIR = ("/Users/marcwonders/Documents/Codex/Projects/"
               "Public Apps Deployment/artifacts/incoming/telescope-simulation/")

# Cloudflare Workers Static Assets limits (per file / per deployment).
MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_FILES = 20_000

REQUIRED = ("index.html", "about.html", "assets/app.js",
            "assets/py/manifest.json", "data/de421.bsp")
# Never published: development pages, notes, caches, AI-assistant files.
FORBIDDEN_NAME = re.compile(
    r"(^|/)(smoke\.html|worker\.js|__pycache__|\.DS_Store|CLAUDE\.md|"
    r"IMPLEMENTATION_LOG\.md|NEXT_STEPS\.md|PLAN_[^/]*|devlog\.md|"
    r"ROADMAP\.md|GUI_PLAN\.md|docs/development)(/|$)")
# A root-absolute or cross-origin URL in a page or loader would break the
# route or contact another server. (Plain links to other sites are fine.)
ABSOLUTE_LOAD = re.compile(
    r"""(src|href)\s*=\s*["']/|fetch\(\s*["'](https?:)?//|"""
    r"""import\s.*from\s+["'](https?:)?//|<script[^>]+src=["']https?:""")
LOADER_FILES = ("index.html", "about.html", "assets/app.js")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=build_web.REPO_ROOT, check=True,
                          capture_output=True, text=True).stdout.strip()


def audit(site: Path) -> list[tuple[str, bool, str]]:
    """Static checks of the exported folder: (check, passed, detail)."""
    files = sorted(p for p in site.rglob("*") if p.is_file())
    rel = [p.relative_to(site).as_posix() for p in files]
    results = []

    missing = [r for r in REQUIRED if not (site / r).is_file()]
    top = sorted(p.name for p in site.iterdir())
    results.append(("Layout: index.html at root, plus assets/ and data/",
                    not missing and top == ["about.html", "assets", "data",
                                            "index.html"],
                    f"top level: {', '.join(top)}"
                    + (f"; missing {missing}" if missing else "")))

    manifest = (site / "assets/py/manifest.json").read_text()
    listed = re.findall(r'"((?:assets|data)/[^"]+)"', manifest)
    absent = [p for p in listed if not (site / p).is_file()]
    results.append(("Every file in the manifest exists", not absent,
                    f"{len(listed)} paths" + (f"; absent {absent}" if absent else "")))

    bad_urls = [f for f in LOADER_FILES
                if ABSOLUTE_LOAD.search((site / f).read_text())]
    results.append(("Pages load only app-relative URLs (no CDN)", not bad_urls,
                    ", ".join(bad_urls) or f"checked {', '.join(LOADER_FILES)}"))

    zip_names = []
    for z in site.glob("assets/downloads/*.zip"):
        zip_names += [f"{z.name}:{n}" for n in zipfile.ZipFile(z).namelist()]
    leaked = [r for r in rel + zip_names if FORBIDDEN_NAME.search(r)]
    results.append(("No internal or development files (incl. inside the zip)",
                    not leaked, ", ".join(leaked[:5]) or
                    f"{len(rel)} site files + {len(zip_names)} zip entries"))

    biggest = max(files, key=lambda p: p.stat().st_size)
    size = biggest.stat().st_size
    total = sum(p.stat().st_size for p in files)
    results.append(("Cloudflare limits (25 MiB per file, 20,000 files)",
                    size <= MAX_FILE_BYTES and len(files) <= MAX_FILES,
                    f"{len(files)} files, {total / 1e6:.1f} MB total; largest "
                    f"{biggest.relative_to(site)} {size / 1e6:.1f} MB"))
    return results


def browser_check(site: Path) -> tuple[str, bool, str]:
    run = subprocess.run(
        ["node", str(build_web.WEB_DIR / "tools/browser_check.mjs"),
         "--root", str(site), "--reload"],
        capture_output=True, text=True, timeout=600)
    timings = re.findall(r"── (first load|refresh at same URL): (\w+) \(([\d.]+) s",
                         run.stdout)
    ok = (run.returncode == 0 and len(timings) == 2
          and all(status == "ready" for _, status, _ in timings))
    detail = "; ".join(f"{what}: {status} in {secs} s"
                       for what, status, secs in timings)
    if not ok:
        detail += "\n" + (run.stdout + run.stderr)[-1500:]
    return (f"Headless Chrome at {ROUTE}: loads, no console errors, "
            "survives refresh", ok, detail)


def handoff_note(results, site: Path) -> str:
    commit = _git("rev-parse", "--short", "HEAD")
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    dirty = " (with uncommitted changes)" if _git("status", "--porcelain") else ""
    checks = "\n".join(f"- {'PASS' if ok else 'FAIL'}: {name}. {detail}"
                       for name, ok, detail in results)
    return f"""# Handoff: Telescope Simulator ({APP_NAME})

Exported {date.today().isoformat()} by `web/tools/export_handoff.py`.

## What it is
An interactive telescope simulator: ray tracing, diffraction, seeing and
simulated eyepiece views. The page runs the author's desktop Python
application in the browser using Pyodide (WebAssembly). It is static files
only, with no server code.

- **Route:** `{ROUTE}`
- **Entry page:** `index.html`.
- **About page:** `about.html`: credits, licences, and the desktop download.

## Source version
- **Repository:** {REPO_URL}
- **Branch:** `{branch}`. The browser version lives on this branch on
  purpose; it is not merged into main.
- **Commit:** `{commit}`{dirty}
- **Desktop app:** frozen at git tag `{build_web.DESKTOP_TAG}`. The browser
  runs that code unchanged.
- **Runtime:** Pyodide {build_web.PYODIDE_VERSION} (Python 3.14), self-hosted.

## Output
- **Folder:** `{APP_NAME}/`, {sum(1 for p in site.rglob('*') if p.is_file())} files.
  - `index.html`, `about.html`: the pages.
  - `assets/`: the front-end script and CSS, the Python runtime (`pyodide/`),
    the app code (`py/`), the desktop source download (`downloads/`), and
    licence texts (`licenses/`).
  - `data/de421.bsp`: the JPL planetary ephemeris, 16.8 MB. It is fetched after
    the page starts.
- **Where:** `{OUT_REL}/{APP_NAME}/` on branch `{branch}`. It is committed
  as built, so no build step is needed to deploy it.
- **Paths:** every path is relative to the page, so the folder can sit at any
  base path. The page works when refreshed at `{ROUTE}`.

## Build and preview
From the source repository root:

```sh
venv/bin/python web/tools/build_web.py         # build into web/dist/
venv/bin/python web/tools/export_handoff.py    # fresh build + checks + this note
python3 -m http.server -d web/dist 8000        # preview at http://localhost:8000/
node web/tools/browser_check.mjs --root {OUT_REL}/{APP_NAME} --reload   # test at {ROUTE}
```

The build downloads its pinned inputs once and caches them in `web/vendor/`.
Every file is sha256-checked against the Pyodide lock file or PyPI.

## Validation
Run automatically for this export:

{checks}

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
"""


def deploy_prompt() -> str:
    """The message to give the deploying agent."""
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    return f"""# Prompt for the deploying agent: Telescope Simulator

Paste the text below into the Public Apps Deployment session.

---

Please integrate the Telescope Simulator at `{ROUTE}`.

**Get the files.** Everything is in git, built and checked, with no build
step needed.
- Repository: {REPO_URL}
- Branch: `{branch}`. Use this branch, not main.
- Folder: `{OUT_REL}/{APP_NAME}/`

```sh
git clone --depth 1 --branch {branch} {REPO_URL}.git telescope-src
cp -R telescope-src/{OUT_REL}/{APP_NAME}/ "{HANDOFF_DIR}"
```

**What it contains.**
- The folder follows the handoff format: `index.html` at the root, plus
  `assets/` and `data/` (and `about.html`).
- All paths are app-relative.
- It is static only. At runtime it makes no requests to any other origin.

**Read `{OUT_REL}/HANDOFF.md` on the same branch.** It covers:
- the source version;
- the build and preview commands;
- the validation results;
- the distribution approval and licences;
- the external services and headers.

In short:
- `.wasm` must be served as `application/wasm`.
- No COOP/COEP headers are needed.
- If a Content-Security-Policy is set, it must allow `'wasm-unsafe-eval'`.
  Pyodide may also need `'unsafe-eval'`, so test with the CSP enabled.
- Long cache lifetimes are fine for `assets/pyodide/`, `assets/py/wheels/`
  and `data/`.
- The largest file is 16.8 MB (`data/de421.bsp`). The first visit downloads
  about 43 MB.

**Check after integrating.** Open `{ROUTE}` and wait for the mode bar; it
takes 10–30 s on first load. Reload the page; it must come back. Check that
the "About · download the desktop app · credits" link opens `about.html`
and that the zip download works.

**Approval.** Do not publish publicly until Marc confirms the distribution
approval listed in HANDOFF.md.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help="folder to export into (default: deploy/)")
    args = parser.parse_args()
    site = args.out / APP_NAME

    build_web.build(site)
    results = audit(site) + [browser_check(site)]
    note = args.out / "HANDOFF.md"
    note.write_text(handoff_note(results, site))
    (args.out / "DEPLOY_PROMPT.md").write_text(deploy_prompt())

    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}\n      {detail}")
    print(f"\nSite: {site}\nNote: {note}")
    sys.exit(0 if all(ok for _, ok, _ in results) else 1)


if __name__ == "__main__":
    main()
