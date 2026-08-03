"""Spectrum → RGB colour science (CIE 1931 2° observer, linear sRGB).

Why this module exists
----------------------
The polychromatic star renderer used to sample exactly three wavelengths
(656.3 / 550.0 / 486.1 nm) and pour each one into a single RGB channel, 1:1.
A star does not emit three spectral lines — it emits a continuum — and
collapsing that continuum onto three deltas is what over-saturated the output.

Concretely: focus a fast singlet at 550 nm and only the 550 nm delta is sharp,
while 486 and 656 nm spread into disks ~10,000× dimmer at the core. All the
light in between (500-540 nm and 560-640 nm, which is barely defocused and
therefore nearly as sharp as the focus wavelength) was simply absent from the
model. The result was a core containing one delta's worth of light in one
channel: **pure green, hue exactly 120°, with R and B numerically zero**, for
every star regardless of its spectral type.

Note that this is *not* fixed by mapping each wavelength through the colour
matching functions alone. Monochromatic 550 nm light lies outside the sRGB
gamut and clips to pure green there too. What fixes it is sampling the
continuum: with bands at 517, 550 and 583 nm all near focus, the core receives
green *and* red-weighted light, and the star's own colour survives.

See `spectral_bands`.

Conventions
-----------
* Wavelengths in nanometres.
* All RGB returned by this module is **linear** sRGB (no gamma / transfer
  function applied). The renderer applies its own display stretch downstream,
  so encoding gamma here would apply it twice.
* Out-of-gamut spectral colours (saturated violets and cyans lie outside the
  sRGB triangle) yield negative channel values; these are clipped to zero,
  which is the standard practical choice when rendering monochromatic light.
"""

from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------------------
# CIE 1931 2° standard observer colour-matching functions, 10 nm steps.
# Columns: wavelength_nm, x_bar, y_bar, z_bar.
# ---------------------------------------------------------------------------
_CIE_1931_2DEG = np.array([
    [380, 0.001368, 0.000039, 0.006450],
    [390, 0.004243, 0.000120, 0.020050],
    [400, 0.014310, 0.000396, 0.067850],
    [410, 0.043510, 0.001210, 0.207400],
    [420, 0.134380, 0.004000, 0.645600],
    [430, 0.283900, 0.011600, 1.385600],
    [440, 0.348280, 0.023000, 1.747060],
    [450, 0.336200, 0.038000, 1.772110],
    [460, 0.290800, 0.060000, 1.669200],
    [470, 0.195360, 0.090980, 1.287640],
    [480, 0.095640, 0.139020, 0.812950],
    [490, 0.032010, 0.208020, 0.465180],
    [500, 0.004900, 0.323000, 0.272000],
    [510, 0.009300, 0.503000, 0.158200],
    [520, 0.063270, 0.710000, 0.078250],
    [530, 0.165500, 0.862000, 0.042160],
    [540, 0.290400, 0.954000, 0.020300],
    [550, 0.433450, 0.994950, 0.008750],
    [560, 0.594500, 0.995000, 0.003900],
    [570, 0.762100, 0.952000, 0.002100],
    [580, 0.916300, 0.870000, 0.001650],
    [590, 1.026300, 0.757000, 0.001100],
    [600, 1.062200, 0.631000, 0.000800],
    [610, 1.002600, 0.503000, 0.000340],
    [620, 0.854450, 0.381000, 0.000190],
    [630, 0.642400, 0.265000, 0.000050],
    [640, 0.447900, 0.175000, 0.000020],
    [650, 0.283500, 0.107000, 0.000000],
    [660, 0.164900, 0.061000, 0.000000],
    [670, 0.087400, 0.032000, 0.000000],
    [680, 0.046770, 0.017000, 0.000000],
    [690, 0.022700, 0.008210, 0.000000],
    [700, 0.011359, 0.004102, 0.000000],
    [710, 0.005790, 0.002091, 0.000000],
    [720, 0.002899, 0.001047, 0.000000],
    [730, 0.001440, 0.000520, 0.000000],
    [740, 0.000690, 0.000249, 0.000000],
    [750, 0.000332, 0.000120, 0.000000],
    [760, 0.000166, 0.000060, 0.000000],
    [770, 0.000083, 0.000030, 0.000000],
    [780, 0.000042, 0.000015, 0.000000],
])

CMF_MIN_NM = float(_CIE_1931_2DEG[0, 0])
CMF_MAX_NM = float(_CIE_1931_2DEG[-1, 0])

