"""Local theory computations for the Tutorial & Testing tab.

NOTE: These functions compute theoretical predictions for educational comparison
purposes. They are NOT part of the telescope_sim physics engine and should not
be used for telescope design. They live here in the tutorial tab code deliberately.

Each function returns a dict with at minimum:
    theory_value: float   — the primary scalar to compare against simulation
    label: str            — display label (e.g. "Airy radius")
    unit: str             — display unit (e.g. "arcsec")
    formula: str          — human-readable formula string
and optionally additional keys for richer display.
"""

from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Ellipse


# ---------------------------------------------------------------------------
# Act 1 — Isolated Effects
# ---------------------------------------------------------------------------

def compute_airy_disk_theory(telescope, wavelength_nm: float = 550.0) -> dict:
    """Theoretical Airy disk first-dark-ring radius.

    Formula: theta = 1.22 * lambda / D  (unobstructed circular aperture)
    """
    wavelength_m = wavelength_nm * 1e-9
    aperture_m = telescope.primary_diameter * 1e-3
    theta_rad = 1.22 * wavelength_m / aperture_m
    theta_arcsec = theta_rad * 206265.0
    return {
        "theory_value": theta_arcsec,
        "label": "Airy radius",
        "unit": "arcsec",
        "formula": "\u03b8 = 1.22\u03bb/D",
    }


def overlay_airy_ring(fig: Figure, airy_radius_arcsec: float) -> None:
    """Draw a dashed cyan circle at the theoretical Airy radius on a 2D PSF plot.

    The figure axes are assumed to be in arcseconds (as produced by plot_psf_2d).
    """
    if not fig.axes:
        return
    ax = fig.axes[0]
    circle = Circle(
        (0.0, 0.0), airy_radius_arcsec,
        fill=False, color="cyan", linestyle="--",
        linewidth=1.5, alpha=0.85,
        label=f"Theory: {airy_radius_arcsec:.3f}\"",
        transform=ax.transData,
    )
    ax.add_patch(circle)
    ax.legend(loc="upper right", fontsize=7, framealpha=0.6)


def compute_rayleigh_theory(telescope, wavelength_nm: float = 550.0) -> dict:
    """Theoretical Rayleigh resolution limit (angular separation).

    Formula: theta_R = 1.22 * lambda / D
    """
    wavelength_m = wavelength_nm * 1e-9
    aperture_m = telescope.primary_diameter * 1e-3
    theta_arcsec = 1.22 * wavelength_m / aperture_m * 206265.0
    return {
        "theory_value": theta_arcsec,
        "label": "Rayleigh limit",
        "unit": "arcsec",
        "formula": "\u03b8\u1d36 = 1.22\u03bb/D",
    }


def compute_central_obstruction_theory(telescope,
                                        obstruction_ratio: float | None = None,
                                        wavelength_nm: float = 550.0) -> dict:
    """Theoretical Strehl ratio reduction from central obstruction.

    Formula: Strehl \u2248 (1 - \u03b5\u00b2)\u00b2  (annular aperture, Maréchal approximation)

    Args:
        telescope: Telescope object (obstruction_ratio read from it if not supplied).
        obstruction_ratio: Override obstruction ratio (0-1). If None, uses telescope value.
    """
    eps = obstruction_ratio if obstruction_ratio is not None else telescope.obstruction_ratio
    strehl = (1.0 - eps ** 2) ** 2
    return {
        "theory_value": strehl,
        "label": "Strehl ratio",
        "unit": "",
        "formula": "S \u2248 (1 \u2212 \u03b5\u00b2)\u00b2",
        "obstruction_ratio": eps,
    }


def compute_vignetting_theory(telescope) -> dict:
    """Fully-illuminated field radius — angle where vignetting begins.

    Beyond this angle, the converging beam from the primary is clipped by
    the secondary mirror, reducing illumination toward the field edge.
    """
    fif_arcsec = telescope.fully_illuminated_field()
    return {
        "theory_value": fif_arcsec,
        "label": "Fully illuminated field",
        "unit": "arcsec",
        "formula": "θ_fif = (r_sec − r_beam) / d_sec × 206265",
    }


# ---------------------------------------------------------------------------
# Act 2 — Compounding Effects
# ---------------------------------------------------------------------------

