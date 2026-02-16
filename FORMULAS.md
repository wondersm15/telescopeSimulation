# Formulas Reference

This file explains the formulas used in the telescope simulation,
particularly those shown on the PSF (Point Spread Function) plot.


## Variables

| Symbol | Meaning | Units |
|--------|---------|-------|
| D | Primary mirror diameter (aperture) | mm |
| f | Focal length of the primary mirror | mm |
| f/# | Focal ratio = f / D | dimensionless |
| λ | Wavelength of light | mm (internally); nm in UI |
| r | Radial distance from center of the focal plane | mm |
| h | Height of a ray above the optical axis in the pupil | mm |
| R | Radius of curvature of a spherical mirror (R = 2f) | mm |
| σ | RMS geometric spot radius | mm |


## Airy Diffraction Pattern

```
I(r) = [2 J₁(x) / x]²,   x = π D r / (λ f)
```

When light from a point source (e.g. a star) passes through a circular
aperture, it does not focus to an infinitely small point — it forms a
diffraction pattern called the **Airy disk**. This is a bright central
spot surrounded by concentric rings of rapidly decreasing brightness.

The formula gives the normalized intensity I as a function of radial
distance r from the center of the pattern. J₁ is the Bessel function
of the first kind (order 1), which arises from the circular symmetry
of the aperture.

This is the fundamental limit on a telescope's resolving power: no
matter how perfect the optics, two point sources closer together than
the Airy disk radius cannot be distinguished.

**Approximation note**: This assumes an unobstructed circular aperture.
Real Newtonian telescopes have a central obstruction from the secondary
mirror support, which slightly modifies the pattern (see PHYSICS.md).


## Airy Disk First Zero (Airy Radius)

```
r₁ = 1.22 λ f / D
```

This is the radius of the first dark ring in the Airy pattern — the
boundary of the central bright spot. It comes from the first zero of
J₁(x), which occurs at x ≈ 3.8317, giving r ≈ 1.22 λf/D.

The Airy radius sets the physical size of the smallest resolvable
detail on the focal plane. A larger aperture D shrinks the Airy disk
(better resolution). A longer focal length f enlarges it (magnifies
the pattern on the focal plane but doesn't change angular resolution).

**Example**: For our 200mm f/5 telescope at λ = 550nm:
r₁ = 1.22 × 0.00055mm × 5 = 0.00336 mm ≈ 3.36 μm


## Rayleigh Resolution Limit

```
θ = 1.22 λ / D
```

This is the angular version of the Airy radius — the minimum angular
separation (in radians) at which two point sources can be distinguished.
It is the same physics as the Airy disk formula, expressed as an angle
on the sky instead of a distance on the focal plane.

The conversion between angular and focal-plane distances is:
r = θ × f  (for small angles, with θ in radians)

**Example**: For our 200mm aperture at λ = 550nm:
θ = 1.22 × 550e-9 / 0.200 = 3.36e-6 rad ≈ 0.69 arcseconds


## Transverse Spherical Aberration (3rd Order)

```
ε(h) ≈ -h³ / (8 f²)
```

*Only shown when the primary mirror is spherical.*

A spherical mirror does not focus all parallel rays to a single point.
Rays hitting the mirror farther from the center (larger h) come to
focus at a different position than rays near the center. This is
**spherical aberration** — the most basic optical aberration.

The formula gives the transverse miss distance ε at the paraxial focal
plane for a ray entering at height h above the axis. This is a
third-order (Seidel) approximation; the simulation uses the exact
formula derived from the mirror equation x² + (y − R)² = R² and the
law of reflection.

The negative sign means the ray crosses the axis before reaching the
paraxial focus (undercorrection). The h³ dependence means edge rays
are affected much more strongly than central rays.

A **parabolic** mirror, by contrast, has zero spherical aberration
for on-axis rays — that is the defining geometric property of a
paraboloid.

**Example**: For our 200mm f/5 spherical mirror, a ray at h = 95mm
(near the edge): ε ≈ -95³ / (8 × 1000²) ≈ -0.107 mm ≈ -107 μm.
This is much larger than the Airy radius (3.36 μm), so the spherical
mirror is far from diffraction-limited.


## Strehl Ratio (Approximation)

```
Strehl ≈ 1 / (1 + (π σ / 2 r₁)²)
```

The Strehl ratio measures how close a telescope is to diffraction-
limited performance. It is defined as the ratio of the actual peak
intensity of the PSF to the peak intensity of a perfect (Airy) PSF:

- **Strehl = 1.0**: perfect optics (diffraction-limited)
- **Strehl > 0.8**: conventionally considered "diffraction-limited"
  (the Maréchal criterion)
- **Strehl << 1**: significant aberration

The formula used here is a convenient approximation based on the
geometric spot size σ (RMS radius) relative to the Airy radius r₁.
A precise Strehl calculation requires wavefront error analysis, which
is not yet implemented (see PHYSICS.md).

**Example**: For a parabolic 200mm f/5 (σ ≈ 0, analytical):
Strehl ≈ 1.0 — diffraction-limited, as expected.

For a spherical 200mm f/5 (σ ≈ 22 μm from best focus):
Strehl ≈ 1 / (1 + (π × 22 / (2 × 3.36))²) ≈ 0.01 — very poor,
confirming the spherical mirror is far from diffraction-limited.


## How They Fit Together

The **combined PSF** shown on the plot is the convolution of the
geometric spot (from ray optics) with the Airy pattern (from wave
optics). This correctly captures both effects:

1. If the geometric spot is much smaller than the Airy disk
   (e.g. parabolic mirror), the combined PSF ≈ the Airy pattern
   and the telescope is diffraction-limited.

2. If the geometric spot is much larger than the Airy disk
   (e.g. spherical mirror), the combined PSF ≈ the geometric spot
   and diffraction is negligible — aberrations dominate.

3. When both are comparable in size, neither can be ignored and the
   full convolution is needed.
