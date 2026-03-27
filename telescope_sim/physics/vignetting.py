"""Vignetting computation for off-axis light in Newtonian telescopes.

At a non-zero field angle, the converging beam from the primary mirror
arrives at the secondary mirror plane shifted laterally.  The illumination
fraction is the overlap area of the beam circle and the secondary circle,
divided by the beam area.

Approximation: tube wall vignetting is not modeled — only the secondary
mirror intercept is considered.
"""

import numpy as np


def circle_overlap_fraction(r1: float, r2: float, d: float) -> float:
    """Fraction of circle-1's area that overlaps with circle-2.

    Uses the standard circle-circle intersection formula via inverse
    cosines.

    Args:
        r1: Radius of the first circle (the beam).
        r2: Radius of the second circle (the secondary mirror).
        d: Distance between the two circle centers.

    Returns:
        Overlap area divided by the area of circle 1 (0.0 to 1.0).
    """
    if d <= 0:
        # Concentric or overlapping centers: overlap = min circle
        return min(1.0, (r2 / r1) ** 2)

    if d >= r1 + r2:
        # No overlap
        return 0.0

    if d + r1 <= r2:
        # Circle 1 entirely inside circle 2
        return 1.0

    if d + r2 <= r1:
        # Circle 2 entirely inside circle 1
        return (r2 / r1) ** 2

    # General overlap via inverse cosines
    cos_alpha = (d ** 2 + r1 ** 2 - r2 ** 2) / (2.0 * d * r1)
    cos_beta = (d ** 2 + r2 ** 2 - r1 ** 2) / (2.0 * d * r2)

    # Clamp for floating-point safety
    cos_alpha = np.clip(cos_alpha, -1.0, 1.0)
    cos_beta = np.clip(cos_beta, -1.0, 1.0)

    alpha = np.arccos(cos_alpha)
    beta = np.arccos(cos_beta)

    overlap_area = (r1 ** 2 * (alpha - np.sin(alpha) * np.cos(alpha))
                    + r2 ** 2 * (beta - np.sin(beta) * np.cos(beta)))

    beam_area = np.pi * r1 ** 2
    return float(overlap_area / beam_area)


def compute_vignetting(field_angle_arcsec, primary_diameter: float,
                       focal_length: float, secondary_offset: float,
                       secondary_minor_axis: float):
    """Compute illumination fraction at a given off-axis field angle.

    The beam from the primary arrives at the secondary plane shifted
    by delta = theta_rad * secondary_offset.  The beam diameter at the
    secondary plane is D_beam = D_primary * (1 - secondary_offset / f).

    NOTE: Tube wall vignetting is not modeled.

    Args:
        field_angle_arcsec: Off-axis angle in arcseconds (scalar or array).
        primary_diameter: Primary mirror diameter in mm.
        focal_length: Focal length of the primary in mm.
        secondary_offset: Distance from primary to secondary along
                          the optical axis in mm.
        secondary_minor_axis: Minor axis of the secondary mirror in mm.

    Returns:
        Illumination fraction (0.0 to 1.0), same shape as input.
    """
    field_angle_arcsec = np.asarray(field_angle_arcsec, dtype=float)
    scalar_input = field_angle_arcsec.ndim == 0
    field_angle_arcsec = np.atleast_1d(field_angle_arcsec)

    theta_rad = field_angle_arcsec / 206265.0

    # Beam radius at the secondary plane
    beam_diameter = primary_diameter * (1.0 - secondary_offset / focal_length)
    r_beam = beam_diameter / 2.0

    # Secondary mirror radius
    r_sec = secondary_minor_axis / 2.0

    # No secondary mirror means full illumination everywhere
    if r_sec <= 0:
        if scalar_input:
            return 1.0
        return np.ones_like(field_angle_arcsec)

    # Lateral shift of the beam center at the secondary plane
    delta = np.abs(theta_rad) * secondary_offset

    result = np.empty_like(field_angle_arcsec)
    for i, d in enumerate(delta):
        result[i] = circle_overlap_fraction(r_beam, r_sec, d)

    if scalar_input:
        return float(result[0])
    return result


def fully_illuminated_field(primary_diameter: float, focal_length: float,
                            secondary_offset: float,
                            secondary_minor_axis: float) -> float:
    """Field angle (arcsec) where vignetting begins.

    Below this angle the beam from the primary fits entirely within the
    secondary mirror.  Above it, light is lost.

    Args:
        primary_diameter: Primary mirror diameter in mm.
        focal_length: Focal length of the primary in mm.
        secondary_offset: Distance from primary to secondary in mm.
        secondary_minor_axis: Minor axis of the secondary mirror in mm.

    Returns:
        Field angle in arcseconds where illumination first drops below 1.0.
    """
    beam_diameter = primary_diameter * (1.0 - secondary_offset / focal_length)
    r_beam = beam_diameter / 2.0
    r_sec = secondary_minor_axis / 2.0

    # Beam fits inside secondary when: d + r_beam <= r_sec
    # i.e. d_max = r_sec - r_beam
    d_max = r_sec - r_beam
    if d_max <= 0:
        # Secondary is smaller than the beam even on-axis
        return 0.0

    theta_rad = d_max / secondary_offset
    return float(theta_rad * 206265.0)