# Linear-sRGB primaries, D65 white point (IEC 61966-2-1).
XYZ_TO_LINEAR_SRGB = np.array([
    [3.2406, -1.5372, -0.4986],
    [-0.9689, 1.8758, 0.0415],
    [0.0557, -0.2040, 1.0570],
])

# Physical constants (SI) for Planck's law.
_PLANCK_H = 6.62607015e-34      # J s
_LIGHT_C = 2.99792458e8         # m / s
_BOLTZMANN_K = 1.380649e-23     # J / K

# Default spectral sampling for the renderer. Nine bands across 400-700 nm
# keeps the per-band chromatic defocus meaningfully different while costing
# less than the old 3-channel path did, because the kernels are now computed
# once per band instead of once per band *per star*.
DEFAULT_N_BANDS = 9
DEFAULT_LAMBDA_MIN_NM = 400.0
DEFAULT_LAMBDA_MAX_NM = 700.0


def cie_xyz_at(wavelength_nm):
    """CIE 1931 2° colour-matching function values at given wavelengths.

    Linearly interpolated from the 10 nm table; zero outside 380-780 nm.

    Args:
        wavelength_nm: Scalar or array of wavelengths in nm.

    Returns:
        Array of shape (..., 3) holding (x_bar, y_bar, z_bar).
    """
    wl = np.atleast_1d(np.asarray(wavelength_nm, dtype=float))
    table_wl = _CIE_1931_2DEG[:, 0]
    out = np.stack([
        np.interp(wl, table_wl, _CIE_1931_2DEG[:, i], left=0.0, right=0.0)
        for i in (1, 2, 3)
    ], axis=-1)
    if np.ndim(wavelength_nm) == 0:
        return out[0]
    return out


def planck_spectral_radiance(wavelength_nm, temperature_k: float):
    """Planck blackbody spectral radiance B_lambda, per unit wavelength.

    Returned in SI (W m^-3 sr^-1). Only the *shape* matters for colour, but
    the absolute form is kept so the function is reusable as real physics.

    Args:
        wavelength_nm: Scalar or array of wavelengths in nm.
        temperature_k: Blackbody temperature in kelvin.

    Returns:
        Spectral radiance, same shape as `wavelength_nm`.
    """
    wl_m = np.asarray(wavelength_nm, dtype=float) * 1e-9
    if temperature_k <= 0:
        return np.zeros_like(wl_m)
    # exponent can overflow for short wavelengths / cool sources; clip it.
    x = np.clip(_PLANCK_H * _LIGHT_C / (wl_m * _BOLTZMANN_K * temperature_k),
                0.0, 700.0)
    return (2.0 * _PLANCK_H * _LIGHT_C ** 2 / wl_m ** 5) / np.expm1(x)


def xyz_to_linear_srgb(xyz, clip_negative: bool = True):
    """Convert CIE XYZ to linear sRGB.

    Args:
        xyz: Array of shape (..., 3).
        clip_negative: Clip out-of-gamut negative channels to zero. Spectral
            (monochromatic) colours are outside the sRGB triangle, so this is
            the norm when rendering them.

    Returns:
        Linear-sRGB array of shape (..., 3).
    """
    rgb = np.asarray(xyz, dtype=float) @ XYZ_TO_LINEAR_SRGB.T
    if clip_negative:
        rgb = np.maximum(rgb, 0.0)
    return rgb


