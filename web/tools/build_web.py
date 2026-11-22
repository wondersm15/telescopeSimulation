"""Build the browser version of the telescope simulator into web/dist/.

Run with the desktop venv from the repo root:

    venv/bin/python web/tools/build_web.py

What it does:
1. Fetches a self-contained Pyodide runtime (core + only the packages the
   simulator needs) into web/vendor/ — cached, sha256-verified, never
   committed. No CDN is used at runtime: the export works on a plain static
   server.
Output layout (the hosting handoff format): HTML pages at the root,
everything they load under assets/, the ephemeris under data/. Paths in
assets/py/manifest.json are relative to the site root.

2. Zips the desktop Python packages, UNCHANGED, into assets/py/app.zip. The
   browser runs the same physics code as the desktop app; the desktop code is
   frozen at tag desktop-v1.0 (see tests/test_desktop_freeze.py).
3. Zips the browser layer (web/py/: the Qt stand-in and the entry
   module) into assets/py/web.zip.
4. Copies the static front-end (web/static/) into dist/. The phase-1
   test page (smoke.html + worker.js) is left out unless --dev-pages.
5. Packages the desktop app's source, read straight from git tag
   desktop-v1.0, as assets/downloads/telescope-simulation-desktop-v1.0.zip,
   with LICENSE and an install guide (web/download/INSTALL.md). Internal
   notes (CLAUDE.md, plans, logs, docs/development/) are not included.
   The app's LICENSE goes to assets/licenses/ for about.html (credits).

Versions are pinned so a rebuild is reproducible. Pyodide 314.x ships
Python 3.14, matching the desktop venv.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import subprocess
import tarfile
import time
import urllib.request
import zipfile
from pathlib import Path

PYODIDE_VERSION = "314.0.8"
PYODIDE_CDN = f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full"
PYODIDE_CORE_URL = (
    "https://github.com/pyodide/pyodide/releases/download/"
    f"{PYODIDE_VERSION}/pyodide-core-{PYODIDE_VERSION}.tar.bz2")

# Pyodide-built packages: their dependency closure is resolved from the lock.
PYODIDE_PACKAGES = ("numpy", "scipy", "matplotlib", "pillow")

# Pure-Python wheels from PyPI, pinned to the desktop requirements.txt, for
# the live-sky ephemeris (telescope_sim/source/realtime.py).
PYPI_WHEELS = (("skyfield", "1.54"), ("jplephem", "2.24"), ("sgp4", "2.25"),
               ("certifi", "2026.5.20"))

DE421_URL = "https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de421.bsp"
DE421_LOCAL_CACHE = Path.home() / ".skyfield" / "de421.bsp"

# The frozen desktop code shipped to the browser, as-is.
APP_PACKAGES = ("telescope_sim", "telescope_gui")

REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = REPO_ROOT / "web"

# The desktop download: the frozen release, public files only.
DESKTOP_TAG = "desktop-v1.0"
DESKTOP_NAME = f"telescope-simulation-{DESKTOP_TAG}"
DESKTOP_PUBLIC_PATHS = ("telescope_sim", "telescope_gui", "tests", "main.py",
                        "gui.py", "requirements.txt", "README.md",
                        "PHYSICS.md", "docs/user", "docs/technical")
# Added to the download from the current tree (published after the tag).
DESKTOP_EXTRA_FILES = {"LICENSE": REPO_ROOT / "LICENSE",
                       "INSTALL.md": WEB_DIR / "download" / "INSTALL.md"}
VENDOR_DIR = WEB_DIR / "vendor"
STATIC_DIR = WEB_DIR / "static"
WEB_PY_DIR = WEB_DIR / "py"
DEFAULT_DIST = WEB_DIR / "dist"


# ── Downloads ─────────────────────────────────────────────────────────

def _download(url: str, dest: Path, sha256: str | None = None) -> Path:
    """Download url to dest unless a verified copy is already there."""
    if dest.exists() and (sha256 is None or _sha256(dest) == sha256):
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  fetch {url}")
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url) as resp, open(tmp, "wb") as out:
        shutil.copyfileobj(resp, out)
    if sha256 is not None and _sha256(tmp) != sha256:
        tmp.unlink()
        raise RuntimeError(f"sha256 mismatch for {url}")
    tmp.rename(dest)
    return dest


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _dependency_closure(lock: dict, names) -> list[str]:
    packages = lock["packages"]
    seen: set[str] = set()
    stack = list(names)
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        if name not in packages:
            raise KeyError(f"{name} is not in pyodide-lock.json")
        seen.add(name)
        stack.extend(packages[name].get("depends", []))
    return sorted(seen)


def fetch_pyodide() -> Path:
    """Pyodide core + needed packages into web/vendor/pyodide/."""
    pyodide_dir = VENDOR_DIR / "pyodide"
    archive = _download(PYODIDE_CORE_URL,
                        VENDOR_DIR / f"pyodide-core-{PYODIDE_VERSION}.tar.bz2")
    if not (pyodide_dir / "pyodide.mjs").exists():
        with tarfile.open(archive) as tar:
            tar.extractall(VENDOR_DIR, filter="data")  # → vendor/pyodide/

    # The core tarball's lock lists every package; we ship only our closure.
    lock = json.loads((pyodide_dir / "pyodide-lock.json").read_text())
    for name in _dependency_closure(lock, PYODIDE_PACKAGES):
        entry = lock["packages"][name]
        _download(f"{PYODIDE_CDN}/{entry['file_name']}",
                  pyodide_dir / entry["file_name"], entry["sha256"])
    return pyodide_dir


def fetch_pypi_wheels() -> list[Path]:
    wheels = []
    for name, version in PYPI_WHEELS:
        meta = json.load(urllib.request.urlopen(
            f"https://pypi.org/pypi/{name}/{version}/json"))
        wheel = next(f for f in meta["urls"]
                     if f["filename"].endswith("py3-none-any.whl"))
        wheels.append(_download(wheel["url"],
                                VENDOR_DIR / "wheels" / wheel["filename"],
                                wheel["digests"]["sha256"]))
    return wheels


def fetch_de421() -> Path:
    dest = VENDOR_DIR / "data" / "de421.bsp"
    if not dest.exists() and DE421_LOCAL_CACHE.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(DE421_LOCAL_CACHE, dest)
    return _download(DE421_URL, dest)


# ── Bundling ──────────────────────────────────────────────────────────

def bundle(dest_zip: Path, root: Path, entries) -> None:
    """Zip `entries` (files or package folders under `root`), no caches."""
    dest_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for entry in entries:
            top = root / entry
            paths = [top] if top.is_file() else sorted(top.rglob("*"))
            for path in paths:
                if path.is_dir() or "__pycache__" in path.parts:
                    continue
                zf.write(path, path.relative_to(root).as_posix())


def bundle_desktop_source(dest_zip: Path) -> None:
    """Zip the public desktop files at DESKTOP_TAG, plus the extras.

    Reads from git, not the working tree, so the download is exactly the
    tagged release. Every entry gets the tag's timestamp, so rebuilding
    gives a byte-identical zip.
    """
    tar_bytes = subprocess.run(
        ["git", "archive", "--format=tar", DESKTOP_TAG, "--",
         *DESKTOP_PUBLIC_PATHS],
        cwd=REPO_ROOT, check=True, capture_output=True).stdout
    dest_zip.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as tar, \
            zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        files = [m for m in tar.getmembers() if m.isfile()]
        stamp = time.gmtime(files[0].mtime)[:6]   # the tag's commit time

        def add(name: str, data: bytes) -> None:
            info = zipfile.ZipInfo(f"{DESKTOP_NAME}/{name}", stamp)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, data)

        for member in files:
            add(member.name, tar.extractfile(member).read())
        for name, source in DESKTOP_EXTRA_FILES.items():
            add(name, source.read_bytes())


# Runtime files only used by Node / the command-line launcher.
PYODIDE_NOT_FOR_BROWSER = ("python", "python.bat", "python.exe",
                           "python_cli_entry.mjs", "package.json", "*.d.ts",
                           "*.part")
# Development pages (the phase-1 feasibility test); not published.
DEV_PAGES = ("smoke.html", "worker.js")


def build(dist: Path, dev_pages: bool = False) -> None:
    print("Fetching runtime (cached in web/vendor/)…")
    pyodide_dir = fetch_pyodide()
    wheels = fetch_pypi_wheels()
    de421 = fetch_de421()

    print(f"Assembling {dist}…")
    if dist.exists():
        shutil.rmtree(dist)
    assets = dist / "assets"
    rel = lambda path: path.relative_to(dist).as_posix()   # manifest paths

    shutil.copytree(pyodide_dir, assets / "pyodide",
                    ignore=shutil.ignore_patterns(*PYODIDE_NOT_FOR_BROWSER))
    (assets / "py" / "wheels").mkdir(parents=True)
    wheel_paths = [assets / "py" / "wheels" / w.name for w in wheels]
    for wheel, dest in zip(wheels, wheel_paths):
        shutil.copy2(wheel, dest)
    ephemeris = dist / "data" / de421.name
    ephemeris.parent.mkdir(parents=True)
    shutil.copy2(de421, ephemeris)
    app_zip, web_zip = assets / "py" / "app.zip", assets / "py" / "web.zip"
    bundle(app_zip, REPO_ROOT, APP_PACKAGES)
    bundle(web_zip, WEB_PY_DIR, sorted(p.name for p in WEB_PY_DIR.iterdir()
                                       if p.name != "__pycache__"))
    shutil.copytree(STATIC_DIR, dist, dirs_exist_ok=True,
                    ignore=None if dev_pages else shutil.ignore_patterns(*DEV_PAGES))
    bundle_desktop_source(assets / "downloads" / f"{DESKTOP_NAME}.zip")
    shutil.copy2(REPO_ROOT / "LICENSE", assets / "licenses" / "LICENSE.txt")

    manifest = {
        "pyodide": PYODIDE_VERSION,
        "pyodide_packages": list(PYODIDE_PACKAGES),
        "wheels": [rel(p) for p in wheel_paths],
        "app_zip": rel(app_zip),
        "web_zip": rel(web_zip),
        "ephemeris": rel(ephemeris),
    }
    (assets / "py" / "manifest.json").write_text(json.dumps(manifest, indent=2))
    total = sum(p.stat().st_size for p in dist.rglob("*") if p.is_file())
    print(f"Done: {total / 1e6:.1f} MB in {dist}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dist", type=Path, default=DEFAULT_DIST,
                        help="output folder (default: web/dist)")
    parser.add_argument("--dev-pages", action="store_true",
                        help="also copy the development test page "
                             "(smoke.html + worker.js)")
    args = parser.parse_args()
    build(args.dist, dev_pages=args.dev_pages)


if __name__ == "__main__":
    main()
