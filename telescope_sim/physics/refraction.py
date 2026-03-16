"""Refraction physics for optical surfaces (Snell's law)."""

import numpy as np


# Cauchy equation coefficients for common optical glasses.
# n(λ) = B + C / λ²  where λ is in nanometers.
GLASS_CATALOG = {
    "BK7": {"B": 1.5046, "C": 4200.0},   # borosilicate crown glass
    "F2":  {"B": 1.6032, "C": 9500.0},    # dense flint glass
    # ED (Extra-low Dispersion) glasses for APO refractors
    "FPL51": {"B": 1.4969, "C": 2800.0},  # fluorite phosphate crown (low dispersion)
    "FPL53": {"B": 1.4387, "C": 2100.0},  # special fluorite phosphate (ultra-low dispersion)
    "S-FPL51": {"B": 1.4964, "C": 2750.0},  # Ohara equivalent to FPL51
}


def refractive_index_cauchy(wavelength_nm: float, B: float, C: float) -> float:
    """Compute refractive index using the Cauchy dispersion equation.

    n(λ) = B + C / λ²

    Args:
        wavelength_nm: Wavelength of light in nanometers.
        B: Cauchy B coefficient (approximate index at long wavelength).
        C: Cauchy C coefficient (nm², controls dispersion strength).

    Returns:
        Refractive index at the given wavelength.
    """
    return B + C / (wavelength_nm ** 2)


def refract_direction(incoming_direction: np.ndarray,
                      surface_normal: np.ndarray,
                      n1: float, n2: float) -> np.ndarray | None:
    """Compute the refracted direction using Snell's law in 2D.

    n1 * sin(θ1) = n2 * sin(θ2)

    Args:
        incoming_direction: Unit vector of the incoming ray direction.
        surface_normal: Unit vector normal to the surface at the
                        point of incidence.
        n1: Refractive index of the medium the ray is coming from.
        n2: Refractive index of the medium the ray is entering.

    Returns:
        Unit vector of the refracted direction, or None if total
        internal reflection occurs.
    """
    d = np.asarray(incoming_direction, dtype=float)
    n = np.asarray(surface_normal, dtype=float)
    n = n / np.linalg.norm(n)

    # Ensure normal points toward the incoming ray (into the surface
    # the ray is arriving from), same convention as reflect_direction.
    cos_i = np.dot(d, n)
    if cos_i > 0:
        n = -n
        cos_i = -cos_i

    # cos_i is now negative (angle between incoming ray and normal > 90°
    # because the ray travels *toward* the surface).  We need |cos θ1|.
    cos_theta1 = -cos_i
    ratio = n1 / n2
    sin_theta2_sq = ratio ** 2 * (1.0 - cos_theta1 ** 2)

    # Total internal reflection check
    if sin_theta2_sq > 1.0:
        return None

    cos_theta2 = np.sqrt(1.0 - sin_theta2_sq)

    # Snell's law vector form:
    # d_refracted = ratio * d + (ratio * cos_theta1 - cos_theta2) * n
    refracted = ratio * d + (ratio * cos_theta1 - cos_theta2) * n
    return refracted / np.linalg.norm(refracted)