def spectral_bands(n_bands: int = DEFAULT_N_BANDS,
                   lambda_min_nm: float = DEFAULT_LAMBDA_MIN_NM,
                   lambda_max_nm: float = DEFAULT_LAMBDA_MAX_NM,
                   samples_per_band: int = 16):
    """Split the visible band into `n_bands` and give each an RGB weight.

    Each band is integrated against the CIE colour-matching functions and
    converted to linear sRGB, so `rgb_weights[i]` is the colour produced by
    unit spectral power arriving in band `i`.

    The weights are **white-balanced**: each channel column is scaled so that
    a flat (equal-energy) spectrum sums to exactly (1, 1, 1). That keeps a
    featureless source neutral grey, which is what the renderer's existing
    "white star" default assumes, and makes any colour in the output
    attributable to the source spectrum or to chromatic aberration rather
    than to the choice of sampling.

    The balance is not cosmetic. sRGB is referenced to D65, so raw integration
    of an equal-energy spectrum comes out warm — about (1.00, 0.79, 0.75).
    Balancing to equal energy re-references the render to illuminant E, which
    puts the neutral point near 5500 K. Sun-like stars therefore render white,
    cooler ones amber and hotter ones blue — the convention astronomers
    actually use when they call the Sun a "yellow" star's reference.

    Args:
        n_bands: Number of bands.
        lambda_min_nm: Lower edge of the sampled range.
        lambda_max_nm: Upper edge of the sampled range.
        samples_per_band: Sub-samples used for the within-band integral.

    Returns:
        (centres_nm, rgb_weights) where `centres_nm` has shape (n_bands,) and
        `rgb_weights` has shape (n_bands, 3).
    """
    if n_bands < 1:
        raise ValueError("n_bands must be >= 1")
    edges = np.linspace(lambda_min_nm, lambda_max_nm, n_bands + 1)
    centres = 0.5 * (edges[:-1] + edges[1:])

    xyz_bands = np.empty((n_bands, 3))
    for i in range(n_bands):
        sub = np.linspace(edges[i], edges[i + 1], samples_per_band)
        # Trapezoidal integral of the CMFs over the band.
        xyz_bands[i] = np.trapezoid(cie_xyz_at(sub), sub, axis=0)

    rgb = xyz_to_linear_srgb(xyz_bands)
    # White-balance: a flat spectrum (all bands equal) must give neutral grey.
    column_sums = rgb.sum(axis=0)
    column_sums[column_sums <= 0] = 1.0
    rgb = rgb / column_sums
    return centres, rgb


def blackbody_linear_srgb(temperature_k: float,
                          n_bands: int = DEFAULT_N_BANDS,
                          lambda_min_nm: float = DEFAULT_LAMBDA_MIN_NM,
                          lambda_max_nm: float = DEFAULT_LAMBDA_MAX_NM):
    """Linear-sRGB colour of a blackbody, normalised so max(channel) == 1.

    Normalising by the peak channel (rather than by luminance) separates
    *colour* from *brightness*: the renderer supplies brightness from the
    star's magnitude, and this supplies only the tint. It matches the
    convention of the hand-tabulated palettes it replaces, whose tuples also
    peak at 1.0.

    Args:
        temperature_k: Effective temperature in kelvin.
        n_bands: Spectral sampling resolution.
        lambda_min_nm: Lower edge of the sampled range.
        lambda_max_nm: Upper edge of the sampled range.

    Returns:
        Length-3 linear-sRGB array with max component 1.0 (zeros if the
        temperature is non-positive).
    """
    centres, rgb_weights = spectral_bands(n_bands, lambda_min_nm,
                                          lambda_max_nm)
    sed = planck_spectral_radiance(centres, temperature_k)
    rgb = sed @ rgb_weights
    peak = float(np.max(rgb))
    if peak <= 0:
        return np.zeros(3)
    return rgb / peak


def band_weights_for_source(centres_nm, rgb_weights,
                            temperature_k: float | None = None,
                            tint_rgb=None):
    """Per-band spectral weights for one source, normalised for the renderer.

    The renderer's brightness convention is that a *perfectly corrected*
    telescope puts the source's brightest channel at the peak set by the
    source's magnitude. So the weights are scaled such that summing every
    band's contribution gives a colour whose largest component is exactly 1.

    Args:
        centres_nm: Band centre wavelengths, shape (n_bands,).
        rgb_weights: Band → linear-sRGB weights, shape (n_bands, 3).
        temperature_k: Blackbody temperature. When given, the band weights
            follow Planck's law — real physics, and the source's colour falls
            out of the integral rather than being asserted.
        tint_rgb: Optional multiplicative linear-RGB tint, used for sources
            that carry a tabulated colour instead of a temperature. Combined
            with a flat spectrum this reproduces the previous behaviour.

    Returns:
        (band_weights, source_rgb) — `band_weights` has shape (n_bands,) and
        `rgb_weights_effective` folded tint has shape (n_bands, 3);
        `source_rgb` is the resulting colour (max component 1.0).
    """
    centres_nm = np.asarray(centres_nm, dtype=float)
    rgb_weights = np.asarray(rgb_weights, dtype=float)

    if temperature_k is not None and temperature_k > 0:
        band_w = planck_spectral_radiance(centres_nm, temperature_k)
    else:
        band_w = np.ones_like(centres_nm)

    effective = rgb_weights.copy()
    if tint_rgb is not None:
        effective = effective * np.asarray(tint_rgb, dtype=float)[None, :]

    source_rgb = band_w @ effective
    peak = float(np.max(source_rgb))
    if peak > 0:
        band_w = band_w / peak
        source_rgb = source_rgb / peak
    return band_w, effective, source_rgb


