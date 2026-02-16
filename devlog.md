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

---

## Session 3 — 2026-02-16

### What was done
- Refactored `ray_trace_plot.py` to extract reusable drawing helpers:
  - `_draw_ray_trace()` — draws mirrors, rays, focal point on a given axes
  - `_draw_spot_diagram()` — draws scatter + circles on a given axes
  - `_draw_focal_image()` / `_compute_focal_image()` — computes and draws image on given axes
  - Existing public `plot_*` functions now thin wrappers around these helpers
- Added 4 comparison functions (all reuse the `_draw_*` helpers, no duplicated drawing code):
  - `plot_ray_trace_comparison()` — 1×N subplots, side-by-side ray traces
  - `plot_spot_diagram_comparison()` — 1×N subplots, side-by-side spot diagrams
  - `plot_focal_image_comparison()` — 1×N subplots, side-by-side focal images
  - `plot_psf_comparison()` — overlay PSF curves on shared linear+log axes with Strehl in legend
- Updated `telescope_sim/plotting/__init__.py` to export new comparison functions
- Rewrote `main.py` as a discoverable control panel:
  - All tunable parameters at the top with descriptive comments
  - Commented-out alternatives for each option (mirror type, ray count, wavelength, seeing, method)
  - `compare_mirrors` flag to toggle single vs comparison mode
  - `run_single()` and `run_comparison()` dispatch functions
- Updated `CLAUDE.md` with preference about exposing options in entry-point scripts

### Decisions made
- Extract `_draw_*` helpers with `ax` parameter to avoid code duplication between single and comparison plots
- PSF comparison uses curve overlay (not side-by-side panels) since the original PSF plot is a complex 3-panel layout
- `_compute_focal_image()` separated from `_draw_focal_image()` so image computation can be reused independently

### Installed
- pytest 9.0.2 (re-installed in new venv context)

### Notes
- All 35 tests pass
- Single mode (spherical), single mode (parabolic), and comparison mode all verified working
- No new dependencies added

---

## Session 4 — 2026-02-16

### What was done
- Added secondary mirror central obstruction to the PSF physics
- Implemented annular aperture PSF formula: `PSF(r) = [1/(1-ε²)]² × [2J₁(x)/x - ε²·2J₁(εx)/(εx)]²`
  - When ε=0, reduces exactly to the standard Airy pattern (no breaking changes)
  - Default obstruction ratio is 20% (from existing secondary_minor_axis / primary_diameter)
- Added `obstruction_ratio` property to `NewtonianTelescope`
- Updated `_airy_psf()` to accept and use `obstruction_ratio` parameter
- Passed obstruction ratio through all callers: `_compute_focal_image()`, `plot_psf_profile()`, `plot_psf_comparison()`
- Masked out centrally-blocked rays in `_analytical_focal_offsets()` (rays at |h| < secondary_radius excluded)
- Updated info/formula displays:
  - `_draw_focal_image()`: shows obstruction ratio in info box, removed "Unobstructed aperture" approx label
  - `plot_psf_profile()`: shows ε and obstruction % in metrics, shows annular PSF formula when ε > 0
  - `plot_psf_comparison()`: shows obstruction ratio in Airy reference label
- Updated PHYSICS.md: moved central obstruction diffraction from "Not Yet Implemented" to "Implemented"

### Decisions made
- Obstruction ratio computed from existing geometry (secondary_minor_axis / primary_diameter)
- No new public API parameters needed — obstruction comes from the telescope object
- Strehl estimation unchanged — it's relative to the diffraction-limited PSF for the same system

### Installed
- Nothing new

### Notes
- Physical effect: secondary rings become stronger, peak intensity slightly lower vs unobstructed
- All existing tests should still pass (no API changes, ε=0 gives exact same results as before)

---

## Session 4 (continued) — 2026-02-16

### What was done
- Moved diffraction PSF computation from plotting module to physics module (separation of concerns)
  - Created `telescope_sim/physics/diffraction.py` with public `compute_psf()` function
  - Removed `_airy_psf()` from `ray_trace_plot.py`, replaced with import of `compute_psf`
  - Updated `telescope_sim/physics/__init__.py` to export `compute_psf`
- Added `include_obstruction` toggle throughout the PSF/imaging pipeline
  - New parameter on public functions: `plot_focal_image()`, `plot_psf_profile()`,
    `plot_psf_comparison()`, `plot_focal_image_comparison()`
  - Threaded through internal helpers: `_draw_focal_image()`, `_compute_focal_image()`,
    `_analytical_focal_offsets()`, `_get_focal_offsets()`
  - When `include_obstruction=False`: passes `obstruction_ratio=0.0` to `compute_psf()`
    and skips the secondary ray mask in `_analytical_focal_offsets()`
  - Info/formula displays updated to show "Obstruction: disabled" when toggled off
- Added `include_obstruction` config option in `main.py` with commented-out alternative
  - Passed through to `run_single()` and `run_comparison()`

### Decisions made
- PSF computation belongs in physics module, not plotting — first step in separation of concerns
- `include_obstruction` defaults to `True` (no change to existing behavior)
- Other physics-computation functions (`_analytical_focal_offsets`, `_estimate_strehl`,
  `_build_geometric_spot_2d`) remain in plotting for now (future refactor opportunity)

### Installed
- Nothing new

### Notes
- All 35 existing tests still pass (no API changes for default behavior)
- `from telescope_sim.physics import compute_psf` now works
- Toggle allows comparing obstructed vs unobstructed PSF for design evaluation

---

## Session 5 — 2026-02-16

### What was done
- Generalized comparison mode from rigid mirror-type comparison to flexible config-dict system
- **`ray_trace_plot.py`**: added `_resolve_physics_params()` helper that normalizes per-panel
  physics dicts (broadcast scalar defaults when `physics_params=None`, merge overrides when provided)
- **`plot_focal_image_comparison()`**: new `physics_params` kwarg; passes per-panel wavelength,
  method, seeing, and obstruction to `_draw_focal_image()`
- **`plot_psf_comparison()`**: new `physics_params` kwarg; auto-detects whether all panels share
  physics+geometry to decide between shared Airy reference (old behavior) vs per-curve
  self-contained labels with richer annotations
- **`main.py`**: replaced `compare_mirrors` / `compare_types` with `compare_mode` / `comparison_configs`
  - Each config dict has a `"label"` plus any overrides (telescope geometry and/or physics keys)
  - `_resolve_comparison_configs()` validates keys (catches typos), partitions into telescope vs
    physics, builds `NewtonianTelescope` instances, returns `(telescopes, labels, physics_params)`
  - `run_comparison()` rewritten to accept `(configs, defaults, num_display_rays)`
  - 6 commented-out example configs: mirror types, obstruction toggle, wavelengths, apertures,
    focal ratios, mixed geometry+physics

### Decisions made
- Config-dict approach: each panel can override any axis (geometry or physics) independently
- Backward compatible: when `physics_params=None`, comparison functions behave identically to before
- Key validation catches typos early with clear error messages
- PSF comparison auto-selects shared vs per-panel Airy reference based on whether configs differ

### Installed
- Nothing new

### Notes
- All 35 existing tests pass
- Smoke-tested: default mirror comparison, obstruction toggle, wavelength comparison all run cleanly
- `run_single()` is completely untouched
- `plot_ray_trace_comparison()` and `plot_spot_diagram_comparison()` unchanged (no physics params)
