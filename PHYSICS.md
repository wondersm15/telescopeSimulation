# Physics Inventory

## Implemented

### Geometric Optics
- **Law of reflection**: `d_reflected = d - 2 * dot(d, n) * n` — exact.
- **Parabolic mirror**: Ray-parabola intersection via quadratic solve, exact surface normals. Correctly focuses all on-axis parallel rays to a single focal point.
- **Spherical mirror**: Ray-circle intersection, exact surface normals. Correctly exhibits spherical aberration (edge rays focus at different point than center rays).
- **Flat mirror**: Ray-line-segment intersection, exact reflection. Used for Newtonian secondary diagonal.

### Wave Optics
- **Airy diffraction pattern**: Point spread function for circular aperture diffraction. Uses `PSF(r) = [2 * J1(x) / x]^2` where `x = pi * D * r / (lambda * f)`. Physically determines the resolution limit of the telescope.
- **Central obstruction diffraction**: Annular aperture PSF accounting for secondary mirror obstruction. Uses `PSF(r) = [1/(1-ε²)]² × [2J₁(x)/x - ε²·2J₁(εx)/(εx)]²` where `ε = D_secondary / D_primary`. Reduces to the standard Airy pattern when ε=0. Produces stronger secondary rings and slightly lower peak intensity compared to an unobstructed aperture.

### Image Formation
- **Focal plane imaging**: Geometric ray positions convolved with diffraction PSF to produce simulated images.


## Not Yet Implemented

### Geometric Optics
- **Refraction** (Snell's law) — needed for lenses, eyepieces, corrector plates
- **Conic sections beyond parabola/sphere** — hyperbolic, elliptical mirrors (for Cassegrain, Ritchey-Chretien designs)
- **Off-axis rays / field angle** — currently only on-axis (parallel to optical axis) rays are modeled
- **Vignetting** — light blockage by the secondary mirror obstruction and tube walls
- **Surface errors** — real mirrors have manufacturing imperfections

### Wave Optics
- **Chromatic effects** — wavelength-dependent behavior (currently monochromatic at 550nm)
- **Wavefront error** — phase errors from imperfect optics
- **Interference and coherence effects**

### Atmospheric
- **Atmospheric seeing** — turbulence-induced blurring (roughly Gaussian, typically 1-3 arcsec FWHM)
- **Atmospheric refraction** — bending of light through the atmosphere
- **Atmospheric extinction** — dimming of light through the atmosphere

### Extended Sources
- **Planetary / deep-sky sources** — spatially extended objects (Jupiter, nebulae) rather than point sources
- **Real-time data integration** — linking to actual astronomical data for source definitions

### Detector
- **Pixel sampling** — finite detector pixel size
- **Noise** — photon noise, read noise, dark current
- **Quantum efficiency** — wavelength-dependent detector sensitivity
