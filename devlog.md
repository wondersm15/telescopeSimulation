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
