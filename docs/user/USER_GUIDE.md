# Telescope Simulation Project — User Guide

A comprehensive guide to the codebase architecture, underlying physics,
how to run analyses, coding patterns used, and how to apply the simulation
to real telescope design decisions.

**Last updated**: March 2026 | **Tests**: 215 passing | **Code**: ~7,200 lines

> **Getting Started**: See [README.md](../../README.md) for installation and quick start. Always activate the virtual environment before working: `source venv/bin/activate`. Run `deactivate` when done.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [How to Run](#2-how-to-run)
3. [Codebase Architecture](#3-codebase-architecture)
4. [Physics Reference](#4-physics-reference)
5. [Coding Patterns and Practices](#5-coding-patterns-and-practices)
6. [How to Use for Analyses](#6-how-to-use-for-analyses)
7. [Known Limitations](#7-known-limitations)
8. [Next Steps](#8-next-steps)
9. [Using This for Telescope Design Decisions](#9-using-this-for-telescope-design-decisions)


---

## 1. Project Overview

This is a 2D telescope simulation that models light propagation through
realistic optical systems. It traces rays through mirrors and lenses,
computes diffraction patterns, and produces simulated images of
astronomical objects (Moon, Jupiter, Saturn, star fields).

### What it can do

- **Ray trace** through 4 telescope designs: Newtonian, Cassegrain,
  Refractor, Maksutov-Cassegrain
- **Visualize** the optical path (rays bouncing off mirrors, refracting
  through lenses)
- **Compute diffraction** (Airy pattern, central obstruction effects,
  spider vane diffraction spikes)
- **Model aberrations** (spherical aberration from ray tracing, Seidel
  coma analytically)
- **Simulate images** of the Moon, Jupiter, Saturn, and star fields as
  seen through a defined telescope + eyepiece
- **Compare configurations** side-by-side (different f/ratios, apertures,
  mirror types, telescope designs)

### File tree

```
telescopeSimulationProject/
├── README.md                        Project overview and quick start
├── CLAUDE.md                        Coding instructions for AI assistance
├── main.py                          Entry point — all user configuration here
├── requirements.txt                 Dependencies (numpy, matplotlib, scipy, pytest)
│
├── docs/                            Documentation
│   ├── user/
│   │   └── USER_GUIDE.md            This file
│   ├── technical/
│   │   ├── PHYSICS.md               Physics implementation inventory
│   │   └── FORMULAS.md              Math formulas reference
│   └── development/
│       ├── ROADMAP.md               Development priorities and planned features
│       └── devlog.md                Development history log
│
├── telescope_sim/                   Main package (~6,000 lines)
│   ├── geometry/                    Optical components and telescope assembly
│   │   ├── telescope.py             4 telescope classes (890 lines)
│   │   ├── mirrors.py              Mirror types: parabolic, spherical, hyperbolic, flat (418 lines)
│   │   ├── lenses.py               Spherical lens with two surfaces (288 lines)
│   │   └── eyepiece.py             Visual observing model (81 lines)
│   │
│   ├── physics/                     Optical physics implementations
│   │   ├── ray.py                   Ray dataclass with history tracking (41 lines)
│   │   ├── reflection.py            Law of reflection (29 lines)
│   │   ├── refraction.py            Snell's law + Cauchy dispersion (74 lines)
│   │   ├── diffraction.py           Airy PSF for circular/annular apertures (52 lines)
│   │   ├── fft_psf.py              FFT-based PSF with spider vanes (123 lines)
│   │   ├── aberrations.py           Seidel 3rd-order coma (139 lines)
│   │   └── vignetting.py            Off-axis illumination model (139 lines)
│   │
│   ├── source/                      Astronomical sources
│   │   ├── light_source.py          Parallel ray generation (56 lines)
│   │   └── sources.py               Jupiter, Saturn, Moon, stars (693 lines)
│   │
│   └── plotting/                    All visualization
│       └── ray_trace_plot.py        40+ plotting functions (2,875 lines)
│
└── tests/                           215 tests across 10 files
    ├── test_geometry.py             Mirrors, lenses, all 4 telescope types
    ├── test_physics.py              Ray class, reflection
    ├── test_refraction.py           Snell's law, dispersion, TIR
    ├── test_aberrations.py          Coma formulas
    ├── test_vignetting.py           Illumination model
    ├── test_eyepiece.py             Magnification, exit pupil, FOV
    ├── test_fft_psf.py              Pupil mask, FFT validation
    ├── test_sources.py              Source rendering, washout model
    └── test_source.py               Parallel ray generation
```


---

## 2. How to Run

### Setup
```bash
cd ~/Work/telescopeSimulationProject
source venv/bin/activate
pip install -r requirements.txt   # first time only
```

### Run the simulation
```bash
python main.py
```
This opens matplotlib windows with ray traces, spot diagrams, PSF
profiles, and simulated images based on the configuration in `main.py`.

### Run tests
```bash
python -m pytest tests/ -v
```

### Configuration

All user-facing options are in `main.py`. The file is organized into
labeled sections with commented-out alternatives you can toggle:

| Section | Key variables | What it controls |
|---------|---------------|------------------|
| Telescope type | `telescope_type` | `"newtonian"`, `"cassegrain"`, `"refracting"`, `"maksutov"` |
| Geometry | `primary_diameter`, `focal_length` | Aperture and focal length in mm |
| Mirror type | `primary_type` | `"parabolic"` or `"spherical"` (Newtonian only) |
| Cassegrain | `primary_focal_length`, `secondary_magnification` | Primary FL and magnification factor |
| Maksutov | `meniscus_thickness` | Corrector lens thickness |
| Spider vanes | `spider_vanes`, `spider_vane_width` | 0/3/4/6 vanes, width in mm |
| Display | `num_display_rays` | Ray count for visualization (11, 21, 51) |
| Wavelength | `wavelength_nm` | 450 (blue), 550 (green), 650 (red) |
| Method | `method` | `"analytical"` (fast) or `"traced"` (validates simulation) |
| Seeing | `seeing_arcsec` | `"excellent"` / `"good"` / `"average"` / `"poor"` / float / None |
| Obstruction | `include_obstruction` | Toggle secondary mirror in PSF |
| Source | `source_type` | `"moon"`, `"jupiter"`, `"saturn"`, `"star"`, `"star_field"`, None |
| Eyepiece | `eyepiece_focal_length_mm` | Eyepiece FL (None = raw focal plane) |
| Coma | `field_angle_arcsec`, `show_coma_analysis` | Off-axis aberration analysis |
| Vignetting | `show_vignetting` | Illumination vs field angle plot |
| Comparison | `compare_mode`, `comparison_configs` | Side-by-side comparison |

### Modes of operation

**Single telescope mode** (`compare_mode = False`):
Produces for the configured telescope:
1. Ray trace diagram (2D side view)
2. Spot diagram at focal plane
3. Focal image (geometric + diffraction)
4. PSF profile (1D, linear + log scale, with Strehl ratio)
5. 2D PSF (if spider vanes > 0)
6. Vignetting curve (if `show_vignetting = True`)
7. Coma analysis (if `show_coma_analysis = True`)
8. Source image (if `source_type` is set)
9. Eyepiece view (if eyepiece configured, with source)

**Comparison mode** (`compare_mode = True`):
Produces side-by-side panels for each config in `comparison_configs`:
1. Ray trace comparison
2. Spot diagram comparison
3. Focal image comparison
4. PSF profile comparison (overlaid)
5. 2D PSF comparison (if any has spider vanes)
6. Vignetting comparison (if `show_vignetting = True`)

**Multi-telescope single mode** (`single_compare` list in main.py):
Runs single-mode plots for each telescope sequentially. Useful for
comparing source images (Moon, Jupiter) across designs, which
comparison mode doesn't support.


---

## 3. Codebase Architecture

### Design philosophy

The code follows a layered architecture where each layer has a single
responsibility:

```
main.py (configuration + orchestration)
    │
    ├── telescope_sim.geometry (what the telescope looks like)
    │   ├── mirrors / lenses (individual optical elements)
    │   └── telescope (assembled optical systems)
    │
    ├── telescope_sim.physics (how light behaves)
    │   ├── ray, reflection, refraction (geometric optics)
    │   ├── diffraction, fft_psf (wave optics)
    │   ├── aberrations (Seidel theory)
    │   └── vignetting (illumination geometry)
    │
    ├── telescope_sim.source (what we're looking at)
    │   ├── light_source (ray generation)
    │   └── sources (astronomical objects)
    │
    └── telescope_sim.plotting (visualization)
        └── ray_trace_plot (all plots)
```

### Key abstractions

**Mirror (ABC)** — All mirror types implement three methods:
- `intersect(ray)` — where does the ray hit? (returns parameter t)
- `normal_at(point)` — what's the surface normal? (for reflection)
- `get_surface_points()` — how to draw it? (for plotting)

The base class provides `reflect_ray(ray)` which calls these three
in sequence. Adding a new mirror type means implementing just those
three methods — reflection logic is inherited.

**Lens (ABC)** — Same pattern but with front/back surfaces:
- `front_intersect` / `back_intersect`
- `front_normal_at` / `back_normal_at`
- `get_front_surface_points` / `get_back_surface_points`

The base class provides `refract_ray(ray)` which refracts through
both surfaces (air→glass at front, glass→air at back).

**Telescope classes** — All four types share the same public interface:
- `trace_ray(ray)` / `trace_rays(rays)` — propagate light
- `focal_ratio`, `tube_length`, `obstruction_ratio` — properties
- `compute_vignetting()` / `fully_illuminated_field()` — off-axis
- `get_components_for_plotting()` — dict for the plotting layer

This means plotting code works with any telescope type without
knowing which one it is — it just reads the components dict.

**Ray** — A simple dataclass holding:
- `origin` (current position)
- `direction` (unit vector)
- `history` (list of all positions visited)

Rays are modified in place as they propagate. The history list
is what gets drawn in ray trace plots.

### Data flow for a simulation run

```
1. main.py creates a telescope (e.g., NewtonianTelescope)
2. create_parallel_rays() generates rays at the aperture
3. telescope.trace_rays(rays) propagates each ray:
   a. Ray hits primary → reflect_ray computes new direction
   b. Ray hits secondary → reflect_ray again (or refract for Mak)
   c. Ray propagates to focal plane
4. telescope.get_components_for_plotting() returns mirror geometry
5. plot_ray_trace() draws mirrors + ray histories
6. plot_focal_image() computes PSF and convolves with geometric spot
7. plot_source_image() renders source through the telescope optics
```

### How each telescope type traces rays

| Telescope | Step 1 | Step 2 | Step 3 | Step 4 |
|-----------|--------|--------|--------|--------|
| **Newtonian** | Reflect off primary (parabolic/spherical) | Reflect off flat diagonal (45deg) | Propagate to side focus | — |
| **Cassegrain** | Reflect off parabolic primary | Reflect off hyperbolic secondary | Propagate down through primary hole | Arrive at back focus |
| **Refractor** | Refract through front surface (air→glass) | Refract through back surface (glass→air) | Propagate to front focus | — |
| **Mak-Cass** | Refract through meniscus (2 surfaces) | Reflect off spherical primary | Reflect off aluminized spot | Propagate through primary hole to back focus |


---

## 4. Physics Reference

### Geometric optics — what's exact

**Law of reflection** (`reflection.py`):
```
d_reflected = d - 2(d . n)n
```
This is exact. The surface normal `n` is auto-oriented toward the
incoming ray, so it works regardless of which side light comes from.

**Snell's law** (`refraction.py`):
```
n1 sin(theta1) = n2 sin(theta2)
```
Implemented in 2D vector form. Returns `None` for total internal
reflection (when `sin(theta2) > 1`). Exact.

**Ray-surface intersections** (`mirrors.py`, `lenses.py`):
Each mirror/lens type solves the exact intersection equation
(ray-parabola, ray-circle, ray-hyperbola) via quadratic formula.
No approximations — the geometry is exact for the defined surface
shapes.

### Wave optics — Airy diffraction (`diffraction.py`)

**Circular aperture (no obstruction)**:
```
PSF(r) = [2 J1(x) / x]^2,   x = pi * D * r / (lambda * f)
```
The Airy pattern is the fundamental resolution limit. The first
dark ring (Airy radius) is at:
```
r_airy = 1.22 * lambda * f / D
```

**Annular aperture (with obstruction)**:
```
PSF(r) = [1/(1-eps^2)]^2 * [2*J1(x)/x - eps^2 * 2*J1(eps*x)/(eps*x)]^2
```
where `eps = D_secondary / D_primary`. The obstruction transfers
energy from the central peak to the diffraction rings, reducing
contrast on planets and the Moon.

**Spider vane diffraction** (`fft_psf.py`):
When spider vanes are present, the analytical Airy formula can't
capture the spike pattern. Instead, a 2D pupil mask is built
(circular aperture minus obstruction minus vane lines) and the PSF
is computed via:
```
PSF = |FFT(pupil)|^2
```
Each vane produces a pair of diffraction spikes perpendicular to
the vane direction. 4 vanes → 4 spikes, 3 vanes → 6 spikes.

### Aberrations

**Spherical aberration** — emerges naturally from ray tracing through
a `SphericalMirror`. No separate formula is needed — the mirror's
surface equation `x^2 + (y-R)^2 = R^2` causes edge rays to focus
short of the paraxial focus. The 3rd-order approximation is:
```
epsilon(h) = -h^3 / (8 f^2)
```
A parabolic mirror has zero spherical aberration by definition.

**Coma** (`aberrations.py`) — modeled analytically using Seidel
3rd-order theory for a parabolic Newtonian primary:
```
C_sagittal(h) = theta * h^2 / (4f)
x = C_s * (2 + cos(2*phi))     [tangential]
y = C_s * sin(2*phi)           [sagittal]
```
Produces the characteristic comet-shaped pattern for off-axis sources.
The coma-free field (where coma < Airy disk) scales as f^2/D^3.

### Dispersion model (`refraction.py`)

```
n(lambda) = B + C / lambda^2     (Cauchy model)
```
Glass catalog:
- **BK7** (borosilicate crown): B=1.5046, C=4200 — low dispersion
- **F2** (dense flint): B=1.6032, C=9500 — high dispersion

Blue light (450nm) refracts more than red (650nm), causing chromatic
aberration in lenses.

### Chromatic aberration

Enable `polychromatic = True` in main.py to activate multi-wavelength
imaging for refractors.  Each RGB channel is convolved with a PSF at
its own wavelength (R=656nm, G=550nm, B=486nm), including
wavelength-dependent defocus.

**Singlet refractor** — large chromatic defocus produces visible
purple/green fringing on high-contrast edges (e.g., Jupiter's limb).

**Achromatic doublet** (`objective_type = "achromat"`) — BK7 crown +
F2 flint cemented doublet cancels primary chromatic aberration.
Residual secondary spectrum is ~f/2500.

**Reflectors** — zero chromatic aberration (mirrors are achromatic).
The `polychromatic` flag has no effect on reflectors.

**Polychromatic ray trace** — `plot_polychromatic_ray_trace()` draws
R/G/B colored rays through the telescope, showing how different
wavelengths focus at different points for singlets.

### Vignetting (`vignetting.py`)

Off-axis light shifts the beam laterally at the secondary mirror
plane. The illumination fraction is the overlap area between the
shifted beam circle and the secondary mirror circle:
```
beam_diameter = D_primary * (1 - secondary_offset / f)
beam_shift = theta * secondary_offset
illumination = circle_overlap(beam_radius, secondary_radius, shift)
```
Tube wall vignetting is not modeled.

### Atmospheric seeing

Atmospheric turbulence causes stars to appear as blurred disks rather
than point sources. The `seeing_arcsec` parameter is the **full width
at half maximum (FWHM)** of this seeing disk — the angular diameter
at which the brightness drops to 50% of the peak.

**What FWHM means**: For a star with 1.5" seeing, the disk measures
1.5" across at half-brightness. Smaller FWHM = sharper images.

Applied as Gaussian blur:
- Excellent: 0.8" FWHM (rare, high-altitude observatories)
- Good: 1.5" FWHM (good amateur site on a calm night)
- Average: 2.5" FWHM (typical suburban/rural)
- Poor: 4.0" FWHM (turbulent, near horizon, or humid)
- None: space telescope (no atmosphere)

The Gaussian formula: blur σ = FWHM / 2.355, applied as a 2D kernel
`exp(-(x²+y²)/(2σ²))`.

**Approximation**: Real seeing follows a Moffat/Kolmogorov profile
with broader wings than Gaussian. The Gaussian model overestimates
contrast transfer at moderate spatial frequencies.

### Image formation pipeline

The simulated image is built in layers:
1. **Source rendering** — ideal image of the object (Moon texture,
   Jupiter bands, etc.)
2. **PSF convolution** — blur by the telescope's diffraction pattern
   (includes obstruction effects)
3. **Seeing convolution** — additional Gaussian blur (if atmosphere on)
4. **Eyepiece cropping** — crop to true field of view
5. **Exit pupil washout** — reduce contrast/saturation if exit pupil
   is large (empirical sigmoid model)

### Strehl ratio (approximation)

```
Strehl ~ 1 / (1 + (pi * sigma / (2 * r_airy))^2)
```
where `sigma` = RMS geometric spot radius. This is a convenient
approximation, not a true wavefront-based Strehl. Values:
- 1.0 = perfect (diffraction-limited)
- &gt;0.8 = conventionally "diffraction-limited" (Marechal criterion)
- &lt;&lt;1 = significant aberration


---

## 5. Coding Patterns and Practices

### Patterns worth studying

**Abstract base classes** (`mirrors.py:Mirror`, `lenses.py:Lens`):
The ABC pattern ensures every new optical element implements the
required interface. The base class provides shared behavior
(`reflect_ray`, `refract_ray`) that works through the abstract
methods. This is the Template Method pattern — the algorithm
skeleton lives in the base class, subclasses fill in the specifics.

**Why it matters**: Adding a new mirror type (e.g., elliptical for
Ritchey-Chretien) only requires implementing `intersect()`,
`normal_at()`, and `get_surface_points()`. All reflection logic,
ray tracing, and plotting work automatically.

**Duck typing for telescopes**:
The four telescope classes don't share a base class, but they all
implement the same interface (same method names, same return types).
The plotting code works with any telescope by calling common methods
like `get_components_for_plotting()`. This is "duck typing" — if it
walks like a telescope and quacks like a telescope, it's a telescope.

**Convention**: Python uses this widely. A formal Protocol or ABC
could enforce it, but the current approach is simpler and idiomatic.

**Separation of concerns**:
- `geometry/` knows shapes, not physics
- `physics/` knows equations, not telescopes
- `telescope.py` assembles components, delegating to both
- `plotting/` only reads data, never modifies optical state

**Example**: `reflect_direction()` in `physics/reflection.py` is a
pure function — it takes vectors, returns a vector. It doesn't know
about mirrors. `Mirror.reflect_ray()` in `geometry/mirrors.py` calls
it after computing the intersection and normal. This separation means
reflection physics can be tested independently of mirror geometry.

**Configuration through comments** (`main.py`):
The entry point exposes every option with descriptive comments and
commented-out alternatives. Users discover features by reading the
config section — no documentation hunting required. This is a
deliberate UX choice for a simulation tool.

### Style conventions (PEP 8)

- `snake_case` for functions, methods, variables
- `PascalCase` for classes
- `UPPER_SNAKE_CASE` for constants
- Private methods prefixed with `_` (e.g., `_reflect_off_spot`)
- Type hints on public interfaces (`float | None`, `list[Ray]`)

### Testing patterns

Tests are organized by module with `setup_method()` creating
standard test fixtures:

```python
class TestParabolicMirror:
    def setup_method(self):
        self.mirror = ParabolicMirror(focal_length=1000.0, diameter=200.0)

    def test_parallel_rays_converge_to_focal_point(self):
        # Tests the defining property of a paraboloid
        ...
```

Tests verify **physical properties** ("parallel rays converge to
one point") not implementation details ("quadratic formula returns
correct t"). This makes tests resilient to refactoring.


---

## 6. How to Use for Analyses

### Study 1: Focal ratio impact (f/5 vs f/6 vs f/8)

Set `compare_mode = True` and configure:
```python
comparison_configs = [
    {"label": "f/5 (1270mm)", "focal_length": 1270.0},
    {"label": "f/6 (1524mm)", "focal_length": 1524.0},
    {"label": "f/8 (2032mm)", "focal_length": 2032.0},
]
```
The PSF comparison shows how the Airy disk scales with f/ratio.
The spot diagram shows identical spots (all parabolic = perfect).
The focal image shows the visual impact of different plate scales.

### Study 2: Spherical vs parabolic mirror

```python
comparison_configs = [
    {"label": "Parabolic", "primary_type": "parabolic"},
    {"label": "Spherical", "primary_type": "spherical"},
]
```
The spot diagram reveals the spherical aberration directly.
The PSF comparison quantifies the Strehl ratio difference.
This answers: "at my chosen f/ratio, can I get away with a
spherical mirror?"

**Rule of thumb**: Spherical mirrors are acceptable when the
aberration is smaller than the Airy disk. This happens at long
f/ratios (roughly f/10+ for typical apertures).

### Study 3: Annular vs Circular Aperture (Obstruction Effects)

Compare the PSF with and without central obstruction to see its effect on
diffraction. Toggle `include_obstruction` in comparison mode:

```python
comparison_configs = [
    {"label": "With Obstruction", "include_obstruction": True},
    {"label": "No Obstruction", "include_obstruction": False},
]
```

The obstruction strengthens secondary diffraction rings and reduces peak
intensity (Strehl ratio), lowering contrast on planets and the Moon.
A 20% obstruction ratio (typical Newtonian) is noticeable; 30%+ (some
Cassegrains) is significant. Refractors have zero obstruction.

### Study 4: Aperture comparison

```python
comparison_configs = [
    {"label": "6\" (150mm)", "primary_diameter": 150.0, "focal_length": 750.0},
    {"label": "8\" (200mm)", "primary_diameter": 200.0, "focal_length": 1000.0},
    {"label": "10\" (254mm)", "primary_diameter": 254.0, "focal_length": 1270.0},
]
```
Shows the resolution improvement (smaller Airy disk) with larger
aperture, all at f/5.

### Study 5: Telescope design comparison

```python
comparison_configs = [
    {"label": "Newtonian f/5", "telescope_type": "newtonian",
     "focal_length": 1270.0, "primary_type": "parabolic"},
    {"label": "Cassegrain f/20", "telescope_type": "cassegrain",
     "primary_focal_length": 1016.0, "secondary_magnification": 5.0},
]
```
Compares ray paths, tube lengths, and obstruction ratios.

### Study 6: Planet/Moon imaging

Set `compare_mode = False`, configure source and eyepiece:
```python
source_type = "jupiter"              # or "moon", "saturn"
eyepiece_focal_length_mm = 5.0      # high magnification
seeing_arcsec = "good"
```
The source image shows what Jupiter/Moon actually looks like through
your telescope at that magnification and seeing conditions. The
eyepiece view shows the true angular size as it would appear to
your eye.

### Study 7: Spider vane diffraction spikes

```python
comparison_configs = [
    {"label": "No vanes", "spider_vanes": 0, "primary_type": "parabolic"},
    {"label": "4 vanes", "spider_vanes": 4, "primary_type": "parabolic"},
]
```
The 2D PSF comparison (log scale) shows the diffraction spike
pattern. The 1D PSF comparison shows the energy redistribution.

### Study 8: Eyepiece Selection Guidance

Key relationships:
- **Magnification** = telescope focal length / eyepiece focal length
- **Exit pupil** = aperture / magnification (should be 0.5–7 mm)
- **True FOV** = apparent FOV / magnification

Rules of thumb:
- **Maximum useful magnification** ≈ 2× aperture in mm (e.g., 500× for 250mm)
- **Minimum useful magnification** ≈ aperture / 7 (exit pupil = 7mm, eye limit)
- **Planetary viewing**: 1–2mm exit pupil (high mag, best contrast)
- **Deep sky**: 3–5mm exit pupil (wide field, bright image)
- **Exit pupil > 5mm**: Light wasted (larger than dark-adapted pupil)

The simulation prints a magnification assessment ("good", "high", "too high", etc.)
when an eyepiece is configured.


---

## 7. Known Limitations

### What's reliable for design decisions

| Analysis | Reliable? | Notes |
|----------|-----------|-------|
| Diffraction limit (Airy disk vs aperture) | Yes | Exact physics |
| Spherical aberration severity vs f/ratio | Yes | Ray-traced from real geometry |
| Central obstruction impact on PSF | Yes | Exact annular aperture formula |
| Tube length comparisons | Yes | Direct from geometry |
| Magnification / exit pupil / FOV | Yes | Exact formulas |
| Spider vane diffraction spikes | Yes | FFT from pupil geometry |
| Coma field for Newtonian | Yes | Seidel 3rd-order (valid for small angles) |

### What's approximate or missing

| Feature | Status | Impact |
|---------|--------|--------|
| Chromatic aberration (refractors) | **Implemented** | Enable `polychromatic = True` to see color fringing |
| Achromatic doublet | **Implemented** | Set `objective_type = "achromat"` for crown+flint doublet |
| Coma for corrected systems (Cassegrain, Mak) | **Overestimated** | Uses Newtonian formula; these designs have less coma |
| Field curvature, astigmatism | Not implemented | Only coma among off-axis aberrations |
| Surface errors (manufacturing) | Not implemented | Assumes perfect optics |
| Atmospheric seeing profile | **Gaussian approx** | Real profile has broader wings (Moffat) |
| Eyepiece aberrations | Not modeled | Eyepiece is geometric only (magnification/FOV) |
| Tube wall vignetting | Not modeled | Reflectors may vignette at tube edges |
| 3D ray tracing | Not implemented | All tracing is 2D cross-sectional |
| Exit pupil washout | Empirical | Sigmoid model not psychophysically calibrated |

### Cross-design comparison caveats

When comparing **across** design types (Newtonian vs Refractor vs
Mak-Cass), be aware:
- For **refractors**, enable `polychromatic = True` to see realistic
  chromatic aberration.  Without it, singlet refractors appear
  unrealistically sharp.  Use `objective_type = "achromat"` to see
  how a doublet corrects this.
- **Coma comparisons** between Newtonian and Mak-Cass/Cassegrain
  are not yet meaningful — the coma model doesn't account for the
  secondary's coma correction
- **Within** a single design type (e.g., comparing two Newtonians),
  all comparisons are valid


---

## 8. Next Steps

### High priority (enables honest cross-design comparison)

1. ~~**Chromatic aberration for refractors**~~ — **Done.** Set
   `polychromatic = True` in main.py. Multi-wavelength (R/G/B)
   PSFs produce color fringing on singlet refractors.

2. **Design-aware coma model** — The classical Cassegrain's hyperbolic
   secondary doesn't correct coma (same as Newtonian). But the
   Maksutov's meniscus reduces it. Adding a per-design coma
   correction factor would make off-axis field comparisons valid.

### Medium priority (useful refinements)

3. **Physical summary output** — A text/table summary comparing
   designs: tube length, back focus distance, obstruction ratio,
   Airy disk size, coma-free field, weight estimate. Directly
   useful for purchase decisions.

4. ~~**Achromatic doublet**~~ — **Done.** Set
   `objective_type = "achromat"` for a BK7+F2 cemented doublet.
   Comparison presets in main.py for singlet vs achromat.

5. **Type hint cleanup** — Plotting functions are annotated as
   `telescope: NewtonianTelescope` but actually accept any type.
   A Protocol class would make this correct.

### Lower priority (cool enhancements)

6. **Moffat/Kolmogorov seeing** — More realistic atmospheric model
   with broader wings.
7. **Surface error modeling** — Wavefront error from manufacturing
   tolerances (Zernike polynomials).
8. **Ritchey-Chretien** — Elliptical mirror for coma-free Cassegrain
   variant (requires new EllipticalMirror class).
9. **Deep-sky objects** — Nebulae, galaxies, star clusters as sources.
10. **3D ray tracing** — Full 3D propagation for off-axis analysis.


---

## 9. Using This for Telescope Design Decisions

### Decisions the simulation can directly inform

**"Should I get an f/5 or f/6 Newtonian?"**

Set up the comparison (as done in `main.py` currently with the 10"
f/5 vs f/6 configs). Key trade-offs you'll see:

| Factor | f/5 (1270mm) | f/6 (1524mm) |
|--------|-------------|-------------|
| Tube length | ~1245mm (shorter, more portable) | ~1499mm (longer) |
| Airy disk | 3.36 µm | 4.03 µm |
| Plate scale | 163"/mm | 135"/mm |
| Coma-free field | Narrower | ~44% wider (scales as f^2) |
| Collimation tolerance | Tighter | More forgiving |
| Eyepiece magnification | Lower per mm of eyepiece FL | Higher per mm |

> **Note on Airy disk size**: Both telescopes have identical angular resolution
> (0.53 arcsec at 550 nm) because they share the same 254 mm aperture. The
> physical Airy disk is larger at f/6 only because the longer focal length
> spreads the image over a bigger area on the focal plane — it is more
> magnified, not less sharp.

The simulation shows these quantitatively in the PSF and spot
diagram comparisons.

**"Can I use a spherical mirror at my chosen f/ratio?"**

Compare parabolic vs spherical at your f/ratio. If the spherical
Strehl ratio is above 0.8, a spherical mirror is acceptable.
Approximate threshold: spherical is OK above f/10 for most
apertures. At f/5-f/6, spherical aberration is severe.

**"How much does the secondary obstruction hurt?"**

Compare with/without obstruction. The PSF comparison shows the
contrast reduction (energy moved from central peak to rings).
Typical impact: 20-30% obstruction reduces Strehl by a few percent
and increases the first ring brightness. For visual planetary
observing, this is noticeable but not dramatic.

**"What aperture do I need to resolve X?"**

The Rayleigh resolution limit is `theta = 1.22 * lambda / D`.
At 550nm: a 150mm scope resolves 0.92", 200mm resolves 0.69",
254mm resolves 0.54". The PSF comparison across apertures shows
this directly. Compare to typical seeing (1.5-2.5") — going above
~250mm aperture rarely helps for visual from a typical site.

**"What eyepiece for planetary viewing?"**

The exit pupil should be 0.5-1.5mm for sharp planetary views
(high magnification, no washout). Use:
```
exit_pupil = aperture / magnification = aperture * f_eyepiece / f_telescope
```
For a 254mm f/5: a 5mm eyepiece gives 254x magnification and
1.0mm exit pupil (ideal). A 25mm eyepiece gives 51x and 5mm exit
pupil (washed out on planets, good for deep sky).

Set these in `main.py` and look at the source images to see the
visual difference.

**"Newtonian vs Cassegrain vs Mak-Cass for my use case?"**

| | Newtonian | Cassegrain | Mak-Cass |
|---|---|---|---|
| **Best for** | Deep sky (wide field, fast f/ratio) | Planetary/lunar (long FL, narrow field) | Planetary/lunar (compact, long FL) |
| **Tube length** | Long (= focal length) | Short (= primary FL) | Short (= primary FL) |
| **Obstruction** | Small (flat diagonal) | Moderate (hyperbolic secondary) | Moderate (aluminized spot) |
| **Collimation** | Needs regular adjustment | More stable | Very stable (sealed tube) |
| **Cost** | Lowest per aperture inch | Moderate | Higher (precision corrector) |

The ray trace comparison shows the physical differences. The PSF
comparison shows the obstruction impact. Use the source imaging to
see what Jupiter or the Moon looks like through each design.

### What to do next with the simulation

1. **Start with the f/5 vs f/6 comparison** already set up — run
   `python main.py` and examine the plots.
2. **Add source imaging** — set `source_type = "jupiter"` or
   `"moon"` with an eyepiece to see simulated views.
3. **Try spherical vs parabolic** at your chosen f/ratio to see
   if the cheaper spherical mirror is viable.
4. **Compare obstruction ratios** to understand the contrast trade-off.
5. **Run coma analysis** (`show_coma_analysis = True`) to understand
   the usable field of view at your f/ratio.

The simulation gives you quantitative answers to these questions
in visual form — PSFs, spot diagrams, and simulated images that
show exactly what the physics predicts.
