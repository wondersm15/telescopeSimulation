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

    Two complementary numbers describe it:
      angular  \u03b8 = 1.22\u00b7\u03bb/D      [arcsec on sky]
      linear   r = 1.22\u00b7\u03bb\u00b7N      [mm at focal plane,  N = f/D]
    The angular size depends only on aperture and wavelength; the linear
    size also scales with focal length (focal length sets the mm scale
    of the focal plane but NOT the angular resolution).
    """
    wavelength_m = wavelength_nm * 1e-9
    aperture_m = telescope.primary_diameter * 1e-3
    theta_rad = 1.22 * wavelength_m / aperture_m
    theta_arcsec = theta_rad * 206265.0

    # Linear radius at focal plane (mm). f-ratio N = f/D (both mm)
    f_ratio = telescope.focal_length / telescope.primary_diameter
    wavelength_mm = wavelength_nm * 1e-6
    r_focal_mm = 1.22 * wavelength_mm * f_ratio

    formula = (f"\u03b8 = 1.22\u03bb/D = {theta_arcsec:.3f}\" "
               f"|  r = 1.22\u03bbN = {r_focal_mm * 1000:.2f} \u00b5m "
               f"at f/{f_ratio:.1f}\n"
               f"\u03bb = wavelength, D = aperture, N = f-ratio (f/D)")
    return {
        "theory_value": theta_arcsec,
        "label": "Airy radius",
        "unit": "arcsec",
        "formula": formula,
        "airy_radius_mm": r_focal_mm,
    }


def overlay_airy_ring(fig: Figure, airy_radius_arcsec: float) -> None:
    """Draw a dashed cyan circle at the theoretical Airy radius on a 2D PSF plot.

    The figure axes are assumed to be in arcseconds (as produced by plot_psf_2d).
    Skipped for 1D radial-profile plots (x-axis labelled "Radial distance").
    """
    if not fig.axes:
        return
    ax = fig.axes[0]
    if "radial distance" in (ax.get_xlabel() or "").lower():
        return  # 1D radial profile; circle overlay isn't meaningful
    circle = Circle(
        (0.0, 0.0), airy_radius_arcsec,
        fill=False, color="cyan", linestyle="--",
        linewidth=1.5, alpha=0.85,
        label=f"Theory: {airy_radius_arcsec:.3f}\"",
        transform=ax.transData,
    )
    ax.add_patch(circle)
    ax.legend(loc="upper right", fontsize=7, framealpha=0.6)


def overlay_spider_vanes(fig: Figure, telescope) -> None:
    """Draw dashed lines along the spider-vane directions on a 2D PSF plot.

    Each vane is drawn as a thin dashed red line from the origin out to the
    plot edge in its physical pupil-plane direction. Spikes appear in the PSF
    perpendicular to these lines — drawing the vanes themselves makes the
    geometric origin of the spike pattern explicit.
    """
    n = getattr(telescope, "spider_vanes", 0)
    if n <= 0 or not fig.axes:
        return
    ax = fig.axes[0]
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    R = max(abs(xlim[0]), abs(xlim[1]), abs(ylim[0]), abs(ylim[1]))
    R *= 0.95
    for k in range(n):
        # Angles match build_pupil_mask exactly: half-strip vanes at 2πk/N
        # going from origin outward. Diffraction spikes appear PERPENDICULAR
        # to each vane (so vanes at 0°/120°/240° produce spikes at 30°,
        # 90°, 150°, 210°, 270°, 330°).
        angle = 2.0 * k * np.pi / n
        x_end = R * np.cos(angle)
        y_end = R * np.sin(angle)
        ax.plot([0.0, x_end], [0.0, y_end],
                color="red", linestyle=":", linewidth=1.1, alpha=0.75,
                label=("Vane positions (spikes are ⊥)" if k == 0 else None),
                zorder=4)
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles, labels, loc="upper right",
              fontsize=7, framealpha=0.7)


def overlay_resolution_circles(fig: Figure,
                                airy_radius_arcsec: float,
                                seeing_arcsec: float | None = None) -> None:
    """Overlay theoretical resolution circles on a rendered image plot.

    Draws a dashed cyan circle at the diffraction-limited Airy radius and
    (when seeing is active) a dotted orange circle at the seeing FWHM.
    Using FWHM (not FWHM/2) makes the orange circle directly comparable to
    the Airy radius as a resolution threshold — whichever circle is larger
    is the dominant limit on resolution at that aperture and seeing.
    """
    if not fig.axes:
        return
    ax = fig.axes[0]
    drew_any = False
    if airy_radius_arcsec > 0:
        ax.add_patch(Circle(
            (0.0, 0.0), airy_radius_arcsec,
            fill=False, color="cyan", linestyle="--",
            linewidth=1.5, alpha=0.9,
            label=f"Airy radius: {airy_radius_arcsec:.2f}\"",
        ))
        drew_any = True
    if seeing_arcsec is not None and seeing_arcsec > 0:
        ax.add_patch(Circle(
            (0.0, 0.0), seeing_arcsec,
            fill=False, color="orange", linestyle=":",
            linewidth=1.5, alpha=0.9,
            label=f"Seeing FWHM: {seeing_arcsec:.2f}\"",
        ))
        drew_any = True
    # Only build a legend when at least one circle was drawn — otherwise
    # (both limits toggled off, R3.10) matplotlib warns "no artists with
    # labels". The ideal-point case is intentionally circle-free.
    if drew_any:
        ax.legend(loc="upper right", fontsize=7, framealpha=0.7)


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
    """Theoretical Strehl ratio + modified Rayleigh limit from obstruction.

    Two related effects of a central obstruction:
      Strehl reduction:  S ≈ (1 − ε²)²  (Maréchal approximation)
      Modified Airy:     θᴿ(ε) ≈ 1.22λ/D / (1 + ε²)  (annular first-zero)
    The displayed value is the Strehl ratio; the modified Rayleigh
    angle is shown in the formula text and exposed via rayleigh_arcsec.
    """
    eps = obstruction_ratio if obstruction_ratio is not None else telescope.obstruction_ratio
    strehl = (1.0 - eps ** 2) ** 2

    wavelength_m = wavelength_nm * 1e-9
    aperture_m = telescope.primary_diameter * 1e-3
    base_rayleigh = 1.22 * wavelength_m / aperture_m * 206265.0
    modified_rayleigh = base_rayleigh / (1.0 + eps ** 2)

    formula = (
        f"S ≈ (1−ε²)²  |  "
        f"θᴿ(ε)={modified_rayleigh:.3f}″ "
        f"= 1.22λ/D/(1+ε²)\n"
        f"ε = secondary/primary Ø (obstruction ratio); S = Strehl ratio"
    )

    return {
        "theory_value": strehl,
        "label": "Strehl ratio",
        "unit": "",
        "formula": formula,
        "obstruction_ratio": eps,
        "rayleigh_arcsec": modified_rayleigh,
        "rayleigh_unobstructed_arcsec": base_rayleigh,
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

def _spider_overlay(fig: Figure, theory_result: dict, telescope) -> None:
    """Scenario-id wrapper that draws spider-vane direction lines."""
    overlay_spider_vanes(fig, telescope)


def _resolution_overlay(fig: Figure, theory_result: dict, telescope,
                        seeing_arcsec: float | None = None) -> None:
    """Scenario-id wrapper for the aperture-vs-seeing comparison.

    Reads Airy radius from the theory dict and draws the two circles.
    """
    airy = theory_result.get("diffraction_limit_arcsec", 0.0)
    overlay_resolution_circles(fig, airy, seeing_arcsec)


def overlay_tutorial_starfield_markers(fig: Figure, telescope=None) -> None:
    """Overlay small cyan dots at each TutorialStarField star position.

    Without these markers, stars can become sub-pixel after rasterisation
    and disappear from the canvas. The markers are placed at the design
    positions used by `TutorialStarField`: one on-axis star, two close
    resolution pairs, a ring at 33% of field radius, a ring at 75% of
    field radius, and four prominent edge stars at 80% in the cardinal
    diagonals. Cyan dots float on top of the rendered image regardless
    of rasterisation density.
    """
    if not fig.axes:
        return
    ax = fig.axes[0]
    xlabel = (ax.get_xlabel() or "").lower()
    if "field angle" not in xlabel:
        return
    xlim = ax.get_xlim()
    R = max(abs(xlim[0]), abs(xlim[1]))
    # Mirror the design positions in TutorialStarField:
    pair_y = max(R * 0.05, 4.0)
    sep_1 = max(R * 0.008, 0.5)
    sep_2 = max(R * 0.004, 0.25)
    positions = [(0.0, 0.0)]
    positions += [(-sep_1, +pair_y), (+sep_1, +pair_y),
                  (-sep_2, -pair_y), (+sep_2, -pair_y)]
    for k in range(8):
        a = k * np.pi / 4
        positions.append((R * 0.33 * np.cos(a), R * 0.33 * np.sin(a)))
        positions.append((R * 0.75 * np.cos(a), R * 0.75 * np.sin(a)))
    for k in range(4):
        a = k * np.pi / 2 + np.pi / 8
        positions.append((R * 0.80 * np.cos(a), R * 0.80 * np.sin(a)))
    xs = [p[0] for p in positions]
    ys = [p[1] for p in positions]
    ax.scatter(xs, ys, s=10, marker='o', facecolors='none',
               edgecolors='cyan', linewidths=0.8, alpha=0.6, zorder=5,
               label="Star positions")


def _coma_starfield_overlay(fig: Figure, theory_result: dict, telescope) -> None:
    """Label ComaDemoField stars + draw reference circles.

    Two reference circles (both centered on the optical axis):
      - cff (coma-free field): radius = 1.22 λ F² / D, where σ_coma
        equals the Airy radius — the boundary of the "sharp" zone.
      - 10 × cff: where σ_coma is 10× the Airy disk; stars beyond this
        radius show severe comatic blur.

    Plus a minimal angle label above each star (no marker rings, no
    connector arrows) mapping comet-shaped stars to their spot-panel
    titles on the before-side.
    """
    from telescope_sim.source.sources import ComaDemoField
    import numpy as np
    if not fig.axes:
        return
    ax = fig.axes[0]
    xlabel = (ax.get_xlabel() or "").lower()
    if "field angle" not in xlabel:
        return

    # Compute cff = 1.22 λ F² / D, returned in arcsec
    wavelength_mm = 550.0 * 1e-6
    f_ratio = telescope.focal_length / telescope.primary_diameter
    cff_mm = 1.22 * wavelength_mm * f_ratio ** 2
    plate_scale = 206265.0 / telescope.focal_length
    cff_arcsec = cff_mm * plate_scale

    # Draw cff circle
    cff_circle = Circle((0, 0), cff_arcsec, fill=False,
                             edgecolor='cyan', linewidth=1.2,
                             linestyle='-', alpha=0.7, zorder=4)
    ax.add_patch(cff_circle)
    # Place label just outside the cff circle at NE direction
    label_r = cff_arcsec * 1.05
    ax.annotate(f"cff = {cff_arcsec:.1f}″",
                xy=(cff_arcsec * 0.71, cff_arcsec * 0.71),
                xytext=(8, 8), textcoords='offset points',
                fontsize=7, color='cyan')

    # 10× cff
    cff10 = 10.0 * cff_arcsec
    cff10_circle = Circle((0, 0), cff10, fill=False,
                              edgecolor='orange', linewidth=1.2,
                              linestyle='--', alpha=0.7, zorder=4)
    ax.add_patch(cff10_circle)
    ax.annotate(f"10× cff = {cff10:.1f}″",
                xy=(cff10 * 0.71, cff10 * 0.71),
                xytext=(8, 8), textcoords='offset points',
                fontsize=7, color='orange')

    # Minimal angle labels above each star
    ylim = ax.get_ylim()
    y_offset = (ylim[1] - ylim[0]) * 0.04
    for ang in ComaDemoField.DEMO_ANGLES_ARCSEC:
        ax.text(ang, y_offset, f"{int(ang)}″",
                fontsize=8, color="yellow", ha="center", va="bottom",
                zorder=6)


# Maps scenario ids to their figure overlay functions (called after plot, before set_figure).
# Functions may use one of three signatures:
#   (fig, theory_value)                        — legacy 2-arg
#   (fig, theory_result, telescope)            — 3-arg
#   (fig, theory_result, telescope, seeing)    — 4-arg
def _starfield_markers_overlay(fig: Figure, theory_result: dict, telescope) -> None:
    """Marker overlay for StarFieldResolutionField (the source used by the
    starfield_resolution scenario after-side). Without markers stars can
    rasterise sub-pixel against a black background. We draw small cyan
    rings at each star's design position, taken from a freshly-instantiated
    source so the markers always match the rendered positions exactly.
    """
    from telescope_sim.source.sources import StarFieldResolutionField
    if not fig.axes:
        return
    ax = fig.axes[0]
    xlabel = (ax.get_xlabel() or "").lower()
    if "field angle" not in xlabel:
        return
    xlim = ax.get_xlim()
    R = max(abs(xlim[0]), abs(xlim[1]))
    if R <= 0:
        return
    sf = StarFieldResolutionField(field_radius_arcsec=R)
    ax.scatter(sf.star_x_arcsec, sf.star_y_arcsec, s=14,
               marker='o', facecolors='none', edgecolors='cyan',
               linewidths=0.7, alpha=0.5, zorder=5,
               label="Star positions")


def _find_reference_side_panel(fig: Figure, plot_ax):
    """Find the axis-off 'side column' panel (metrics/formulas) in a
    plot_psf_profile figure, so legends/notes can be placed there instead of
    on top of the curves. Returns the rightmost text-only axis, or None.
    """
    candidates = []
    for ax in fig.axes:
        if ax is plot_ax:
            continue
        # The side panel has axis turned off and carries text but no lines.
        has_lines = len(ax.get_lines()) > 0
        axis_off = not ax.axison
        if axis_off and not has_lines:
            candidates.append(ax)
    if not candidates:
        return None
    # Rightmost by axes position (the metrics/formulas column).
    return max(candidates, key=lambda a: a.get_position().x0)


def _obstruction_overlay(fig: Figure, theory_result: dict, telescope,
                         scenario=None) -> None:
    """For central_obstruction in 1D PSF view, plot the comparison curve.

    Color convention is consistent across both sides:
      Unobstructed (ε=0)  →  solid blue
      Obstructed (ε>0)    →  dashed red

    On the BEFORE side (unobstructed telescope) the existing curve is
    already the unobstructed PSF — we just restyle it to solid blue
    and add the obstructed comparison as a dashed red curve, both at
    peak 1.0 (shape comparison, no Strehl scaling).

    On the AFTER side (obstructed telescope) the existing curve is the
    obstructed PSF at peak 1.0 — we scale it down to its Strehl ratio
    (1−ε²)², restyle to dashed red, and add the unobstructed reference
    as solid blue at peak 1.0. The Strehl gap is then visible.
    """
    if not fig.axes:
        return
    import numpy as np
    from telescope_sim.physics.diffraction import compute_psf

    eps_this = (telescope.obstruction_ratio
                if telescope.enable_obstruction else 0.0)
    if eps_this > 0:
        is_before_side = False
        eps_compare = 0.0
        strehl_obs = (1.0 - eps_this ** 2) ** 2
    else:
        is_before_side = True
        if scenario is not None:
            eps_compare = scenario.after_telescope.obstruction_ratio
        else:
            eps_compare = 0.30
        strehl_obs = (1.0 - eps_compare ** 2) ** 2

    for ax in fig.axes:
        xlabel = (ax.get_xlabel() or "").lower()
        if "radial distance" not in xlabel:
            continue
        wavelength_mm = 550.0 * 1e-6
        D = telescope.primary_diameter
        f = telescope.focal_length
        xlim = ax.get_xlim()
        r_max_um = max(abs(xlim[0]), abs(xlim[1]))
        if r_max_um <= 0:
            continue

        # Find the existing plot_psf_profile data line (long ydata, peak
        # near 1.0) and restyle / rescale it consistently.
        for line in ax.get_lines():
            ydata = np.asarray(line.get_ydata(), dtype=float)
            if ydata.size < 50 or not np.isfinite(ydata).any():
                continue
            peak = float(np.nanmax(ydata))
            if abs(peak - 1.0) > 0.02:
                continue
            if is_before_side:
                # Existing curve = unobstructed PSF → solid blue
                line.set_color("blue")
                line.set_linestyle("-")
                line.set_linewidth(2.0)
                line.set_label("Unobstructed (ε=0)")
            else:
                # Existing curve = obstructed PSF → dashed red, scaled
                # to Strehl peak so the peak-intensity loss is visible.
                line.set_ydata(ydata * strehl_obs)
                line.set_color("red")
                line.set_linestyle("--")
                line.set_linewidth(2.0)
                line.set_label(
                    f"Obstructed (ε={eps_this:.2f}, Strehl ≈ {strehl_obs:.3f})"
                )

        # Add the comparison curve in the OTHER color/style.
        r = np.linspace(0, r_max_um * 1e-3, 800)  # mm
        psf_cmp = compute_psf(r, D, f, wavelength_mm, eps_compare)
        if ax.get_yscale() == "log":
            psf_plot = np.clip(psf_cmp, 1e-6, None)
        else:
            psf_plot = psf_cmp
        if is_before_side:
            # On the unobstructed side, the comparison is OBSTRUCTED → red dashed
            ax.plot(r * 1000, psf_plot, color="red", linestyle="--",
                    linewidth=1.5, alpha=0.85,
                    label=f"Obstructed (ε={eps_compare:.2f}) shape")
        else:
            # On the obstructed side, the comparison is UNOBSTRUCTED → solid blue
            ax.plot(r * 1000, psf_plot, color="blue", linestyle="-",
                    linewidth=1.5, alpha=0.85,
                    label="Unobstructed (ε=0) reference")

        # On the AFTER side, shade the Strehl gap.
        if not is_before_side and eps_this > 0:
            ax.axhline(strehl_obs, color="red", linestyle=":",
                       linewidth=1.0, alpha=0.6)
            ax.fill_between([0, r_max_um], strehl_obs, 1.0,
                            color="red", alpha=0.08, zorder=0)

        # R4.3: the per-side NORMALISATION BASIS is the key thing to convey,
        # so make it the PLOT TITLE (was "No/With obstruction"), and fold the
        # blue/red colour key into it — that removes the separate legend
        # entirely, so it blocks neither the curves (R3.5) nor the side-panel
        # formulas (R4.3b). The two sides use DIFFERENT normalisations:
        #   before (unobstructed): each curve to its own peak = 1.0 → SHAPE
        #     comparison (energy pushed from core into rings).
        #   after  (obstructed): obstructed curve scaled to its Strehl
        #     (1−ε²)² vs the unobstructed reference at 1.0 → PEAK-INTENSITY
        #     (Strehl) loss (shaded).
        if ax.get_legend() is not None:
            ax.get_legend().remove()
        # Clear the generic "Point Spread Function" suptitle so it doesn't
        # collide with the per-side normalisation title we set below.
        if getattr(fig, "_suptitle", None) is not None:
            fig.suptitle("")
        if is_before_side:
            ax.set_title(
                "Normalised to each own peak → PSF SHAPE\n"
                "blue = unobstructed · red = obstructed (shape)",
                fontsize=8.5)
        else:
            ax.set_title(
                f"Obstructed scaled to Strehl (1−ε²)² ≈ {strehl_obs:.3f} "
                "→ PEAK-INTENSITY loss\n"
                "red = obstructed · blue = unobstructed reference "
                "(shaded = Strehl gap)",
                fontsize=8.5)


def _chromatic_star_labels_overlay(fig: Figure, theory_result: dict,
                                    telescope, scenario=None,
                                    side: str = "after") -> None:
    """Label MultiColorStarField stars on the BEFORE side with their
    spectral class and characteristic temperature (K and eV).

    Only renders on the before side — the after side is left clean so
    the user can compare a labelled reference against the live
    objective/seeing/view changes.
    """
    if side != "before":
        return
    from telescope_sim.source.sources import MultiColorStarField
    if not fig.axes:
        return
    ax = fig.axes[0]
    xlabel = (ax.get_xlabel() or "").lower()
    if "field angle" not in xlabel:
        return
    sf = MultiColorStarField()
    K_per_eV = 11604.5
    for label, x, y, mag, T_K in sf.STARS:
        cls_short = label.split("(")[-1].rstrip(")") if "(" in label else ""
        eV = T_K / K_per_eV
        text = f"{cls_short}\n{T_K} K\n{eV:.2f} eV"
        ax.annotate(text, xy=(x, y), xytext=(8, 8),
                    textcoords="offset points",
                    fontsize=6, color="yellow", alpha=0.85,
                    ha="left", va="bottom",
                    bbox=dict(boxstyle="round,pad=0.15",
                              facecolor="black", edgecolor="none",
                              alpha=0.4))


OVERLAY_FUNCTIONS: dict[str, callable] = {
    "airy_disk": overlay_airy_ring,
    "spider_vanes": _spider_overlay,
    "obstruction_plus_spiders": _spider_overlay,
    "aperture_vs_seeing": _resolution_overlay,
    "fratio_coma": _coma_starfield_overlay,
    # starfield_resolution: no overlay markers — rely on the rendered
    # stars themselves (variable brightness, planted close pairs and
    # bright edge stars) to be visible. The previous marker overlay
    # polluted the before-side (PointSource Airy disk) with the
    # after-side's 84-star markers projected into a 10″ window.
    "central_obstruction": _obstruction_overlay,
    "chromatic_plus_seeing": _chromatic_star_labels_overlay,
}