def compute_aperture_vs_seeing_theory(telescope,
                                       seeing_arcsec: float = 2.5,
                                       wavelength_nm: float = 550.0) -> dict:
    """Critical aperture where diffraction limit equals atmospheric seeing.

    Formula: D_crit = 1.22 * lambda / theta_seeing

    For apertures smaller than D_crit: diffraction-limited.
    For apertures larger than D_crit: seeing-limited (atmosphere dominates).
    """
    wavelength_m = wavelength_nm * 1e-9
    aperture_m = telescope.primary_diameter * 1e-3

    if seeing_arcsec and seeing_arcsec > 0:
        seeing_rad = seeing_arcsec / 206265.0
        d_crit_mm = 1.22 * wavelength_m / seeing_rad * 1000.0
    else:
        d_crit_mm = 0.0

    diff_limit_arcsec = 1.22 * wavelength_m / aperture_m * 206265.0
    effective_arcsec = max(diff_limit_arcsec, seeing_arcsec or 0.0)
    is_seeing_limited = (seeing_arcsec or 0.0) > diff_limit_arcsec

    return {
        "theory_value": effective_arcsec,
        "label": "Effective resolution",
        "unit": "arcsec",
        "formula": "D\u2099\u1d63\u1d62\u209c = 1.22\u03bb/\u03b8\u209b\u1d49\u1d49",
        "critical_aperture_mm": d_crit_mm,
        "diffraction_limit_arcsec": diff_limit_arcsec,
        "is_seeing_limited": is_seeing_limited,
    }


def compute_coma_fratio_theory(telescope, wavelength_nm: float = 550.0) -> dict:
    """Coma-free field radius, scaling with f-ratio squared.

    Delegates to the existing coma_free_field() function in telescope_sim.
    This wrapper keeps the call site consistent with other theory functions.
    """
    from telescope_sim.physics.aberrations import coma_free_field
    wavelength_mm = wavelength_nm * 1e-6
    cff_arcsec = coma_free_field(
        telescope.focal_length,
        telescope.primary_diameter,
        wavelength_mm,
    )
    f_ratio = telescope.focal_length / telescope.primary_diameter
    return {
        "theory_value": cff_arcsec,
        "label": "Coma-free field radius",
        "unit": "arcsec",
        "formula": "CFF \u221d f\u00b2",
        "f_ratio": f_ratio,
    }


def compute_spherical_aberration_theory(telescope,
                                         wavelength_nm: float = 550.0) -> dict:
    """Geometric transverse spherical aberration blur radius for a spherical mirror.

    For a perfect sphere, marginal rays focus short of the paraxial focus.
    The geometric blur radius at the paraxial focus is:

        r_blur = D³ / (128 · f²)  [mm]

    Converting to angular extent:

        θ = r_blur · 206265 / f = D³ · 206265 / (128 · f³)  [arcsec]

    Note: parabolic primaries have zero spherical aberration (returns 0).
    Airy radius shown for comparison: θ_Airy = 1.22 · λ / D.
    """
    primary_type = getattr(telescope, 'primary_type', 'parabolic')
    f = telescope.focal_length
    D = telescope.primary_diameter

    if primary_type != 'spherical':
        return {
            "theory_value": 0.0,
            "label": "SA blur radius",
            "unit": "arcsec",
            "formula": "Parabolic: SA = 0",
        }

    r_blur_mm = D ** 3 / (128.0 * f ** 2)
    theta_arcsec = r_blur_mm * 206265.0 / f
    return {
        "theory_value": theta_arcsec,
        "label": "SA blur radius",
        "unit": "arcsec",
        "formula": "r = D³/(128f²)",
    }


# ---------------------------------------------------------------------------
# Registry — maps scenario theory_function names to callables
# ---------------------------------------------------------------------------

THEORY_FUNCTIONS: dict[str, callable] = {
    "compute_airy_disk_theory": compute_airy_disk_theory,
    "compute_rayleigh_theory": compute_rayleigh_theory,
    "compute_central_obstruction_theory": compute_central_obstruction_theory,
    "compute_vignetting_theory": compute_vignetting_theory,
    "compute_aperture_vs_seeing_theory": compute_aperture_vs_seeing_theory,
    "compute_coma_fratio_theory": compute_coma_fratio_theory,
    "compute_spherical_aberration_theory": compute_spherical_aberration_theory,
}

# Maps scenario ids to their figure overlay functions (called after plot, before set_figure)
OVERLAY_FUNCTIONS: dict[str, callable] = {
    "airy_disk": overlay_airy_ring,
}
