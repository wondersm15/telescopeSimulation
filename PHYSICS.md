# Physics Implementation Reference

This document provides a comprehensive overview of what physical phenomena are and aren't modeled in the telescope simulation, where they're implemented, and how accurate they are.

---

## ✅ Implemented Physics

### 1. Diffraction (Wave Optics)

**Location**: `telescope_sim/plotting/psf.py`, used throughout PSF computations

**What**: Light diffracts at the aperture, creating an Airy pattern (central disk + rings).

**Where it appears**:
- PSF plots (1D and 2D)
- Simulated source images (Jupiter, Moon, stars)
- Performance analysis

**Accuracy**:
- Uses exact Airy disk formula: `I(r) = [2·J₁(x)/x]²` where `x = π·D·r/(λ·f)`
- FFT-based computation for spider vanes (exact diffraction through aperture)
- Central obstruction included via obstruction ratio

**Formula**:
```
Rayleigh resolution limit = 1.22 · λ / D  (in radians)
Airy disk radius = 1.22 · λ · f/D  (in mm at focal plane)
```

**Real physics**: ✅ Accurate for circular apertures


---

### 2. Central Obstruction (Secondary Mirror)

**Location**: All PSF and image rendering functions

**What**: Secondary mirror blocks central portion of aperture, reducing contrast and enlarging Airy disk.

**Where it appears**:
- Cassegrain, Newtonian (when secondary present), Maksutov-Cassegrain telescopes
- PSF computations include obstruction ratio
- Simulated images show reduced contrast

**Accuracy**:
- Obstruction ratio automatically computed from secondary diameter
- PSF modified by `(1 - ε²)` factor where ε = obstruction ratio
- Affects Strehl ratio and contrast transfer function

**Real physics**: ✅ Accurate obstruction model


---

### 3. Spider Vane Diffraction Spikes

**Location**: `telescope_sim/plotting/psf.py` (FFT-based PSF computation)

**What**: Spider vanes supporting the secondary mirror create diffraction spikes perpendicular to each vane.

**Where it appears**:
- 2D PSF plots (log scale reveals spikes)
- Simulated star images
- Comparison mode PSF analysis

**Accuracy**:
- FFT computation of aperture function includes vanes as thin obstructions
- Number of spikes = 2 × number of vanes (for straight vanes)
- Spike intensity and extent depend on vane width

**Configuration**:
- Spider vanes: 0, 3, or 4 typical (adjustable in GUI)
- Vane width: 0.5-5.0 mm (default 2.0 mm)

**Real physics**: ✅ Accurate diffraction from thin obstructions


---

### 4. Chromatic Aberration (Refractors Only)

**Location**: `telescope_sim/optics/apo_lenses.py`, `telescope_sim/plotting/ray_trace_plot.py` (chromatic PSF)

**What**: Different wavelengths focus at different distances due to dispersion in glass.

**Where it appears**:
- Singlet refractors: significant color fringing
- Achromats: reduced but visible at high magnification
- APO doublets/triplets: minimal (near diffraction-limited)

**Implementation**:
- Wavelength-dependent refractive index via Sellmeier equation
- Per-band PSF convolution for RGB source images (see §7)
- Longitudinal chromatic aberration causes wavelength-dependent defocus

**Accuracy**:
- Uses real glass dispersion formulas (N-BK7, N-SF11, etc.)
- APO designs use realistic glass combinations
- Approximate formula for singlets: `blur ≈ 30/f-ratio arcsec`

**Real physics**: ✅ Accurate for implemented lens types


---

### 7. Spectral Rendering / Colorimetry

**Location**: `telescope_sim/physics/colorimetry.py`, used by
`_render_source_through_telescope` in `telescope_sim/plotting/ray_trace_plot.py`

**What**: Turning a source spectrum plus wavelength-dependent optics into
screen RGB.

**Implementation**:
- CIE 1931 2° standard-observer colour-matching functions, 10 nm table
- Planck's law for the stellar spectral energy distribution, from each star's
  effective temperature (`star_temperatures_K`)
- The visible band (400–700 nm, 9 slices by default) is sampled; each slice
  gets its own chromatic defocus PSF and its own linear-sRGB weight from the
  CMF integral, so every slice contributes to all three channels
- Weights are white-balanced to equal energy, putting the neutral point near
  5500 K — Sun-like stars render white, cooler amber, hotter blue-white
