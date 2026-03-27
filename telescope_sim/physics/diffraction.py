"""Diffraction PSF computation for circular and annular apertures."""

import numpy as np
from scipy.special import j1


def rayleigh_criterion_arcsec(wavelength_m: float, aperture_m: float,
                              obstruction_ratio: float = 0.0) -> float:
    """Rayleigh criterion angular resolution in arcseconds.

    For an annular aperture with obstruction ratio epsilon, the first
    zero of the diffraction pattern shifts inward, slightly improving
    angular resolution: theta = 1.22 * lambda / D / (1 + epsilon^2).

    Args:
        wavelength_m: Wavelength of light in meters.
        aperture_m: Aperture diameter in meters.
        obstruction_ratio: Central obstruction ratio (0.0 to <1.0).

    Returns:
        Angular resolution in arcseconds.
    """
    base = 1.22 * wavelength_m / aperture_m * 206265
    if obstruction_ratio > 0:
        base *= 1.0 / (1.0 + obstruction_ratio ** 2)
    return base


def compute_psf(r: np.ndarray, aperture_diameter: float,
                focal_length: float,
                wavelength_mm: float,
                obstruction_ratio: float = 0.0) -> np.ndarray:
    """Compute the diffraction PSF for a circular or annular aperture.

    For an unobstructed aperture (epsilon=0):
        PSF(r) = [2 * J1(x) / x]^2

    For an annular aperture (epsilon>0, central obstruction):
        PSF(r) = [1/(1-eps^2)]^2 * [2*J1(x)/x - eps^2 * 2*J1(eps*x)/(eps*x)]^2

    where x = pi * D * r / (lambda * f), eps = D_secondary / D_primary.
    When eps=0 this reduces exactly to the standard Airy pattern.

    Args:
        r: Array of radial distances from center in mm.
        aperture_diameter: Telescope aperture diameter in mm.
        focal_length: Telescope focal length in mm.
        wavelength_mm: Wavelength of light in mm.
        obstruction_ratio: Central obstruction ratio (0.0 to <1.0).

    Returns:
        Normalized intensity array (peak = 1.0).
    """
    x = np.pi * aperture_diameter * r / (wavelength_mm * focal_length)
    eps = obstruction_ratio

    # Compute 2*J1(x)/x, handling x=0 where the limit is 1.0
    jinc = np.ones_like(x)
    nonzero = x != 0
    jinc[nonzero] = 2.0 * j1(x[nonzero]) / x[nonzero]

    if eps < 1e-12:
        # Unobstructed circular aperture
        return jinc ** 2

    # Annular aperture: subtract the contribution of the blocked center
    eps_x = eps * x
    jinc_eps = np.ones_like(x)
    nonzero_eps = eps_x != 0
    jinc_eps[nonzero_eps] = (2.0 * j1(eps_x[nonzero_eps])
                             / eps_x[nonzero_eps])

    amplitude = (jinc - eps ** 2 * jinc_eps) / (1.0 - eps ** 2)
    return amplitude ** 2
