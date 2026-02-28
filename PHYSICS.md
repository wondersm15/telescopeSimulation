# Physics Inventory

## Implemented

### Geometric Optics
- **Law of reflection**: `d_reflected = d - 2 * dot(d, n) * n` — exact.
- **Parabolic mirror**: Ray-parabola intersection via quadratic solve, exact surface normals. Correctly focuses all on-axis parallel rays to a single focal point.
- **Spherical mirror**: Ray-circle intersection, exact surface normals. Correctly exhibits spherical aberration (edge rays focus at different point than center rays).
- **Flat mirror**: Ray-line-segment intersection, exact reflection. Used for Newtonian secondary diagonal.
- **Hyperbolic mirror**: Ray-hyperbola intersection via quadratic solve, exact surface normals on the convex branch. Used for Cassegrain secondary. Surface equation: `(y+a)²/a² - x²/b²= 1` with `b² = a²(e²-1)`.
- **Cassegrain two-mirror system**: Parabolic primary + convex hyperbolic secondary. The secondary magnifies the focal length by factor M: `f_eff = f_primary × M`. Hyperbola foci placed at primary focus (F1) and system back focus (F2). Standard Cassegrain geometry formulas derive secondary position, size, eccentricity, and semi-major axis from primary focal length, magnification, and back focal distance.
- **Refraction (Snell's law)**: `n1 * sin(θ1) = n2 * sin(θ2)` — exact 2D vector form. Handles total internal reflection (returns None when sin(θ2) > 1). Used for lens surfaces.
- **Spherical lens surfaces**: Two-surface lens model with independent front and back radii of curvature. Supports biconvex, planoconvex, and meniscus configurations. Ray traced through front (air→glass) and back (glass→air) refractions.
- **Cauchy dispersion model**: `n(λ) = B + C/λ²` — wavelength-dependent refractive index for optical glasses. Preset coefficients for BK7 crown and F2 flint glass. Enables chromatic analysis (blue light refracts more than red).
- **Refracting telescope**: Objective lens focuses light directly to focal plane. Zero central obstruction. Lens geometry auto-computed from lensmaker's equation for symmetric biconvex singlet. *Approximation: thin-lens formula R = 2f(n-1) used for initial geometry; thick-lens effects shift focus slightly.*
- **Maksutov-Cassegrain**: Meniscus corrector (refraction through front and back surfaces) + spherical primary (reflection) + aluminized spot on meniscus back surface acting as convex secondary (reflection). The corrector compensates spherical aberration from the spherical primary. Reuses Cassegrain geometry formulas for secondary placement and magnification. *Approximation: near-concentric meniscus formula used for auto-computed front radius; exact aberration correction depends on precise radius matching in real designs.*
- **Vignetting**: Circle-overlap computation for off-axis illumination fraction at the secondary mirror. Beam diameter and shift at the secondary plane computed from geometry. *Approximation: tube wall vignetting not modeled.*

### Wave Optics
- **Airy diffraction pattern**: Point spread function for circular aperture diffraction. Uses `PSF(r) = [2 * J1(x) / x]^2` where `x = pi * D * r / (lambda * f)`. Physically determines the resolution limit of the telescope.
- **Central obstruction diffraction**: Annular aperture PSF accounting for secondary mirror obstruction. Uses `PSF(r) = [1/(1-ε²)]² × [2J₁(x)/x - ε²·2J₁(εx)/(εx)]²` where `ε = D_secondary / D_primary`. Reduces to the standard Airy pattern when ε=0. Produces stronger secondary rings and slightly lower peak intensity compared to an unobstructed aperture.
- **Spider vane diffraction**: 2D FFT-based PSF with pupil mask including spider vane obstructions. Computes `PSF = |FFT(pupil)|²` (Fraunhofer diffraction). Each vane produces a pair of opposing diffraction spikes perpendicular to the vane direction. Validated against analytical Airy when no vanes are present.

### Aberrations
- **Off-axis coma (Seidel 3rd order)**: Tangential coma `C_T(h) = 3θh²/(2R²)`, sagittal `C_S = C_T/3`. Produces the classic comet/fan pattern for off-axis sources. Includes RMS computation, coma-free field calculation, and 2D spot diagrams. *Approximation: Seidel 3rd-order — valid for small field angles.*

### Image Formation
- **Focal plane imaging**: Geometric ray positions convolved with diffraction PSF to produce simulated images. Supports both analytical Airy and FFT-based PSF kernels (the latter when spider vanes are present).
- **Adaptive resolution**: Image resolution automatically scales to resolve the telescope's diffraction limit or atmospheric seeing (whichever is larger), with ~3 pixels per resolution element. Capped at source texture resolution (2048 for Moon) or 4096 hard ceiling.

### Atmospheric
- **Atmospheric seeing**: Gaussian blurring of the focal-plane image with configurable FWHM. Presets: "excellent" (0.8"), "good" (1.5"), "average" (2.5"), "poor" (4.0"). *Approximation: Gaussian profile; real seeing follows Moffat/Kolmogorov profile with broader wings.*

### Visual Observing
- **Eyepiece model**: Computes magnification (f_telescope / f_eyepiece), true field of view (AFOV / magnification), and exit pupil (aperture / magnification). Crops/pads the rendered image to the eyepiece's TFOV. Produces a "true angular size" figure scaled to match the apparent size at 50cm viewing distance. *Note: the eyepiece does not modify the PSF — the image is formed at the focal plane before the eyepiece. This is a geometric/field-of-view model, not a ray-traced optical element.*
- **Exit pupil brightness / washout**: At low magnification (large exit pupil), bright extended objects appear washed out with reduced contrast and color saturation. Uses a sigmoid model: washout ≈ 0 at exit pupil ≤ 1.5mm (ideal planetary viewing), ramps up through 3mm, saturates near 1.0 at ≥ 5mm. Reduces contrast (blend toward mean) and desaturates (blend RGB toward luminance). Applied only to extended sources (planets, Moon) when an eyepiece is configured. *Approximations: (1) sigmoid coefficients (midpoint=3mm, steepness=1.5) are empirical, not derived from psychophysical calibration; (2) saturation reduction factor (0.8 at full washout) is aggressive — real desaturation varies by individual; (3) no surface-brightness dependence — a dim nebula is treated the same as bright Jupiter at equal exit pupil; (4) no Purkinje shift — dark-adapted scotopic color sensitivity (blue shift at low light) is not modeled.*


## Not Yet Implemented

### Geometric Optics
- **Chromatic aberration visualization** — multi-wavelength tracing through lenses to show color fringing
- **Achromatic doublet** — crown + flint glass combination to cancel chromatic aberration
- **Conic sections beyond implemented** — elliptical mirrors (for Ritchey-Chrétien designs and other advanced configurations)
- **Surface errors** — real mirrors have manufacturing imperfections (wavefront error from surface figure)

### Wave Optics
- **Chromatic PSF** — wavelength-dependent diffraction pattern (polychromatic imaging)
- **Wavefront error** — phase errors from imperfect optics, Zernike polynomial decomposition
- **Interference and coherence effects**

### Atmospheric
- **Atmospheric refraction** — bending of light through the atmosphere
- **Atmospheric extinction** — dimming of light through the atmosphere
- **Sky background brightness** — light pollution / sky glow reducing contrast on extended objects
- **Kolmogorov/Moffat seeing profile** — current Gaussian model lacks the broader wings of real turbulence; a Moffat or Kolmogorov profile would give more realistic contrast transfer (MTF)

### Brightness & Visual Perception
- **Surface brightness vs magnification** — extended object surface brightness drops as magnification increases (same light spread over more apparent area). At extreme magnification, objects dim and lose color saturation.
- **Eye adaptation** — dark-adapted eye has different color sensitivity (Purkinje shift). Bright objects partially light-adapt the eye, changing perceived color and contrast.
- **Human eye resolution limit** — the eye resolves ~1 arcminute. At low magnification, telescope-resolved detail below this threshold is lost.

### Eyepiece Optics
- **Chromatic aberration (eyepiece)** — eyepiece lenses introduce wavelength-dependent focus shift and color fringing, especially in simple designs (Plössl). Apochromatic designs reduce this.
- **Ray-traced eyepiece model** — current eyepiece is geometric (magnification/FOV only). A ray-traced model would capture field curvature, astigmatism, distortion, and edge-of-field aberrations.

### Extended Sources
- **Real-time data integration** — linking to actual astronomical data for source definitions
- **Deep-sky objects** — nebulae, galaxies, star clusters

### Detector
- **Pixel sampling** — finite detector pixel size
- **Noise** — photon noise, read noise, dark current
- **Quantum efficiency** — wavelength-dependent detector sensitivity
