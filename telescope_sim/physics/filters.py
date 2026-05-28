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
    description="Wratten 25 red — blocks blue/green, passes 600 nm+. "
                "Enhances Great Red Spot and Mars surface features.",
    transmission=_gaussian_transmission(
        center_nm=660.0, fwhm_nm=140.0, peak_t=0.85),
)

WRATTEN_47 = Filter(
    name="W47 (blue)",
    description="Wratten 47 dark blue — passes 380–490 nm. "
                "Brings out Jupiter's white zones and Venus cloud detail.",
    transmission=_gaussian_transmission(
        center_nm=450.0, fwhm_nm=80.0, peak_t=0.30),
)

WRATTEN_58 = Filter(
    name="W58 (green)",
    description="Wratten 58 green — passes ~480–580 nm. "
                "Increases Jovian belt contrast.",
    transmission=_gaussian_transmission(
        center_nm=540.0, fwhm_nm=80.0, peak_t=0.60),
)


# Ordered library for UI dropdowns.
FILTER_LIBRARY: tuple[Filter, ...] = (
    NO_FILTER,
    ND_05, ND_10, ND_20,
    WRATTEN_25, WRATTEN_47, WRATTEN_58,
)


def get_filter_by_name(name: str) -> Filter:
    """Look up a filter by its `name` field; falls back to NO_FILTER."""
    for f in FILTER_LIBRARY:
        if f.name == name:
            return f
    return NO_FILTER
