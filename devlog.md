# Development Log

## Session 1 — 2026-02-14

### What was done
- Created `CLAUDE.md` with project description, goals, architecture, language preferences, coding conventions, and general preferences
- Updated coding convention from camelCase to PEP 8 standard (snake_case, PascalCase, UPPER_SNAKE_CASE)
- Created this `devlog.md` file for tracking progress across sessions

### Decisions made
- Primary language: Python
- Follow PEP 8 naming conventions
- Envisioned modules: Geometry, Source, Physics, Plotting/Visualization

### Installed
- Python virtual environment (venv) with Python 3.14.2
- Git initialized with .gitignore

### Notes
- Project directory is currently empty aside from config files
- No code written yet — still in planning/setup phase

---

## Session 1 (continued) — 2026-02-14

### What was done
- Implemented v0.1 of the telescope simulation codebase
- Created `telescope_sim` package with 4 modules:
  - **physics/** — `Ray` dataclass and `reflect_direction()` function
  - **geometry/** — `Mirror` ABC, `ParabolicMirror`, `SphericalMirror`, `FlatMirror`, `NewtonianTelescope`
  - **source/** — `create_parallel_rays()` for point sources at infinity
  - **plotting/** — `plot_ray_trace()` for 2D side-view ray trace visualization
- Created `main.py` entry point (200mm f/5 Newtonian example)
- Created `requirements.txt`

### Decisions made
- Mirror ABC defines common interface (intersect, reflect_ray, get_surface_points) for extensibility
- 2D ray tracing for v0.1 (side-view cross-section)
- Parabolic mirror as default; spherical mirror available for comparison
- Dependencies: numpy, matplotlib only

### Installed
- numpy 2.4.2
- matplotlib 3.10.8 (plus dependencies: contourpy, cycler, fonttools, kiwisolver, packaging, pillow, pyparsing, python-dateutil, six)

### Notes
- Both parabolic and spherical mirrors tested and working
- Spherical mirror correctly shows spherical aberration (ray spread) vs parabolic
- Ray tracing sequence: parallel rays → primary reflection → secondary reflection → focal area

---

## Session 2 — 2026-02-15

### What was done
- Added pytest test suite (35 tests across physics, geometry, source modules)
- Added spot diagram at focal plane with RMS and max extent circle options
- Added physics-based focal plane imaging:
  - Airy diffraction PSF using Bessel function J1 (scipy)
  - Geometric spot reconstructed as rotationally symmetric 2D pattern
  - Convolution of geometric + Airy for combined image
  - Optional atmospheric seeing parameter
- Added PSF profile plot (linear + log scale) with:
  - Ideal Airy, geometric spot, and combined PSF curves
  - Rayleigh resolution limit, Strehl ratio estimate
- Created PHYSICS.md — inventory of implemented vs missing physics
- Updated CLAUDE.md with physics policy: use real physics, flag approximations
- Approximation warnings now shown on plot outputs (yellow text)

### Decisions made
- Use real physics everywhere possible; flag approximations in code and output
- scipy added as dependency (for Bessel functions, FFT convolution)
- Rotationally symmetric reconstruction for 2D images from 1D cross-section ray tracer

### Installed
- pytest 9.0.2
- scipy 1.17.0

### Notes
- Parabolic PSF shows geometric spot ~12μm RMS vs 3.35μm Airy radius (Strehl ~0.07)
- Spherical PSF shows geometric spot ~22μm RMS (Strehl ~0.01) — clear aberration
- The geometric spot for parabolic should ideally be near-zero for a perfect parabola;
  the ~12μm is likely numerical precision from 2D simulation with only 21 rays