# ---------------------------------------------------------------------------
# Mesopic (rod/cone) colour vision — EYE VIEW ONLY
# ---------------------------------------------------------------------------
# Flux below which the cones contribute nothing and vision is rod-only, i.e.
# achromatic, expressed as a fraction of the display saturation level. Flux
# above which the cones bleach and the percept whitens, same units.
CONE_THRESHOLD_FLUX = 0.05
CONE_BLEACH_FLUX = 0.5


def mesopic_chroma_gain(flux,
                        cone_threshold: float = CONE_THRESHOLD_FLUX,
                        bleach_level: float = CONE_BLEACH_FLUX):
    """How much of a pixel's colour a dark-adapted eye actually perceives.

    Human colour vision is *band-pass in luminance*, not monotonic:

    * **Too dim** — below roughly 0.005 cd/m² only the rods respond. Rods are
      a single photoreceptor class, so their output carries no colour
      information at all: scotopic vision is genuinely achromatic. This is why
      a faint nebula looks grey through an eyepiece however colourful the
      photograph is, and why only the brightest few stars show an obvious tint
      to the naked eye.
    * **Mid range** — the mesopic zone (~0.005 to ~5 cd/m², CIE 191:2010),
      where cones progressively take over and colour saturation climbs.
    * **Too bright** — cone photopigment bleaches and the percept desaturates
      toward white. This is the familiar whiteout of a brilliant star's core.

    Both limits blend the pixel toward its own luminance (neutral grey of the
    same brightness); only the middle of the range shows full chroma.

    ⚠️ APPROXIMATION — the shape is real, the calibration is not. The renderer
    works in normalised display flux (1.0 = the saturation level), not in
    cd/m², so the two thresholds are anchored by eye rather than derived from
    an absolute retinal illuminance. Both terms are smooth Michaelis-Menten
    saturating curves rather than the CIE mesopic interpolation. Treat the
    *ordering* of effects as physical and the exact crossover flux as a tuned
    display parameter.

    Applies to the eye view only. A detector has no cones: a camera records
    the same chromaticity at any flux until the pixel wells clip, so the
    linear/detector path must not call this.

    Args:
        flux: Linear flux array, normalised so 1.0 is the display saturation
            level (i.e. after division by ``saturation_divisor``).
        cone_threshold: Flux at which cones supply half their full chroma.
        bleach_level: Flux at which bleaching has removed half the chroma.

    Returns:
        Array of gains in [0, 1) to multiply each pixel's departure from its
        own luminance by. 0 = grey, 1 = the source's full colour.
    """
    flux = np.asarray(flux, dtype=float)
    flux = np.maximum(flux, 0.0)
    # Cones switching on: 0 at zero flux → 1 well above threshold.
    cone_on = flux / (flux + max(cone_threshold, 1e-12))
    # Cones bleaching out: 1 at low flux → 0 well above the bleach level.
    bleach_out = max(bleach_level, 1e-12) / (flux + max(bleach_level, 1e-12))
    return cone_on * bleach_out


def apply_mesopic_desaturation(image_rgb,
                               cone_threshold: float = CONE_THRESHOLD_FLUX,
                               bleach_level: float = CONE_BLEACH_FLUX):
    """Blend an RGB image toward grey where the eye could not see colour.

    Thin wrapper over `mesopic_chroma_gain` that computes each pixel's Rec.709
    luminance, evaluates the gain at that luminance, and interpolates between
    grey and the original colour.

    Args:
        image_rgb: (H, W, 3) linear RGB, normalised so 1.0 is the display
            saturation level.
        cone_threshold: See `mesopic_chroma_gain`.
        bleach_level: See `mesopic_chroma_gain`.

    Returns:
        A new (H, W, 3) array; the input is not modified.
    """
    image_rgb = np.asarray(image_rgb, dtype=float)
    lum = (0.2126 * image_rgb[..., 0]
           + 0.7152 * image_rgb[..., 1]
           + 0.0722 * image_rgb[..., 2])
    gain = mesopic_chroma_gain(lum, cone_threshold, bleach_level)
    return lum[..., None] + gain[..., None] * (image_rgb - lum[..., None])