- 9 slices verified converged against 21 (colour shift < 0.05 per channel)

**Accuracy**:
- Star colours are *integrated from* Planck's law and the CMFs rather than
  tabulated, so they are real physics rather than art direction. Every
  spectral-class palette in `sources.py` is derived this way — the previous
  hand-written tuples disagreed with the blackbody colours (they gave class F
  a warm tint where a 7000 K blackbody is slightly *blue* of the D65 sRGB
  white point)
- ⚠️ Out-of-gamut spectral colours are clipped to the sRGB cube. This is a
  display limit, not a modelling choice: near-monochromatic 550 nm light
  (a badly chromatic objective's core) cannot be shown by an sRGB monitor at
  its true saturation, so it renders as full green
- ⚠️ Sources without a modelled temperature (plain `StarField`, `PointSource`)
  fall back to a flat spectrum carrying their tabulated tint

**Real physics**: ✅ Colour science and stellar SED are accurate; ⚠️ display
gamut is a hard limit of sRGB output

#### 7b. Mesopic colour vision (eye view only)

**Location**: `colorimetry.mesopic_chroma_gain` / `apply_mesopic_desaturation`

**What**: How much of a pixel's colour a dark-adapted observer can actually
perceive. Human colour vision is **band-pass in luminance**:

| Regime | Luminance | Percept |
|---|---|---|
| Scotopic | ≲ 0.005 cd/m² | Rods only — a single receptor class, so **no colour at all** |
| Mesopic | ~0.005–5 cd/m² | Cones progressively engage; saturation climbs |
| Photopic | ≳ 5 cd/m² | Full colour (all ordinary daylight scenes) |
| Glare | ~10⁵ cd/m² and up | Cones overloaded; percept whitens |

Both ends blend a pixel toward its own luminance; only the middle shows full
chroma. This is why a nebula looks grey in an eyepiece and colourful in a
photograph, and why only the brightest stars show an obvious tint.

**Applied to the eye view only.** A detector has no cones — a camera records
the same chromaticity at any flux until the wells clip — so the detector path
deliberately skips it. That difference is the point of the *Viewing Modes:
Detector vs Eye* tutorial module, and since R5.8 it is the *only* thing that
differs between the two views: both are drawn through the same display
transfer function (§7c), so everything else you see between them is physics
rather than a display curve.

**Two calibrations** (the same curve, different units):

- **Extended sources (Moon, Jupiter, Saturn) — gated in cd/m².** Each source
  has a catalogue surface brightness (`surface_brightness_mag_arcsec2()`),
  converted with L = 10.8·10⁴ · 10^(−0.4·S) cd/m². The display-to-cd/m² scale
  is **measured** in each render: the Eye view displays the object at its
  naked-eye surface brightness (§7c), so its mean display luminance must
  equal its catalogue luminance; the real retinal luminance at the chosen
  exit pupil is that times (p/7 mm)². Values: full Moon 3.35 mag/arcsec² (≈4,900
  cd/m²; Allen, V = −12.74 over 1865″), Jupiter 5.3 (≈800 cd/m²) and the
  Saturn globe 6.7 (≈220 cd/m²) (Mallama & Hilton 2018 V(1,0) at mean
  opposition). The Moon's lit part dims with phase angle α as ΔV = 0.026α +
  4·10⁻⁹α⁴ (Allen). The cone half-gain sits at the geometric mean of the CIE
  191 limits (0.16 cd/m²), giving ≈3 % colour at 0.005 cd/m² and ≈97 % at
  5 cd/m². The figure annotation states the object's luminance and regime.
- **Star sources — display units.** Stars have no surface brightness, so the
  original tuned gate (threshold 0.05, bleach 0.5 of display saturation) is
  kept. The *Viewing Modes* star demo is built on it. Flagged on the figure.

**Accuracy**:
- ✅ The *shape* is real: the two-sided rod/cone structure, and the fact that
  faint light is achromatic, are established visual physiology
- ✅ Extended sources: the luminance scale and the switch-on thresholds are
  physical (catalogue photometry + CIE 191:2010)
- ⚠️ The glare/whitening level for extended sources (10⁵ cd/m²) is an order
  of magnitude, not fitted. Steady-state half-bleach (~10^4.3 td, Rushton &
  Henry 1968) does not itself desaturate the percept, because cone gain adapts
- ⚠️ Saturn's rings get the globe's surface brightness (B ring similar,
  A/C rings fainter)
- ⚠️ Stars: thresholds are tuned display parameters, not cd/m²
- ⚠️ Both terms are smooth Michaelis–Menten curves rather than the CIE
  191:2010 mesopic interpolation

**Real physics**: ✅ for extended sources (switch-on); ⚠️ glare level and
the star gate are tuned

**Resolved 2026-10-31** (was: "Jupiter goes grey at a 2 mm exit pupil"). The
old gate's display units were normalised per source, so one threshold meant
very different luminances for different objects. Jupiter at 2 mm is ≈65
cd/m², photopic, and now shows its colour. Its bleach term had also removed
about half of every planet's colour even at a 7 mm pupil.

#### 7c. Display transfer function (both views)

**Location**: `colorimetry.srgb_encode` / `srgb_decode` / `tone_map_gamma`,
applied at the end of `_render_source_through_telescope` and (for the
colormapped path) by `ray_trace_plot._DisplayNorm`

**What**: The step that puts simulated radiance on a physical screen. A
monitor is not linear — handed a code value `v` it emits luminance ≈ `v²·²`
(the sRGB EOTF). `imshow` writes float RGB straight into the display buffer,
so its input *is* a code value. Encoding with the inverse curve cancels the
monitor's decode, leaving **screen luminance ∝ simulated radiance**.

**Why there is no "eye response" curve here.** The observer is already in the
loop, looking at the monitor. Their logarithmic response is applied by them,
in real time. The renderer previously applied an `asinh` stretch in the eye
view "to model the eye's log response", which compressed the scene twice.
Measured on Jupiter that flattened real belt/zone contrast by 2.1× and
squashed a 12.25× exit-pupil surface-brightness range to 2.56× on screen
(R5.8); the detector view, missing the encode in the other direction,
exaggerated the same contrast by 2.15×. Both are now encoded identically.

**Tone mapping.** A screen in a lit room holds ~200:1
(`DISPLAY_USABLE_CONTRAST`). Where a scene exceeds that, `tone_map_gamma`
returns γ = ln(D)/ln(S) and the render is compressed by `radiance^γ` — which
maps an S:1 scene onto exactly D:1 and degenerates to γ = 1 when the scene
fits. Scene contrast is a property of the **source** (its magnitude spread),
never of the frame: deriving it per render would let it drift as a slider
moves, breaking the shared brightness scale the Before/After panels depend
on.

**Where it engages**: the Moon spans 2:1, Jupiter 203:1, Saturn 484:1, and
both star fields fit — 17 of 18 modules render at γ = 1.0, exactly
photometric. Only `saturation_demo` (mag −1…6.5, 1000:1) compresses, at
γ = 0.767, and that figure prints the exponent and the words "not
photometric".

**Accuracy**:
- ✅ The sRGB curve is the IEC 61966-2-1 standard, exact and losslessly
  invertible
- ✅ Verified end-to-end by decoding renders back to luminance: belt/zone
  contrast and aperture D² (16.01× vs 16.00×) reproduce at fidelity 1.00.
  (The 49× exit-pupil ratio was also reproduced on screen until
  2026-10-31; it is now reported in cd/m² instead. See below.)
- ⚠️ `DISPLAY_USABLE_CONTRAST = 200` is a room-lighting assumption, not a
  measurement of the user's monitor; a dark room supports more
- ⚠️ Tone-mapped output (γ < 1) is deliberately **not** photometric. Flagged
  on the figure itself, not only in code

**Eye view: extended objects shown at naked-eye surface brightness**
(2026-10-31). Real surface brightness through a telescope is (p/7 mm)² of
naked-eye, capped at 1, and that factor is still computed. It sets the
object's retinal luminance in cd/m², which drives the colour gate (§7b) and
is printed on the figure. It is **not** applied to the displayed picture.
Rendered literally on a linear screen, a 1 mm exit pupil is 2 % brightness,
so high-power views of the Moon and planets came out near black. A real
observer doesn't see that: their dark-adapted eye adapts to the field, and a
200× Moon still looks bright. The screen can't make the viewer's eye adapt
to a dark patch, so the renderer shows the adapted percept directly. Point
sources are unchanged (aperture-driven, ∝ D²).

- ⚠️ Perceptual display choice, not photometry: brightness differences
  *between* exit pupils are not shown, only the cd/m² figure and the colour
  that follows from it. Flagged on the figure ("Approx: shown at naked-eye
  brightness (eye adapts)")
- Considered and rejected as over-complicated: a Ward (1994) contrast-based
  adaptation scale, which would partially restore the dimming

**Real physics**: ✅ Exact at γ = 1 (nearly every module); ⚠️ disclosed
approximation where the scene physically cannot fit a display; ⚠️ Eye-view
extended-source brightness is the adapted percept, not radiance

### 8. Eyepiece: magnification, exit pupil and field of view

**Location**: `telescope_sim/geometry/eyepiece.py`, consumed by
`ray_trace_plot.plot_source_image` and by the `eyepiece_magnification`
tutorial module (R5.9)

**What**: The eyepiece is what converts a focal-plane image into something an
eye can look at, and it sets four coupled quantities from one choice:

| Quantity | Formula | Notes |
|---|---|---|
| Magnification | `M = f_tel / f_ep` | Both focal lengths, same units |
| Exit pupil | `p = D / M` ( = `D·f_ep/f_tel` ) | Diameter of the light cone leaving the eyepiece |
| True field | `TFOV = 206265·d_stop / f_tel` | **Exact**, when the field-stop diameter is known |
| True field (fallback) | `TFOV ≈ AFOV / M` | Approximate — ignores eyepiece distortion |

**The exit pupil is the master variable.** Magnification, true field, apparent
size and eye-view surface brightness are not four independent knobs — pick an
eyepiece and all of them follow. This is why the tutorial exposes a real
eyepiece selector rather than a free-floating exit-pupil control: an
independent exit-pupil slider would let the user request combinations that no
physical eyepiece can produce.

Both useful-magnification limits are **derived from the exit pupil**, not
hard-coded:
- **Max useful** `M = D / MIN_USEFUL_EXIT_PUPIL_MM` (0.5 mm) — beyond this the
  cone is finer than the eye can use and the view only gets dimmer and
  blurrier. This is the origin of the familiar "2× the aperture in mm" rule of
  thumb, which is just `D / 0.5` rewritten
- **Min useful** `M = D / DEFAULT_EYE_PUPIL_MM` (7.0 mm) — below this the exit
  pupil overflows the eye's own pupil and the surplus aperture is thrown away

`DEFAULT_EYE_PUPIL_MM` is the **same object** as the renderer's `EYE_PUPIL_MM`
(aliased, not re-declared, and pinned by an identity assertion in
`tests/test_eyepiece.py`). If the two drifted, the eyepiece model and the
eye-view brightness model would be describing different observers.

**Exit-pupil washout** (`_apply_exit_pupil_washout`): as the exit pupil grows
past the eye's pupil, or shrinks toward the diffraction limit, fine detail
loses contrast. The operator blends the image toward a **locally** smoothed
copy (Gaussian, σ = 4% of the frame) rather than toward the frame average.
Two defects were fixed here in R5.9/S2, both of which the frame-mean version
had:
- it **added light to empty sky** — for the Moon at a 6.4 mm exit pupil, black
  sky rendered at 0.68, so the night sky glowed grey
- it made washout **depend on framing** — the same object in a wider field had
  a different mean, hence different contrast, which is unacceptable in a
  module whose whole subject is changing the field of view

A fixed fraction of the *frame* is the right scale because the field maps to
the eyepiece's fixed apparent field, so 4% of the frame is a constant
*apparent* angle to the observer — which is the scale the eye's response is
defined on.

> **Consumer note:** this operator is shared code. The correction changes the
> eye-view render in the **Design tab** as well as the tutorial (`design_tab.py`
> imports the same `plot_source_image`). That is intended — the old behaviour
> was wrong in both places.

**Eye relief** — the distance behind the eyepiece where the exit pupil forms,
and the reason short focal lengths are uncomfortable and eyeglass wearers need
long-eye-relief designs — is **described in the reference text but NOT
modelled**. Nothing in the render depends on it.

**Accuracy**:
- ✅ `M`, `p`, and the exact `TFOV` from a field stop are elementary geometric
  optics, exact
- ✅ Both useful-magnification limits are derived from their defining exit
  pupil, verified by monkeypatching the constant (`test_threshold_actually_
  drives_the_limit`) rather than by asserting an equivalent formula
- ⚠️ `TFOV ≈ AFOV/M` is the standard approximation, used only when no field
  stop is supplied; which basis was used is disclosed in `Eyepiece.summary()`
  and by the `tfov_is_exact` property
- ⚠️ `_WASHOUT_LOCAL_SCALE = 0.04` is **empirical** — chosen so the effect
  reads as loss of fine detail rather than as global fog, not fitted to
  psychophysical data. Flagged in code and in the module narrative
- ❌ Eye relief, eyepiece aberrations, and field-stop vignetting are not
  modelled

**Real physics**: ✅ Exact for the geometric quantities; ⚠️ the washout
operator is a disclosed perceptual approximation


---

### 5. Coma (Off-Axis Aberration)

**Location**: `telescope_sim/plotting/ray_trace_plot.py` (`compute_coma_spot()`, `_compute_psf_at_field_angle()`)

**What**: Off-axis point sources appear comet-shaped due to asymmetric aberration.

**Where it appears**:
- Source images at field positions away from optical axis
- Worst for parabolic mirrors at low f-ratios
- Negligible for on-axis imaging

**Implementation**:
- Geometric ray-traced coma pattern computed from field angle
- Pupil zones sampled azimuthally to build coma "wing"
- Convolved with Airy PSF for final image

**Formula**:
```
Coma blur ≈ (field_angle)² / (16·f-ratio³)  (approximate)
```

**Real physics**: ✅ Geometric approximation, accurate for small field angles


---

### 6. Spherical Aberration (Spherical Primaries)

**Location**: `telescope_sim/plotting/ray_trace_plot.py` (`_compute_spherical_aberration_spot()`)

**What**: Spherical mirrors focus marginal rays closer than paraxial rays, creating blur.

**Where it appears**:
- Newtonian telescopes with spherical primary option
- Ray trace spot diagrams show enlarged blur circle
- Simulated source images convolved with geometric aberration PSF

**Implementation**:
- Ray tracing through spherical mirror surfaces
- Geometric spot diagram converted to PSF kernel
- Convolved with diffraction PSF for combined effect

**Accuracy**:
- Exact ray tracing for spherical surfaces
- Longitudinal spherical aberration: `LSA ≈ D³/(128·f³)` (Gauss approximation)
- Approximate blur formula: `blur ≈ 1000/(f-ratio)³ arcsec`

**Note**: Parabolic primaries have zero on-axis spherical aberration (by design).

**Real physics**: ✅ Accurate geometric model


---

## ❌ NOT Yet Implemented

### 1. Astigmatism

**What**: Off-axis aberration where tangential and sagittal ray bundles focus at different distances.

**Impact**: Would cause star images to appear elliptical off-axis.

**Why not included**: Lower priority than spherical/coma; requires 3D ray tracing.


---

### 2. Field Curvature

**What**: Best focus surface is curved, not flat.

**Impact**: Stars sharp at center but blurred at edge of field (or vice versa).

**Why not included**: Most noticeable for wide-field imaging; simulation currently focuses on on-axis or small-field performance.


---

### 3. Distortion (Pincushion/Barrel)

**What**: Magnification varies across field, warping straight lines.

**Impact**: Geometric image warping (not blur).

**Why not included**: Minimal impact on resolution/PSF; primarily affects astrometry.


---

### 4. Atmospheric Seeing

**What**: Turbulence in atmosphere blurs images even for perfect optics.

**Impact**: Ground-based telescopes limited to ~1 arcsec resolution regardless of aperture.

**Partial implementation**: Seeing blur can be added as Gaussian convolution in source rendering, but not yet exposed in GUI.

**Future**: Add seeing FWHM parameter (typical values: 1-2 arcsec for good sites, 0.5 arcsec for excellent).


---

### 5. Thermal Effects

**What**: Temperature gradients inside telescope tube create air currents (tube currents).

**Impact**: Degrades image quality, especially for closed-tube designs.

**Why not included**: Highly variable and system-dependent; difficult to model accurately.


---

### 6. Optical Surface Errors

**What**: Deviations from ideal mirror/lens shape due to manufacturing tolerances.

**Impact**: Reduces Strehl ratio, degrades PSF.

**Why not included**: Requires specifying surface error maps (beyond scope of basic simulation).


---

## Where Physics is Applied

### Ray Trace Plots
- ✅ Geometric aberrations (spherical, coma)
- ✅ Chromatic aberration (refractors, wavelength-dependent paths)
- ✅ Exact ray-surface intersections

### PSF Plots (1D and 2D)
- ✅ Diffraction (Airy pattern)
- ✅ Central obstruction
- ✅ Spider vane diffraction spikes
- ✅ Spherical aberration (spherical primaries) via convolution

### Spot Diagrams
- ✅ Geometric aberrations (shows ray convergence)
- ✅ Color-coded by incident radial distance (shows spherical aberration)
- ✅ RMS and max spread metrics

### Simulated Source Images (Jupiter, Moon, Stars)
- ✅ Diffraction PSF convolution
- ✅ Chromatic aberration (RGB channel-specific PSFs for refractors)
- ✅ Coma (off-axis sources)
- ✅ Spherical aberration (spherical primaries)
- ✅ Spider diffraction spikes
- ⚠️  Seeing (optional, not yet in GUI)

### MTF (Modulation Transfer Function)
- ✅ Diffraction-limited MTF
- ✅ Obstruction effects
- ❌ Geometric aberrations (not yet combined with MTF)


---

## Accuracy Summary

| Physics Effect              | Implementation | Accuracy Level | Notes                          |
|-----------------------------|----------------|----------------|--------------------------------|
| Diffraction (Airy)          | Exact formula  | ✅ Exact       | Standard Bessel function       |
| Central obstruction         | Exact formula  | ✅ Exact       | Modified Airy pattern          |
| Spider diffraction          | FFT aperture   | ✅ Accurate    | 2D Fourier optics              |
| Chromatic (refractors)      | Sellmeier eqn  | ✅ Accurate    | Real glass dispersion          |
| Coma (off-axis)             | Geometric rays | ⚠️  Approx     | Valid for small field angles   |
| Spherical aberration        | Ray tracing    | ✅ Accurate    | Exact for spherical surfaces   |
| Astigmatism                 | Not included   | ❌ N/A         | Future work                    |
| Field curvature             | Not included   | ❌ N/A         | Future work                    |
| Atmospheric seeing          | Gaussian blur  | ⚠️  Simplified | Not exposed in GUI yet         |


---

## Formulas and References

### Diffraction
- Rayleigh criterion: `θ = 1.22 λ / D` (radians)
- Dawes limit: `θ = 116 / D_mm` (arcsec) — empirical for double stars
- Airy disk angular diameter: `θ = 2.44 λ / D` (radians)

### Chromatic Aberration
- Longitudinal CA: `ΔfCA = f · (nF - nC) / (nd - 1)` where nF, nC, nd are refractive indices
- Singlet blur (approx): `30 / f-ratio` arcsec

### Spherical Aberration
- Longitudinal SA: `LSA ≈ D³ / (128 f³)` (Gauss formula for spherical mirror)
- Angular blur: `~1000 / (f-ratio)³` arcsec (rough estimate)

### Obstruction
- Strehl ratio reduction: `S ≈ (1 - ε²)` for small obstructions, where ε = obstruction ratio
- Central obstruction typical values:
  - Newtonian: 15-25% (diameter ratio)
  - Cassegrain: 25-35%
  - Maksutov: 30-40%


---

## How to Verify Implemented Physics

### Test Cases

1. **Diffraction**: Compare PSF Airy disk size vs. analytical formula → should match within 1%
2. **Chromatic aberration**: Refractor with singlet should show color fringing on Jupiter limb
3. **Spherical aberration**: f/4 spherical Newtonian should show ~15 arcsec blur vs. f/4 parabolic ~0.3 arcsec
4. **Spider spikes**: 4-vane spider should produce 8 spikes at 45° angles
5. **Coma**: Off-axis source in Newtonian should show asymmetric comet-like PSF


---

## Future Enhancements

1. Add atmospheric seeing parameter to GUI (source images tab)
2. Implement astigmatism for off-axis performance
3. Add field curvature visualization
4. Include thermal effects (tube currents) as optional degradation
5. Surface error maps for simulating real mirror quality
6. Zemax/CODE V comparison mode for validation


---

**Last Updated**: March 2026
**See also**: CLAUDE.md (coding conventions), README.md (project overview)
