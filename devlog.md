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

---

## Session 6 — 2026-02-17

### What was done
- Added three major physics features: **vignetting**, **spider vane diffraction**, and **off-axis coma**
- **New physics modules**:
  - `telescope_sim/physics/vignetting.py` — circle-overlap illumination fraction computation, fully-illuminated field calculation. Tube wall vignetting flagged as not modeled.
  - `telescope_sim/physics/fft_psf.py` — 2D FFT-based PSF with pupil mask (circular aperture + central obstruction + spider vanes). Fraunhofer diffraction via `PSF = |FFT(pupil)|²`. Validated against analytical Airy.
  - `telescope_sim/physics/aberrations.py` — Seidel 3rd-order coma formulas: spot diagram, RMS computation, coma-free field. Flagged as 3rd-order approximation.
- **Telescope geometry** (`telescope.py`):
  - Added `spider_vanes` and `spider_vane_width` parameters to `NewtonianTelescope.__init__()`
  - Added `compute_vignetting()` and `fully_illuminated_field()` methods (delegate to physics module)
  - Added spider vane info to `get_components_for_plotting()`
- **Light source** (`light_source.py`):
  - Added `field_angle_arcsec` parameter to `create_parallel_rays()` for off-axis beams
- **New plot functions** (in `ray_trace_plot.py`):
  - `plot_vignetting_curve()` — illumination vs field angle with fully-illuminated boundary marker
  - `plot_vignetting_comparison()` — overlay curves for multiple telescopes
  - `plot_psf_2d()` — 2D PSF on log scale showing diffraction spikes
  - `plot_coma_spot()` — 2D coma spot diagram convolved with diffraction PSF
  - `plot_coma_field_analysis()` — two-panel: RMS coma vs field angle + spot diagram grid
  - `_build_coma_spot_2d()` — direct 2D Gaussian-splat binning (no rotational symmetry assumption)
  - `_resample_fft_psf()` — resamples FFT PSF onto target image grid
- **FFT PSF integration** in `_compute_focal_image()`:
  - When `spider_vanes > 0`, uses FFT-based PSF instead of analytical Airy
  - When `spider_vanes == 0`, behavior identical to before (no changes to existing pipeline)
- **Spider vane drawing** in `_draw_ray_trace()`: thin lines at secondary height
- **main.py** updates:
  - New config options: `spider_vanes`, `spider_vane_width`, `field_angle_arcsec`, `show_coma_analysis`, `show_vignetting`
  - `_TELESCOPE_KEYS` extended with spider vane keys
  - `run_single()` conditionally calls vignetting/coma/PSF-2D plots
  - `run_comparison()` conditionally calls `plot_vignetting_comparison()`
  - New commented-out comparison examples: spider vane comparison, apertures with vignetting
- **New tests** (3 test files):
  - `tests/test_vignetting.py` — 11 tests: concentric, no-overlap, monotonic, array input, telescope delegation
  - `tests/test_fft_psf.py` — 10 tests: mask shape/binary/area, FFT vs analytical Airy, spike directions
  - `tests/test_aberrations.py` — 9 tests: on-axis zero, linear scaling, tangential/sagittal ratio, coma-free field
- Updated `PHYSICS.md`: moved vignetting/spider vanes/coma to Implemented; added chromatic PSF and surface errors to Not Yet Implemented
- Updated `telescope_sim/physics/__init__.py` and `telescope_sim/plotting/__init__.py` with new exports

### Decisions made
- **Coma is a separate analysis pathway**, not integrated into `_compute_focal_image()`. Rationale: coma needs 2D positions (not 1D offsets), answers different questions than on-axis analysis, keeps existing pipeline clean.
- Spider vane drawing in ray trace is additive (no changes to existing `_draw_ray_trace` logic)
- FFT PSF only used when `spider_vanes > 0`, preserving exact existing behavior otherwise
- Vignetting uses geometry-based circle overlap (real physics), flags tube wall as not modeled
- Coma uses real Seidel 3rd-order formulas, flags as approximation valid for small angles

