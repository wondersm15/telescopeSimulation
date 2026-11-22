# Telescope Simulator: desktop app (v1.0)

This is the source code of the desktop application. It is the same code that
the browser version at `/apps/telescope-simulation/` runs, so you can use it to
check the browser version, or to work offline with the full desktop window.

## Requirements
- Python 3.11 or newer. Tested with Python 3.14 on macOS.
- About 400 MB of disk space for the Python packages (numpy, scipy,
  matplotlib, PyQt6, skyfield).
- macOS, Windows or Linux; any system where PyQt6 installs from pip.

## Install (once)
Open a terminal in this folder, then run:

```bash
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

On Windows, type `python` where these instructions say `python3`.

## Run
With the virtual environment active:

```bash
python gui.py      # the interactive application (recommended)
python main.py     # scripted run: edit the options at the top of main.py
```

**Live sky:** the first time you tick "Use live ephemeris" in a tutorial
scenario, the app downloads the 16 MB JPL DE421 ephemeris from JPL
into `~/.skyfield`. After that it works offline.

## Check the installation (optional)

```bash
python -m pytest tests/
```

All tests should pass (about one to two minutes).

## What's included
- `telescope_sim/`: the physics, optics and image-simulation code.
- `telescope_gui/`: the desktop application.
- `tests/`: the automated test suite.
- `README.md`: project overview.
- `PHYSICS.md`: which physics is real and which is approximated.
- `docs/user/`: the user guide.
- `docs/technical/`: the formulas reference.
- `telescope_sim/source/data/CREDITS.md`: sources and licences of the planet textures.

The development notes that `README.md` links to (`docs/development/`) are
internal and are not included. Some documents also mention `CLAUDE.md`, the
project's notes for its AI coding assistant, which is not included either.

## Licence
The code is under the MIT licence (`LICENSE`). The Moon texture is public
domain (NASA). The Jupiter and Saturn textures are CC BY 4.0, by Solar System
Scope. See `telescope_sim/source/data/CREDITS.md`.
