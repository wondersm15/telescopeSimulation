"""Optical filters: ND (neutral density) and colour (Wratten) types.

A filter is a function T(λ) returning transmission ∈ [0, 1]. The
renderer multiplies per-wavelength flux by T(λ) before saturation
clipping, so filters genuinely reduce collected photons (dimming
bright targets, reducing detector saturation) and shift colour balance.

For polychromatic rendering, each filter pre-computes per-channel
transmission averages T_R, T_G, T_B over the R/G/B response bands at
656.3, 550.0, 486.1 nm respectively (Fraunhofer C, "design", and F
lines). Monochromatic rendering uses T(λ) at the rendering wavelength.

Wratten transmission curves are tabulated from Kodak's published
specifications (Tiffen reissue). ND filters follow the standard
optical-density definition: T = 10⁻ᵒᵈ.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np


# Channel band centres (nm) — match chromatic rendering in ray_trace_plot.
# These are the Fraunhofer C / "design" / F wavelengths.
CHANNEL_WAVELENGTHS_NM = (656.3, 550.0, 486.1)


@dataclass(frozen=True)
class Filter:
    """A spectral filter with a transmission function.

    Args:
        name: Short identifier (used in UI dropdowns and titles).
        description: Human-readable purpose (shown in tooltips).
        transmission: Callable T(wavelength_nm) → transmission in [0, 1].
    """
    name: str
    description: str
    transmission: Callable[[float], float]

    def channel_transmissions(self) -> tuple[float, float, float]:
        """Pre-computed (T_R, T_G, T_B) using the channel band centres.

        This is a simple point-sampling at the channel wavelength. A
        more accurate model would integrate T(λ) over each detector
        response band — for the tutorial application the difference is
        negligible.
        """
        return tuple(float(self.transmission(wl))
                     for wl in CHANNEL_WAVELENGTHS_NM)  # type: ignore[return-value]

    @property
    def luminance_transmission(self) -> float:
        """Single-number transmission for monochromatic / luminance scaling.

        Computed at the design wavelength (550 nm). Used by the
        single-channel image path.
        """
        return float(self.transmission(550.0))


# ── Concrete filters ─────────────────────────────────────────────────

def _flat_transmission(value: float) -> Callable[[float], float]:
    """Wavelength-independent transmission (used for ND filters)."""
    def T(wavelength_nm: float, _v: float = value) -> float:
        return _v
    return T


def _gaussian_transmission(center_nm: float, fwhm_nm: float,
                            peak_t: float) -> Callable[[float], float]:
    """Gaussian-shape transmission centred at `center_nm`.

    Approximates Wratten colour-filter passbands. Real Wratten curves
    aren't perfectly Gaussian (they have asymmetric edges and out-of-
    band leakage), but a Gaussian is close enough for the tutorial.
    """
    sigma = fwhm_nm / 2.355
    def T(wavelength_nm: float,
          _c: float = center_nm,
          _s: float = sigma,
          _p: float = peak_t) -> float:
        return _p * float(np.exp(-((wavelength_nm - _c) ** 2)
                                  / (2.0 * _s ** 2)))
    return T


def _longpass_transmission(cutoff_nm: float, edge_nm: float,
                            peak_t: float) -> Callable[[float], float]:
    """Sharp long-pass (high-pass in wavelength) transmission.

    Blocks short wavelengths and passes everything above `cutoff_nm` via a
    logistic edge of width `edge_nm` (smaller = sharper). This matches real
    Wratten red filters (e.g. W25), which have a steep cut-on near 590 nm
    and pass the whole red tail — NOT a symmetric Gaussian bump, which leaks
    green and makes white targets read orange/yellow.

        T(λ) = peak / (1 + exp(-(λ - cutoff) / edge))
    """
    def T(wavelength_nm: float,
          _c: float = cutoff_nm,
          _e: float = edge_nm,
          _p: float = peak_t) -> float:
        return _p / (1.0 + float(np.exp(-(wavelength_nm - _c) / _e)))
    return T


NO_FILTER = Filter(
    name="None",
    description="No filter — full spectrum, all wavelengths transmitted.",
    transmission=lambda wl: 1.0,
)

ND_05 = Filter(
    name="ND-0.5",
    description="Neutral density 0.5 (32% transmission). "
                "Reduces brightness without colour shift.",
    transmission=_flat_transmission(10 ** -0.5),  # ≈ 0.316
)

ND_10 = Filter(
    name="ND-1.0",
    description="Neutral density 1.0 (10% transmission). "
                "Useful for the Moon at high magnification.",
    transmission=_flat_transmission(10 ** -1.0),  # = 0.100
)

ND_20 = Filter(
    name="ND-2.0",
    description="Neutral density 2.0 (1% transmission). "
                "Heavy stop-down for very bright objects.",
    transmission=_flat_transmission(10 ** -2.0),  # = 0.010
)

# Wratten approximations. Centre/FWHM/peak from published transmission
# curves; gaussian approximation is qualitative.
WRATTEN_25 = Filter(
    name="W25 (red)",
    description="Wratten 25 red — sharp cut-on ~590 nm, passes the whole "
                "red tail (long-pass). On Jupiter it gives a fairly UNIFORM "
                "red disk (zones, belts and the Red Spot all reflect red, so "
                "feature contrast is LOW); its real value is cutting blue haze "
                "/ atmospheric dispersion and darkening blue festoons. Great "
                "on Mars. Blocks blue/green almost completely.",
    # Long-pass, NOT a Gaussian: a real W25 has a steep cut-on near 590 nm
    # and transmits all longer wavelengths. The previous 140 nm Gaussian
    # leaked ~15% green (T_G≈0.15), so white targets read orange/yellow.
    transmission=_longpass_transmission(
        cutoff_nm=595.0, edge_nm=12.0, peak_t=0.90),
)

WRATTEN_47 = Filter(
    name="W47 (blue)",
    description="Wratten 47 DARK blue — passes 380–490 nm at low "
                "transmission, so the image is quite dim. Classic for Venus "
                "cloud detail; for Jupiter the lighter W80A is usually "
                "preferred (brighter, same blue-contrast effect).",
    transmission=_gaussian_transmission(
        center_nm=450.0, fwhm_nm=80.0, peak_t=0.30),
)

WRATTEN_80A = Filter(
    name="W80A (light blue)",
    description="Wratten 80A light blue — passes blue–green at high "
                "transmission. THE Jupiter contrast filter: the belts and "
                "Great Red Spot absorb blue, so they darken against the "
                "blue-reflecting white zones — features 'pop'. Bright enough "
                "to keep the disk clearly visible.",
    # Broad, bright blue-green: T_R≈0.01, T_G≈0.34, T_B≈0.74. Real W80A is a
    # light blue used far more than the dark W47 for planetary contrast.
    transmission=_gaussian_transmission(
        center_nm=475.0, fwhm_nm=140.0, peak_t=0.75),
)

WRATTEN_58 = Filter(
    name="W58 (green)",
    description="Wratten 58 green — passes ~500–570 nm. "
                "Increases Jovian belt contrast (intermediate between the "
                "blue and red extremes).",
    # Narrowed from 80→55 nm FWHM so the blue tail is rejected more
    # cleanly (was T_B≈0.17); a real W58 cuts blue and red hard.
    transmission=_gaussian_transmission(
        center_nm=535.0, fwhm_nm=55.0, peak_t=0.62),
)


# Ordered library for UI dropdowns.
FILTER_LIBRARY: tuple[Filter, ...] = (
    NO_FILTER,
    ND_05, ND_10, ND_20,
    WRATTEN_25, WRATTEN_58, WRATTEN_80A, WRATTEN_47,
)


def get_filter_by_name(name: str) -> Filter:
    """Look up a filter by its `name` field; falls back to NO_FILTER."""
    for f in FILTER_LIBRARY:
        if f.name == name:
            return f
    return NO_FILTER
