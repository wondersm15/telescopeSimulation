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
| Photopic (bright) | ≫ 5 cd/m² | Cone pigment bleaches; percept whitens |

Both ends blend a pixel toward its own luminance; only the middle shows full
chroma. This is why a nebula looks grey in an eyepiece and colourful in a
photograph, and why only the brightest stars show an obvious tint.

**Applied to the eye/log view only.** A detector has no cones — a camera
records the same chromaticity at any flux until the wells clip — so the linear
path deliberately skips it. That difference is the point of the *Viewing Modes:
Detector vs Eye* tutorial module.

**Accuracy**:
- ✅ The *shape* is real: the two-sided rod/cone/bleaching structure, and the
  fact that faint flux is achromatic, are established visual physiology
- ⚠️ The *calibration* is not derived. The renderer works in normalised
  display flux (1.0 = saturation level), not cd/m², so the cone threshold
  (0.05) and bleach level (0.5) are tuned display parameters, and both terms
  are smooth Michaelis–Menten curves rather than the CIE 191:2010 mesopic
  interpolation. Flagged in the module docstring and in the module narrative

**Real physics**: ⚠️ Physiologically-motivated perceptual model — ordering and
limiting behaviour are real, absolute thresholds are tuned


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