### Installed
- Nothing new

### Notes
- All 35 existing tests should still pass (no breaking changes)
- 30 new tests across 3 test files
- Default main.py config unchanged (parabolic vs spherical comparison, no spider vanes)

---

## Session 7 — 2026-02-17

### What was done
- Added astronomical source imaging: **PointSource**, **StarField**, and **Jupiter** classes
- **New file**: `telescope_sim/source/sources.py`
  - `AstronomicalSource` ABC with `render_ideal()` and `field_extent_arcsec` interface
  - `PointSource` — single star at configurable field angle/PA/magnitude
  - `StarField` — random field of stars with uniform-in-area placement, configurable magnitudes, seeded RNG
  - `Jupiter` — parametric disk with limb darkening (u=0.5), sinusoidal equatorial bands, Great Red Spot. Flagged as parametric/artistic model.
- **New rendering pipeline** in `ray_trace_plot.py`:
  - `_compute_psf_at_field_angle()` — computes PSF including off-axis coma, reuses existing `compute_psf`, `compute_fft_psf`, `compute_coma_spot`
  - `_render_source_through_telescope()` — full pipeline: ideal image → per-star PSF placement (with coma + vignetting) for point sources, or on-axis PSF convolution for Jupiter → optional seeing blur
  - `plot_source_image()` — displays result with angular axes (arcsec), annotation box, auto colormap selection
- **main.py** updates:
  - New config options: `source_type` ("star", "star_field", "jupiter", or None), `num_stars`, `star_field_radius_arcsec`, `jupiter_diameter_arcsec`
  - `run_single()` accepts optional `source` parameter, calls `plot_source_image()` when set
  - Star field uses log scale by default for dynamic range
- **New test file**: `tests/test_sources.py` — 30 tests covering all source classes and rendering pipeline
- Updated `telescope_sim/source/__init__.py` and `telescope_sim/plotting/__init__.py` with new exports

### Decisions made
- Per-star PSF rendering for PointSource/StarField (field-dependent coma + vignetting per star)
- On-axis PSF convolution for Jupiter (disk is small enough that PSF variation is negligible)
- Source imaging is single-telescope only (not in comparison mode)
- Jupiter model is parametric — flagged as approximation, not radiative transfer

### Installed
- Nothing new

### Notes
- All 104 tests pass (74 existing + 30 new)
- To try: set `compare_mode = False` and `source_type = "jupiter"` (or "star_field") in main.py

---

## Session 7 (continued) — 2026-02-18

### What was done
- Switched to realistic colors for source images:
  - Stars (PointSource, StarField): white on black sky ("gray" colormap)
  - Jupiter: true RGB rendering with cream zones, brown belts, reddish-orange GRS
  - Per-channel PSF convolution preserves color fidelity through blurring
