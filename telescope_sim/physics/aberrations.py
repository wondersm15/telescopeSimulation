"""Off-axis aberration formulas for Newtonian telescopes.

Implements third-order Seidel coma for a parabolic primary mirror.
Coma is the dominant off-axis aberration in Newtonian telescopes and
determines the usable field of view.

Approximation: Seidel 3rd-order approximation — valid for small field
angles (typically < a few arcminutes).
"""

import numpy as np


def compute_coma_spot(field_angle_arcsec: float, focal_length: float,
                      primary_diameter: float,
                      obstruction_ratio: float = 0.0,
                      num_pupil_zones: int = 50,
                      num_azimuthal: int = 72):
    """Compute 2D coma spot positions at the focal plane.

    For a parabolic primary at field angle theta, third-order Seidel coma
    gives the transverse displacement at the focal plane:

        C_s(h) = theta * h^2 / (4 * f)     (sagittal coefficient)

    The spot pattern at pupil coords (h, phi) is:
        x = C_s * (2 + cos(2*phi))         (tangential direction)
        y = C_s * sin(2*phi)               (sagittal direction)

    Tangential extent = 3*C_s, sagittal extent = 2*C_s.
    This traces the classic comet/fan pattern.

    Args:
        field_angle_arcsec: Off-axis angle in arcseconds.
        focal_length: Focal length of the primary in mm.
        primary_diameter: Primary mirror diameter in mm.
        obstruction_ratio: Central obstruction ratio (0.0 to <1.0).
        num_pupil_zones: Number of radial zones across the pupil.
        num_azimuthal: Number of azimuthal samples per zone.

    Returns:
        Tuple of (x_offsets, y_offsets) arrays in mm, each of shape
        (num_pupil_zones * num_azimuthal,).
    """
    theta_rad = field_angle_arcsec / 206265.0

    r_max = primary_diameter / 2.0
    r_min = r_max * obstruction_ratio

    h_values = np.linspace(r_min, r_max, num_pupil_zones, endpoint=True)
    phi_values = np.linspace(0, 2.0 * np.pi, num_azimuthal, endpoint=False)

    # Create meshgrid of (h, phi)
    hh, pp = np.meshgrid(h_values, phi_values)
    hh = hh.ravel()
    pp = pp.ravel()

    # Seidel coma: sagittal coma coefficient for transverse displacement
    # at the focal plane.  For a parabolic Newtonian:
    #   C_s(h) = theta * h^2 / (4 * f)
    # The full spot pattern is:
    #   x = C_s * (2 + cos(2*phi))    (tangential direction)
    #   y = C_s * sin(2*phi)           (sagittal direction)
    # Tangential extent = 3 * C_s (at phi=0), sagittal extent = 2 * C_s.
    C_s = theta_rad * hh ** 2 / (4.0 * focal_length)

    # Focal plane positions
    x_offsets = C_s * (2.0 + np.cos(2.0 * pp))
    y_offsets = C_s * np.sin(2.0 * pp)

    return x_offsets, y_offsets


def compute_coma_rms(field_angle_arcsec: float, focal_length: float,
                     primary_diameter: float,
                     obstruction_ratio: float = 0.0) -> float:
    """RMS coma radius at the focal plane.

    Analytically derived from the Seidel coma formula integrated over
    the pupil.

    Args:
        field_angle_arcsec: Off-axis angle in arcseconds.
        focal_length: Focal length of the primary in mm.
        primary_diameter: Primary mirror diameter in mm.
        obstruction_ratio: Central obstruction ratio.

    Returns:
        RMS coma radius in mm.
    """
    theta_rad = field_angle_arcsec / 206265.0
    R = 2.0 * focal_length
    r_max = primary_diameter / 2.0

    # For a filled circular pupil (no obstruction), the RMS coma is:
    # sigma = (3 * theta * r_max^2) / (2 * R^2) * sqrt(1/4.5)
    # With obstruction ratio eps, the effective r_max is reduced.
    # We use numerical computation via spot for accuracy.
    if abs(theta_rad) < 1e-15:
        return 0.0

    x_off, y_off = compute_coma_spot(field_angle_arcsec, focal_length,
                                     primary_diameter, obstruction_ratio,
                                     num_pupil_zones=100,
                                     num_azimuthal=144)
    r = np.sqrt(x_off ** 2 + y_off ** 2)
    return float(np.sqrt(np.mean(r ** 2)))


def coma_free_field(focal_length: float, primary_diameter: float,
                    wavelength_mm: float) -> float:
    """Field angle (arcsec) where RMS coma equals the Airy radius.

    Below this angle, the telescope is effectively diffraction-limited
    (coma is smaller than the Airy disk).  This defines the usable
    field of view for critical imaging.

    Args:
        focal_length: Focal length of the primary in mm.
        primary_diameter: Primary mirror diameter in mm.
        wavelength_mm: Wavelength of light in mm.

    Returns:
        Field angle in arcseconds.
    """
    f_ratio = focal_length / primary_diameter
    airy_radius = 1.22 * wavelength_mm * f_ratio

    # Binary search for the field angle where RMS coma = airy_radius
    lo, hi = 0.0, 3600.0  # 0 to 1 degree
    for _ in range(60):
        mid = (lo + hi) / 2.0
        rms = compute_coma_rms(mid, focal_length, primary_diameter)
        if rms < airy_radius:
            lo = mid
        else:
            hi = mid

    return (lo + hi) / 2.0