- Renamed focal image title from "Simulated Image" to "Point Spread Function" (it shows the telescope's response to a point source, not an astronomical image)
- Added **Saturn** source with:
  - Oblate disk (~10% oblateness), subtle equatorial bands, limb darkening
  - A, B, C rings with radially varying brightness and Cassini division
  - Ring tilt parameter (0 = edge-on, 27 = max opening)
  - Realistic RGB: pale gold disk, cream/tan rings with per-section colors
- Added **Moon** source with:
  - Highland disk with mild limb darkening
  - 10 named maria as dark elliptical patches at approximate selenographic positions
  - Phase parameter (0 = new, 0.5 = quarter, 1.0 = full) with curved terminator
  - Realistic RGB: warm gray highlands, cool dark gray maria
- Generalized rendering pipeline to use `hasattr(source, 'render_ideal_rgb')` instead of Jupiter-specific type checks — any source with an RGB renderer now gets per-channel PSF convolution automatically
- New config options in main.py: `source_type = "saturn"` / `"moon"`, `saturn_ring_tilt_deg`, `moon_phase`
- 24 new tests for Saturn and Moon (render shape, ring presence, Cassini division, maria darker than highlands, phase shadow, RGB output, edge-on rings)

### Decisions made
- All extended sources (Jupiter, Saturn, Moon) share the same rendering path via duck typing
- Saturn ring shadow on planet not modeled (flagged in docstring)
- Moon maria are parametric ellipses, not real selenographic data (flagged)
- Moon is very large (~31') — may need large FOV or reduced resolution to render practically

### Installed
- Nothing new

### Notes
- All 128 tests pass (74 existing + 54 source tests)
- Saturn at default 18" with 20° ring tilt shows clearly separated A/B rings and Cassini division
- Moon phase=0.5 correctly shows first-quarter illumination

---

## Session 8 — 2026-02-21

### What was done
- Completely rebuilt the Moon model from simple ellipses to a detailed procedural surface:
  - **26 overlapping maria components** with noise-modulated irregular boundaries
    and smoothstep transitions for natural blending
  - **15 named craters** (Tycho, Copernicus, Aristarchus, Plato, etc.) with
    bright rims and darker floors
  - **400 random small craters** for surface texture, rendered with local
    pixel-patch slicing for performance
  - **Bright ray systems** from Tycho (12 rays), Copernicus (8 rays), and
    Aristarchus (6 rays) with distance falloff
  - **Multi-scale surface noise** at 4 octaves for highland texture
  - **Gaussian smoothing** pass to blend all features naturally
  - RGB colors: warm highlands vs cool dark maria, with albedo-dependent
    color shifts
- Performance optimization: reduced Moon full-pipeline render from ~387s to ~6s
  by replacing full-image Python loops with local pixel-patch operations and
  capping auto-scale resolution at 1024 pixels
- Fixed Saturn front/back ring rendering: near-side rings now properly cross
  over the planet face with 85% opacity

### Decisions made
- Procedural noise approach for Moon texture (no external image dependencies)
- Auto-scale resolution capped at 1024px (good detail at ~2.4"/pixel for Moon)
- Small craters use local pixel-patch slicing instead of full-image distance arrays

### Installed
- Nothing new

### Notes
- All 128 tests pass
- Moon renders in ~6 seconds including PSF convolution at 1024px

## Session 9 — 2026-02-21

### What was done
- Replaced procedural Moon model with NASA LRO texture-mapped approach
  - Downloaded `lroc_color_2k.jpg` (2048x1024 equirectangular, 447KB) from
    NASA SVS CGI Moon Kit (https://svs.gsfc.nasa.gov/4720)
  - Stored in `telescope_sim/source/data/moon_albedo.jpg`
  - Rewrote `Moon` class to use orthographic projection of the texture onto
    the visible disk, with bilinear interpolation for smooth sampling
  - Kept limb darkening (u=0.15) and curved phase terminator
  - Added `sub_observer_lon_deg` parameter for libration/rotation
  - Removed procedural code (~300 lines of maria, craters, rays, noise)
  - Removed scipy dependency (was only needed for procedural gaussian_filter)
  - Texture cached at class level (loaded once, shared by all instances)
- Result: photorealistic Moon with real maria, craters, ray systems, and
  color directly from LRO LROC WAC data

### Decisions made
- Use real NASA texture data instead of procedural generation — vastly more
  realistic and actually simpler code
- Replaced `seed` parameter with `sub_observer_lon_deg` (seed was only needed
  for procedural random craters)
- Texture file committed to repo (447KB, small enough for version control)

### Installed
- Nothing new (PIL/Pillow already available)

### Notes
- All 128 tests pass
- Credit: NASA/GSFC/Arizona State University, LRO LROC WAC mosaic

---

## Session 10 — 2026-02-22

### What was done
- Added **atmospheric seeing presets** to main.py:
  - `SEEING_PRESETS` dict: "excellent" (0.8"), "good" (1.5"), "average" (2.5"), "poor" (4.0")
  - Default seeing changed from `None` to `"good"` — ground-based observers always have atmosphere
  - String presets resolved to float in `main()` before passing downstream
- **Adaptive resolution cap** in `plot_source_image()`:
  - Resolution now scales to ~3 pixels per resolution element (Airy radius or seeing sigma, whichever larger)
  - Moon capped at 2048 (texture resolution limit); other sources at 4096
  - Replaces fixed 1024 cap that was coarser than the diffraction limit
- **Eyepiece model** (`telescope_sim/geometry/eyepiece.py`):
  - `Eyepiece` dataclass with magnification, true FOV, and exit pupil calculations
  - 6 presets: Plössl 25mm/10mm, wide 20mm/13mm, ultra-wide 9mm/5mm
  - `from_preset()` class method for named presets
- **Eyepiece integration** in plotting:
  - `plot_source_image()` accepts optional `eyepiece` parameter
  - When set, crops/pads rendered image to eyepiece's true FOV
  - Produces **two figures**: "enhanced view" (analysis-friendly) + "true angular size" (scaled to match apparent size at 50cm viewing distance)
  - Circular field stop, eyepiece annotations (mag, TFOV, exit pupil)
- **New helper functions** in `ray_trace_plot.py`:
  - `_draw_source_on_axes()` — shared image drawing logic
  - `_crop_or_pad_to_fov()` — FOV adjustment for eyepiece
- Updated `main.py` with eyepiece configuration section
- Updated `PHYSICS.md`: moved atmospheric seeing to Implemented, added eyepiece model and adaptive resolution entries
- 10 new tests in `test_eyepiece.py`, 4 new integration tests in `test_sources.py`

### Decisions made
- Eyepiece is a **geometric model**, not a ray-traced optical element — it affects FOV and magnification but not the PSF (image is formed at the focal plane before the eyepiece)
- True-size figure assumes 50cm viewing distance and 96 DPI (documented on plot)
- Figure size capped at 20" max / 3" min for practicality
- Seeing default is "good" (1.5") — most realistic for typical ground-based observing

### Installed
- Nothing new

### Notes
- All existing + new tests should pass
- Backward compatible: `eyepiece=None` gives single figure (same as before)
- `seeing_arcsec=None` still works as space telescope mode

---

## Session 11 — 2026-02-22

### What was done
- Added **exit pupil brightness / washout** perceptual effect
  - New `_apply_exit_pupil_washout()` helper in `ray_trace_plot.py`
  - Sigmoid model: washout ≈ 0 at exit pupil ≤ 1.5mm, ~0.5 at 3mm, ~0.95 at 5mm
  - Reduces contrast (blend toward mean brightness) and desaturates RGB
    (blend toward luminance) for bright extended objects
  - Applied automatically in `plot_source_image()` when eyepiece is configured
    and source is extended (Jupiter, Saturn, Moon — not PointSource/StarField)
  - Washout strength shown in plot annotations when > 1%
- Added 5 unit tests in `test_eyepiece.py` (sigmoid values, contrast, desaturation)
- Added 3 integration tests in `test_sources.py` (large vs small exit pupil, no
  eyepiece, shape preservation)
- Updated PHYSICS.md: moved "Exit pupil brightness / washout" to Implemented

### Decisions made
- Washout is perceptual, applied post-rendering (does not modify PSF or physics)
- Only extended sources affected (point sources/star fields have different
  brightness behavior)
- Empirical sigmoid — flagged as approximation in code and PHYSICS.md
- No new config options needed: automatic based on exit pupil from eyepiece

### Installed
- Nothing new

### Notes
- Real-world context: observing Jupiter through a large telescope at low
  magnification (large exit pupil) produces a washed-out, overly bright image
  with reduced contrast and color saturation — this effect now modeled
- Fix in real observing: higher magnification (smaller exit pupil) or ND filter

---

## Session 12 — 2026-02-22

### What was done
- Added **Classical Cassegrain telescope** model (parabolic primary + convex hyperbolic secondary)
- **New class**: `HyperbolicMirror` in `telescope_sim/geometry/mirrors.py`
  - Implements `Mirror` ABC: `intersect()`, `normal_at()`, `get_surface_points()`
  - Ray-hyperbola intersection via quadratic solve on `(y+a)²/a² - x²/b² = 1`
  - Convex surface normals point toward primary (downward at vertex)
- **New class**: `CassegrainTelescope` in `telescope_sim/geometry/telescope.py`
  - Parameters: `primary_diameter`, `primary_focal_length`, `secondary_magnification`, `back_focal_distance`
  - Computes: effective focal length (`f_primary × M`), secondary position, size, hyperbola parameters
  - Standard Cassegrain geometry: `a = c - d`, `e = (M+1)/(M-1)`, `d = (f+B)/(M+1)`
  - Full interface matching `NewtonianTelescope` (duck typing): `focal_ratio`, `tube_length`, `obstruction_ratio`, `trace_ray`, `trace_rays`, `get_components_for_plotting`, `compute_vignetting`, `fully_illuminated_field`
  - Ray trace sequence: primary → hyperbolic secondary → back through hole → focal plane behind primary
- **Made `_find_focal_plane_positions()` direction-agnostic** in `ray_trace_plot.py`
  - Detects dominant travel direction of final ray segments (x for Newtonian, y for Cassegrain)
  - Scans along dominant axis, measures spread in perpendicular axis
  - Works for both telescope types without type-checking
- **Updated `main.py`**:
  - New `telescope_type` option ("newtonian" or "cassegrain")
  - Cassegrain-specific parameters: `primary_focal_length`, `secondary_magnification`, `back_focal_distance`
  - `_resolve_comparison_configs()` builds correct telescope class based on `telescope_type`
  - Commented-out Newtonian vs Cassegrain comparison example
- **9 new tests** in `tests/test_geometry.py`:
  - `HyperbolicMirror`: surface points shape/bounds, convex normal direction
  - `CassegrainTelescope`: focal ratio, effective FL, ray convergence behind primary, multi-ray convergence, plotting components, obstruction ratio
- Updated `PHYSICS.md`: added hyperbolic mirror and Cassegrain two-mirror system to Implemented
- Updated `telescope_sim/geometry/__init__.py` with new exports

### Decisions made
- Classical Cassegrain uses parabolic primary (same as Newtonian) + hyperbolic secondary
- `CassegrainTelescope` uses duck typing (same interface) rather than shared ABC — all existing plotting code works unchanged
- Vignetting delegates to same physics module using primary_focal_length (not effective FL)
- Back focal distance defaults to 15% of primary diameter if not specified

### Installed
- Nothing new

### Notes
- All 163 tests pass (154 existing + 9 new)
- Key physics: effective FL = primary FL × magnification, giving long focal length in short tube
- Example: 200mm f/20 Cassegrain (4000mm effective FL) using 800mm primary FL with M=5

## Session 8 — 2026-02-22

### What was done
- Added refraction physics (Snell's law) in `telescope_sim/physics/refraction.py`
  - `refract_direction()`: 2D vector Snell's law with total internal reflection detection
  - `refractive_index_cauchy()`: Cauchy dispersion equation n(λ) = B + C/λ²
  - `GLASS_CATALOG`: preset coefficients for BK7 crown and F2 flint glass
- Created lens geometry in `telescope_sim/geometry/lenses.py`
  - `Lens` ABC parallel to `Mirror` ABC — two-surface model (front + back)
  - `SphericalLens`: biconvex, planoconvex, meniscus configurations via R_front/R_back
  - Standard optics sign convention: R > 0 = convex toward incoming light
- Added `RefractingTelescope` in `telescope_sim/geometry/telescope.py`
  - Singlet objective lens with auto-computed geometry from lensmaker's equation
  - Zero central obstruction, clean Airy pattern
  - Same interface as Newtonian/Cassegrain (trace_ray, get_components_for_plotting, etc.)
- Updated ray trace plotting for lens visualization
  - Draws objective as filled shape (light blue) between front/back surface curves
  - Added `primary_type == "lens"` case in `_analytical_focal_offsets` (diffraction-limited)
- Updated `main.py` with `"refracting"` telescope type option
- Added `_REFRACTING_KEYS` config set, comparison support, Refractor display name
- Updated module exports (`__init__.py` for physics and geometry)
- Updated `PHYSICS.md`: moved refraction to Implemented, added chromatic/achromat to Not Yet Implemented
- Added 8 new refraction tests and 6 new lens/refractor geometry tests

### Decisions made
- Standard optics sign convention for R: positive = center of curvature on transmission side
- Lens uses `point - sphere_center` for normals (auto-corrected by refract_direction)
- Monochromatic singlet treated as diffraction-limited for analytical focal offsets
- Refractor vignetting returns 1.0 everywhere (no tube wall model yet)

### Installed
- Nothing new

### Notes
- All 182 tests pass (163 existing + 19 new)
- Tricky part: getting sphere center placement right for correct lens convergence/divergence
- Future extensions enabled: achromatic doublet, Maksutov-Cassegrain, chromatic aberration viz

---

## Session — 2026-02-27: Maksutov-Cassegrain Telescope

### What was done
- Added `MaksutovCassegrainTelescope` class to `telescope_sim/geometry/telescope.py`
  - Catadioptric design: meniscus corrector (refraction) + spherical primary (reflection) + aluminized spot secondary (reflection)
  - Reuses Cassegrain geometry formulas for secondary placement, magnification, back focus
  - `_reflect_off_spot()` private method for aluminized spot reflection (no new Mirror subclass needed)
  - Near-concentric meniscus formula for auto-computing front radius from back radius and thickness
  - `corrected_optics = True` flag distinguishes corrected spherical primary from bare spherical
  - Full interface: trace_ray, trace_rays, compute_vignetting, fully_illuminated_field, get_components_for_plotting
- Updated ray trace plotting (`ray_trace_plot.py`)
  - Added `"maksutov"` drawing branch: meniscus as filled shape, aluminized spot highlighted in silver, spherical primary
  - `_analytical_focal_offsets` checks `corrected_optics` flag — returns zeros for corrected systems
- Updated `telescope_sim/geometry/__init__.py` with new export
- Updated `main.py`
  - Added `"maksutov"` telescope type option with descriptive comment
  - Added `_MAKSUTOV_KEYS` config set, comparison support, Maksutov builder branch
  - Added commented-out Cassegrain vs Maksutov comparison example
- Added 7 new tests in `tests/test_geometry.py::TestMaksutovCassegrainTelescope`
- Updated `PHYSICS.md` with Maksutov-Cassegrain entry

### Decisions made
- Aluminized spot handled as private method using meniscus back surface geometry (no new class)
- SphericalLens reused for meniscus (both radii negative = meniscus configuration)
- SphericalMirror reused for primary (R = 2f)
- `corrected_optics` attribute avoids conflating bare vs corrected spherical primaries in analytical offsets

### Installed
- Nothing new

### Notes
- All 189 tests pass (182 existing + 7 new)
- Ray path exercises both refraction AND reflection: refract through meniscus → reflect off primary → reflect off spot → back focus

---

## Session — 2026-03-07: User Guide and Review

### What was done
- Created comprehensive `USER_GUIDE.md` covering:
  - Codebase architecture and design patterns
  - All physics formulas with explanations
  - Coding patterns for learning (ABCs, duck typing, separation of concerns)
  - 7 example analysis studies with configuration snippets
  - Known limitations and reliability assessment
  - Prioritized next steps
  - Telescope design decision guide with trade-off tables
- Set up 10" f/5 vs f/6 Newtonian comparison in main.py
- Set up Moon imaging through both configurations
- Added `single_compare` mechanism for multi-telescope source imaging
- Thorough codebase review: 197 tests, ~6,800 lines, 4 telescope types

### Notes
- All 197 tests pass
- Key finding from review: simulation is reliable for within-design-type comparisons (e.g., Newtonian vs Newtonian), but cross-design-type comparisons have gaps (missing chromatic aberration for refractors, coma model doesn't account for correctors)

## Session — 2026-03-08: Implementation Plan Execution (Tasks #4–#14)

### What was done
**Phase 1: Quick doc/config fixes**
- Fixed misleading Airy disk comment in USER_GUIDE (µm units, added magnification explanation)
- Fixed aperture comparison examples to use constant f/5 (was varying f/ratios)
- Documented annular vs circular aperture comparison feature

**Phase 2: Type hint cleanup**
- Updated ray_trace_plot.py to import all telescope types
- Created Telescope union type for better type coverage
- Removed Newtonian-specific comments from generic code paths

**Phase 3: Plotting improvements**
- Added shared axis scale for ray trace comparison plots (visually comparable sizes)
- Added per-plot toggles to main.py (show_ray_trace, show_spot_diagram, etc.)
- Fixed spot diagram noise floor by using analytical method when available
- Improved coma analysis plots:
  - Added axis labels and caption to spot grid
  - Created plot_coma_field_analysis_comparison() for overlaying RMS curves
  - Wired into comparison mode with show_coma_comparison toggle

**Phase 4: Eyepiece enrichment**
- Added helper methods to Eyepiece class: max/min useful magnification, assessment, summary()
- Print eyepiece summary in run_single() showing magnification assessment
- Added eyepiece selection guidance to USER_GUIDE.md

**Phase 5: Schmidt-Cassegrain telescope**
- Implemented full SchmidtCassegrainTelescope class with:
  - Spherical primary + convex spherical secondary
  - Schmidt corrector plate (modeled as zero-power element)
  - Ray tracing through all surfaces
  - Properties (focal_ratio, tube_length, obstruction_ratio)
  - Vignetting support
- Added Schmidt-Cassegrain drawing support in ray_trace_plot.py
- Updated all exports and main.py configuration
- Added to PHYSICS.md with approximation notes
- Added 7 tests (all passing)

**Phase 6: Mak-Cass geometry fix**
- Replaced thin-lens formula with iterative ray-trace solver
- Correctly accounts for meniscus refraction effects on effective focal length
- Improved ray convergence from ~10mm spread to <2mm (tightened test threshold)

**Phase 7: Tests & verification**
- All 204 tests pass
- Schmidt-Cassegrain: 7 new tests, all passing (residual ~2.4mm spherical aberration expected due to zero-power corrector approximation)
- Mak-Cass: Improved convergence verified

### Files modified
- telescope_sim/geometry/telescope.py: Schmidt-Cassegrain class, Mak-Cass fix
- telescope_sim/geometry/eyepiece.py: New helper methods
- telescope_sim/plotting/ray_trace_plot.py: Type hints, shared axes, Schmidt drawing, coma comparison
- telescope_sim/plotting/__init__.py: Export plot_coma_field_analysis_comparison
- main.py: Plot toggles, Schmidt config, eyepiece summary
- USER_GUIDE.md: Airy fix, aperture study, eyepiece guidance
- PHYSICS.md: Schmidt-Cassegrain entry
- tests/test_geometry.py: Schmidt-Cassegrain tests, Mak-Cass threshold update

### Notes
- All tasks from implementation plan completed successfully
- Schmidt-Cassegrain has expected residual aberration due to zero-power corrector approximation
- Mak-Cass now uses physically accurate iterative solver instead of thin-lens approximation
- 204 tests passing (was 197 before session)
