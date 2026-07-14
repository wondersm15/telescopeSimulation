"""2D side-view ray trace visualization and focal plane imaging."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import matplotlib.pyplot as plt

from telescope_sim.physics.ray import Ray
from telescope_sim.physics.diffraction import compute_psf, rayleigh_criterion_arcsec
from telescope_sim.physics.fft_psf import compute_fft_psf
from telescope_sim.physics.aberrations import (
    compute_coma_spot,
    compute_coma_rms,
    coma_free_field,
)

if TYPE_CHECKING:
    from telescope_sim.geometry.telescope import (
        NewtonianTelescope,
        CassegrainTelescope,
        RefractingTelescope,
        MaksutovCassegrainTelescope,
        SchmidtCassegrainTelescope,
    )
    # Union of all telescope types (duck-typed, no common base class)
    Telescope = (NewtonianTelescope | CassegrainTelescope
                 | RefractingTelescope | MaksutovCassegrainTelescope
                 | SchmidtCassegrainTelescope)


# ── Absolute brightness calibration ──────────────────────────────────
#
# These two constants form the photometric anchor for source-image
# rendering. Together they define what "exposure_level = 1.0" means:
#
#   APERTURE_REFERENCE_MM
#       Reference aperture (100 mm). A telescope of diameter D collects
#       N ∝ D² photons; we scale per-star flux by (D / APERTURE_REFERENCE_MM)²
#       so a bigger scope genuinely brightens the image (physically correct
#       — previously the renderer ignored aperture area).
#
#   SATURATION_LEVEL
#       The rendered pixel value that maps to fully-saturated display
#       (clipped to 1.0). Calibrated empirically so a mag-0 PointSource
#       through a 100 mm scope at unit exposure, no seeing, default FOV
#       (20″) and 512 px canvas peaks at ~0.95 — just below saturation.
#       Brighter stars / larger apertures / longer exposures will then
#       legitimately saturate; fainter stars / smaller apertures will
#       sit at their true relative brightness.
#
# Empirical anchor measurement (100 mm f/8, mag 0, 20″ FOV, 512 px,
# no seeing): raw stamped peak ≈ 0.993. SATURATION_LEVEL = 1.0 puts
# this just below saturation, so the anchor case displays as a bright
# (but not clipped) star. Larger apertures or brighter magnitudes
# saturate; smaller apertures or dimmer stars sit at their true
# relative brightness (mag 4 at 100 mm ≈ 0.025).
APERTURE_REFERENCE_MM = 100.0
SATURATION_LEVEL = 1.0

# Dark-adapted human eye pupil diameter (mm). This is the reference exit
# pupil at which an extended object reaches naked-eye surface brightness:
# a telescope can never make an extended object's surface brightness exceed
# the naked-eye value, and at smaller exit pupils (higher magnification)
# the surface brightness falls as (exit_pupil / EYE_PUPIL_MM)². Used by the
# Eye-view brightness model, where exposure (a detector concept) does not
# apply — brightness comes from the optics instead. Visual-astronomy
# standard ~7 mm. Perceptual model — flagged in the plot annotation.
EYE_PUPIL_MM = 7.0


def _draw_ray_trace(ax: plt.Axes, rays: list[Ray], components: dict,
                    title: str = "Newtonian Telescope Ray Trace",
                    ray_color: str = "gold",
                    ray_alpha: float = 0.7,
                    mirror_color: str = "steelblue",
                    mirror_linewidth: float = 3.0,
                    show_tube: bool = True,
                    ray_colors: list | None = None,
                    show_focal_marker: bool = True) -> None:
    """Draw a ray trace diagram on the given axes.

    This is the core drawing helper used by both plot_ray_trace and
    the comparison functions.

    Args:
        ray_colors: Optional list of per-ray colors (matplotlib color spec).
            When provided, each ray uses its corresponding entry from
            the list instead of the single `ray_color`. Used by the
            ray-fan visualisation to share a pupil-zone colormap with
            the ray-trace panel.
        show_focal_marker: When False, suppresses the default "focal
            point" star + eyepiece icon. Useful when the caller wants
            to place its own focal-plane marker (e.g. at the *paraxial*
            plane rather than the mean of the secondary hits).
    """
    if show_tube:
        _draw_tube(ax, components)

    primary_pts = components["primary_surface"]
    secondary_pts = components["secondary_surface"]
    primary_type = components.get("primary_type", "")
    secondary_type = components.get("secondary_type", "")

    if components.get("telescope_style") == "maksutov":
        # Draw the meniscus corrector as a filled shape between
        # front and back surface curves (light blue fill).
        corr_front = components["corrector_front"]
        corr_back = components["corrector_back"]
        lens_x = np.concatenate([corr_front[:, 0], corr_back[::-1, 0]])
        lens_y = np.concatenate([corr_front[:, 1], corr_back[::-1, 1]])
        ax.fill(lens_x, lens_y, color="lightblue", alpha=0.4,
                label="Meniscus corrector")
        ax.plot(corr_front[:, 0], corr_front[:, 1],
                color="steelblue", linewidth=mirror_linewidth,
                solid_capstyle="round")
        ax.plot(corr_back[:, 0], corr_back[:, 1],
                color="steelblue", linewidth=mirror_linewidth,
                solid_capstyle="round")

        # Highlight the aluminized spot on the back surface center
        spot_d = components["spot_diameter"]
        spot_half = spot_d / 2.0
        # Extract the portion of the back surface within the spot
        spot_mask = np.abs(corr_back[:, 0]) <= spot_half
        if np.any(spot_mask):
            spot_pts = corr_back[spot_mask]
            ax.plot(spot_pts[:, 0], spot_pts[:, 1],
                    color="silver", linewidth=mirror_linewidth + 2,
                    solid_capstyle="round", label="Aluminized spot",
                    zorder=3)

        # Draw the spherical primary mirror
        ax.plot(primary_pts[:, 0], primary_pts[:, 1],
                color=mirror_color, linewidth=mirror_linewidth,
                solid_capstyle="round", label="Primary (spherical)")

    elif components.get("telescope_style") == "schmidt":
        # Schmidt-Cassegrain: corrector plate + spherical primary + convex secondary
        # Draw corrector plate as a thin vertical line across the aperture
        corrector_y = components.get("corrector_position", 0)
        corrector_half = components["primary_diameter"] / 2.0
        ax.plot([-corrector_half, corrector_half],
                [corrector_y, corrector_y],
                color="gray", linestyle="--", linewidth=1.5, alpha=0.7,
                label="Schmidt corrector (approx.)")

        # Draw spherical primary
        ax.plot(primary_pts[:, 0], primary_pts[:, 1],
                color=mirror_color, linewidth=mirror_linewidth,
                solid_capstyle="round", label="Primary (spherical)")

        # Draw convex spherical secondary
        ax.plot(secondary_pts[:, 0], secondary_pts[:, 1],
                color="firebrick", linewidth=mirror_linewidth,
                solid_capstyle="round", label="Secondary (spherical)")

    elif components.get("telescope_style") == "refractor":
        # Draw the objective lens(es).
        obj_type = components.get("objective_type", "singlet")
        glass_label = components.get("objective_glass", "")

        if obj_type == "achromat" and "interface_surface" in components:
            # Draw achromatic doublet: crown (light blue) + flint (light orange)
            interface_pts = components["interface_surface"]
            # Crown element: front surface to interface
            crown_x = np.concatenate([primary_pts[:, 0],
                                       interface_pts[::-1, 0]])
            crown_y = np.concatenate([primary_pts[:, 1],
                                       interface_pts[::-1, 1]])
            ax.fill(crown_x, crown_y, color="lightblue", alpha=0.5,
                    label="Crown (BK7)")
            # Flint element: interface to back surface
            flint_x = np.concatenate([interface_pts[:, 0],
                                       secondary_pts[::-1, 0]])
            flint_y = np.concatenate([interface_pts[:, 1],
                                       secondary_pts[::-1, 1]])
            ax.fill(flint_x, flint_y, color="navajowhite", alpha=0.5,
                    label="Flint (F2)")
            # Outlines
            ax.plot(primary_pts[:, 0], primary_pts[:, 1],
                    color="steelblue", linewidth=mirror_linewidth,
                    solid_capstyle="round")
            ax.plot(interface_pts[:, 0], interface_pts[:, 1],
                    color="gray", linewidth=mirror_linewidth * 0.7,
                    solid_capstyle="round", linestyle="--", alpha=0.7)
            ax.plot(secondary_pts[:, 0], secondary_pts[:, 1],
                    color="darkorange", linewidth=mirror_linewidth,
                    solid_capstyle="round")
        elif obj_type == "apo-doublet" and "interface_surface" in components:
            # Draw APO doublet: ED (light cyan) + crown (light blue)
            interface_pts = components["interface_surface"]
            # ED element: front surface to interface
            ed_x = np.concatenate([primary_pts[:, 0],
                                   interface_pts[::-1, 0]])
            ed_y = np.concatenate([primary_pts[:, 1],
                                   interface_pts[::-1, 1]])
            ax.fill(ed_x, ed_y, color="lightcyan", alpha=0.5,
                    label="ED (FPL51)")
            # Crown element: interface to back surface
            crown_x = np.concatenate([interface_pts[:, 0],
                                      secondary_pts[::-1, 0]])
            crown_y = np.concatenate([interface_pts[:, 1],
                                      secondary_pts[::-1, 1]])
            ax.fill(crown_x, crown_y, color="lightblue", alpha=0.5,
                    label="Crown (BK7)")
            # Outlines
            ax.plot(primary_pts[:, 0], primary_pts[:, 1],
                    color="cyan", linewidth=mirror_linewidth,
                    solid_capstyle="round")
            ax.plot(interface_pts[:, 0], interface_pts[:, 1],
                    color="gray", linewidth=mirror_linewidth * 0.7,
                    solid_capstyle="round", linestyle="--", alpha=0.7)
            ax.plot(secondary_pts[:, 0], secondary_pts[:, 1],
                    color="steelblue", linewidth=mirror_linewidth,
                    solid_capstyle="round")
        elif obj_type == "apo-triplet" and "interface1_surface" in components and "interface2_surface" in components:
            # Draw APO triplet: outer (ED) + middle (flint) + outer (ED)
            interface1_pts = components["interface1_surface"]
            interface2_pts = components["interface2_surface"]
            # Element 1 (front): front surface to interface1
            elem1_x = np.concatenate([primary_pts[:, 0],
                                      interface1_pts[::-1, 0]])
            elem1_y = np.concatenate([primary_pts[:, 1],
                                      interface1_pts[::-1, 1]])
            ax.fill(elem1_x, elem1_y, color="lightcyan", alpha=0.5,
                    label="APO-S outer (anomalous PD)")
            # Element 2 (middle): interface1 to interface2
            elem2_x = np.concatenate([interface1_pts[:, 0],
                                      interface2_pts[::-1, 0]])
            elem2_y = np.concatenate([interface1_pts[:, 1],
                                      interface2_pts[::-1, 1]])
            ax.fill(elem2_x, elem2_y, color="navajowhite", alpha=0.5,
                    label="Flint (F2)")
            # Element 3 (back): interface2 to back surface
            elem3_x = np.concatenate([interface2_pts[:, 0],
                                      secondary_pts[::-1, 0]])
            elem3_y = np.concatenate([interface2_pts[:, 1],
                                      secondary_pts[::-1, 1]])
            ax.fill(elem3_x, elem3_y, color="lightcyan", alpha=0.5)
            # Outlines
            ax.plot(primary_pts[:, 0], primary_pts[:, 1],
                    color="cyan", linewidth=mirror_linewidth,
                    solid_capstyle="round")
            ax.plot(interface1_pts[:, 0], interface1_pts[:, 1],
                    color="gray", linewidth=mirror_linewidth * 0.7,
                    solid_capstyle="round", linestyle="--", alpha=0.7)
            ax.plot(interface2_pts[:, 0], interface2_pts[:, 1],
                    color="gray", linewidth=mirror_linewidth * 0.7,
                    solid_capstyle="round", linestyle="--", alpha=0.7)
            ax.plot(secondary_pts[:, 0], secondary_pts[:, 1],
                    color="cyan", linewidth=mirror_linewidth,
                    solid_capstyle="round")
        else:
            # Singlet: single filled shape
            obj_label = (f"Objective lens ({glass_label})"
                         if glass_label else "Objective lens")
            lens_x = np.concatenate([primary_pts[:, 0],
                                      secondary_pts[::-1, 0]])
            lens_y = np.concatenate([primary_pts[:, 1],
                                      secondary_pts[::-1, 1]])
            ax.fill(lens_x, lens_y, color="lightblue", alpha=0.5,
                    label=obj_label)
            ax.plot(primary_pts[:, 0], primary_pts[:, 1],
                    color="steelblue", linewidth=mirror_linewidth,
                    solid_capstyle="round")
            ax.plot(secondary_pts[:, 0], secondary_pts[:, 1],
                    color="steelblue", linewidth=mirror_linewidth,
                    solid_capstyle="round")
    else:
        primary_label = f"Primary ({primary_type})" if primary_type else "Primary mirror"
        secondary_label = (f"Secondary ({secondary_type})"
                           if secondary_type else "Secondary mirror")
        ax.plot(primary_pts[:, 0], primary_pts[:, 1],
                color=mirror_color, linewidth=mirror_linewidth,
                solid_capstyle="round", label=primary_label)
        ax.plot(secondary_pts[:, 0], secondary_pts[:, 1],
                color="firebrick", linewidth=mirror_linewidth,
                solid_capstyle="round", label=secondary_label)

    # Draw spider vane cross-sections as thin lines at secondary height
    if "spider_vanes" in components:
        n_vanes = components["spider_vanes"]
        sec_y = components["secondary_offset"]
        half_d = components["primary_diameter"] / 2.0
        # In the 2D side view, vanes appear as vertical lines
        # at evenly spaced x-positions across the aperture
        for k in range(n_vanes):
            angle = k * np.pi / n_vanes
            # Project vane onto x-axis
            x_vane = half_d * np.cos(angle)
            if abs(x_vane) > 1e-3:  # skip vanes along optical axis
                ax.plot([x_vane, x_vane],
                        [sec_y - 3, sec_y + 3],
                        color="gray", linewidth=1.5, alpha=0.7)
                ax.plot([-x_vane, -x_vane],
                        [sec_y - 3, sec_y + 3],
                        color="gray", linewidth=1.5, alpha=0.7)

    for ray_idx, ray in enumerate(rays):
        if len(ray.history) < 2:
            continue
        path = np.array(ray.history)
        if ray_colors is not None and ray_idx < len(ray_colors):
            color = ray_colors[ray_idx]
        else:
            color = ray_color
        ax.plot(path[:, 0], path[:, 1],
                color=color, alpha=ray_alpha, linewidth=1.0)

    end_points = [ray.history[-1] for ray in rays if len(ray.history) >= 3]
    if end_points and show_focal_marker:
        focal_area = np.mean(end_points, axis=0)
        ax.plot(focal_area[0], focal_area[1], "r*", markersize=12,
                label="Focal point", zorder=5)

        # Draw an eyepiece icon at the focal point.
        # Detect dominant ray direction to orient the eyepiece barrel.
        _draw_eyepiece_icon(ax, rays, focal_area, components)

    ax.set_aspect("equal")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_title(title)
    ax.legend(loc="upper right", fontsize="small")
    ax.grid(True, alpha=0.3)


def plot_ray_trace(rays: list[Ray], components: dict,
                   title: str = "Newtonian Telescope Ray Trace",
                   figsize: tuple[float, float] = (14, 8),
                   ray_color: str = "gold",
                   ray_alpha: float = 0.7,
                   mirror_color: str = "steelblue",
                   mirror_linewidth: float = 3.0,
                   show_tube: bool = True,
                   save_path: str | None = None) -> plt.Figure:
    """Plot a 2D side-view ray trace diagram.

    Args:
        rays: List of traced Ray objects (with populated history).
        components: Dictionary from
                    NewtonianTelescope.get_components_for_plotting().
        title: Plot title.
        figsize: Figure size in inches.
        ray_color: Color for ray lines.
        ray_alpha: Transparency for ray lines.
        mirror_color: Color for mirror surfaces.
        mirror_linewidth: Line width for mirrors.
        show_tube: Whether to draw the telescope tube outline.
        save_path: If provided, save the figure to this path.

    Returns:
        The matplotlib Figure object.
    """
    fig, ax = plt.subplots(1, 1, figsize=figsize)
    _draw_ray_trace(ax, rays, components, title=title,
                    ray_color=ray_color, ray_alpha=ray_alpha,
                    mirror_color=mirror_color,
                    mirror_linewidth=mirror_linewidth,
                    show_tube=show_tube)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


def _find_focal_plane_positions(rays: list[Ray]) -> np.ndarray | None:
    """Find where traced rays cross the best focal plane.

    Detects the dominant travel direction of the final ray segments
    (x for Newtonian, y for Cassegrain), scans along that axis for
    the position where perpendicular spread is minimized, and returns
    the perpendicular offsets centered on zero.

    Args:
        rays: List of fully traced Ray objects.

    Returns:
        Array of transverse offsets at the focal plane, centered on zero.
        Returns None if no valid rays are found.
    """
    # Need at least 2 points to define the post-optic ray direction.
    # Newtonian-without-obstruction rays have 3 history points [start,
    # primary, terminal]; refractors typically have 4+. Cassegrain has
    # ≥4. Accepting >= 2 covers all configurations.
    traced_rays = [r for r in rays if len(r.history) >= 2]
    if not traced_rays:
        return None

    segments = []
    for ray in traced_rays:
        p_start = np.array(ray.history[-2])
        p_end = np.array(ray.history[-1])
        segments.append((p_start, p_end))

    # Detect dominant travel direction: compare total |dx| vs |dy|
    total_dx = sum(abs(s[1][0] - s[0][0]) for s in segments)
    total_dy = sum(abs(s[1][1] - s[0][1]) for s in segments)

    # scan_axis=0 means scan along x, measure spread in y
    # scan_axis=1 means scan along y, measure spread in x
    scan_axis = 0 if total_dx >= total_dy else 1
    perp_axis = 1 - scan_axis

    # Scan positions along the dominant axis to find best focus.
    # Extend the search range well past the segment endpoint(s) because for
    # Newtonians the traced rays stop at the secondary position, far short
    # of the actual focal plane (one focal length away). Refractors with
    # fully-traced rays already cover the focus inside the segment range.
    raw_min = min(min(s[0][scan_axis], s[1][scan_axis]) for s in segments)
    raw_max = max(max(s[0][scan_axis], s[1][scan_axis]) for s in segments)
    span = max(raw_max - raw_min, 1e-6)
    # Pick the dominant forward direction from the mean segment vector
    mean_forward = np.mean([
        s[1][scan_axis] - s[0][scan_axis] for s in segments
    ])
    if mean_forward >= 0:
        scan_min = raw_min - 0.5 * span
        scan_max = raw_max + 5.0 * span
    else:
        scan_min = raw_min - 5.0 * span
        scan_max = raw_max + 0.5 * span
    def _scan(positions):
        """Find position with minimum perpendicular spread; allow generous
        extrapolation so a focal plane many segment-lengths away can be found."""
        best_p = positions[0]
        best_s = float("inf")
        for tp in positions:
            crossings = []
            for p_start, p_end in segments:
                d_scan = p_end[scan_axis] - p_start[scan_axis]
                if abs(d_scan) < 1e-12:
                    continue
                t = (tp - p_start[scan_axis]) / d_scan
                if -2.0 <= t <= 20.0:
                    perp_val = (p_start[perp_axis]
                                + t * (p_end[perp_axis] - p_start[perp_axis]))
                    crossings.append(perp_val)
            if len(crossings) >= 2:
                spread = np.std(crossings)
                if spread < best_s:
                    best_s = spread
                    best_p = tp
        return best_p, best_s

    # Coarse pass over the wide range, then refine in a small window around
    # the coarse minimum so we converge precisely on the focal plane.
    coarse_pos, _ = _scan(np.linspace(scan_min, scan_max, 400))
    coarse_step = (scan_max - scan_min) / 400.0
    fine_lo = coarse_pos - 2.0 * coarse_step
    fine_hi = coarse_pos + 2.0 * coarse_step
    best_pos, best_spread = _scan(np.linspace(fine_lo, fine_hi, 400))

    # Compute ray positions at the best focal plane
    perp_positions = []
    for p_start, p_end in segments:
        d_scan = p_end[scan_axis] - p_start[scan_axis]
        if abs(d_scan) < 1e-12:
            continue
        t = (best_pos - p_start[scan_axis]) / d_scan
        perp_val = (p_start[perp_axis]
                    + t * (p_end[perp_axis] - p_start[perp_axis]))
        perp_positions.append(perp_val)

    perp_positions = np.array(perp_positions)
    center = np.mean(perp_positions)
    return perp_positions - center


def _trace_dense_rays(telescope: Telescope,
                      num_rays: int = 501) -> list[Ray]:
    """Create and trace a dense set of rays through the telescope.

    Used internally by plot_focal_image and plot_psf_profile so that
    physics-based imaging is independent of the user's visual ray count.

    Args:
        telescope: The telescope to trace through.
        num_rays: Number of rays to trace (more = smoother results).

    Returns:
        List of traced Ray objects.
    """
    from telescope_sim.source import create_parallel_rays

    rays = create_parallel_rays(
        num_rays=num_rays,
        aperture_diameter=telescope.primary_diameter,
        entry_height=telescope.tube_length * 1.15,
    )
    telescope.trace_rays(rays)
    return rays


def _analytical_focal_offsets(telescope: Telescope,
                              num_zones: int = 1001,
                              include_obstruction: bool = True) -> np.ndarray:
    """Compute focal plane offsets from exact mirror geometry formulas.

    Instead of tracing rays through the simulation, this evaluates
    the closed-form aberration equations for the primary mirror type.

    Parabolic: all offsets are identically zero (perfect on-axis focus
    by definition of a paraboloid).

    Spherical: exact transverse spherical aberration derived from the
    mirror equation (x^2 + (y-R)^2 = R^2) and law of reflection.
    For a ray at pupil height h, the reflected direction is:
        dx = -2hs/R^2,  dy = 1 - 2h^2/R^2
    where s = sqrt(R^2 - h^2).  The transverse position at each
    candidate focal plane is evaluated exactly, and the plane of
    least confusion (minimum RMS spread) is selected.

    Args:
        telescope: The telescope to analyze.
        num_zones: Number of pupil sample points.

    Returns:
        Array of transverse offsets at the best focal plane (mm).
    """
    r_max = (telescope.primary_diameter / 2.0) * 0.95  # match 5% margin
    h_values = np.linspace(-r_max, r_max, num_zones)

    # Mask out rays blocked by the secondary mirror obstruction
    if include_obstruction:
        secondary_radius = telescope.secondary_minor_axis / 2.0
        unblocked = np.abs(h_values) >= secondary_radius
        h_values = h_values[unblocked]
        num_zones = len(h_values)

    if getattr(telescope, 'corrected_optics', False):
        # Corrected systems (e.g., Maksutov-Cassegrain with meniscus
        # corrector) are diffraction-limited on-axis.
        return np.zeros(num_zones)

    if telescope.primary_type == "parabolic":
        return np.zeros(num_zones)

    elif telescope.primary_type == "lens":
        # Monochromatic singlet on-axis: diffraction-limited.
        # NOTE: Chromatic aberration (multi-wavelength) not yet modeled.
        return np.zeros(num_zones)

    elif telescope.primary_type == "spherical":
        R = 2.0 * telescope.focal_length
        f0 = telescope.focal_length

        # Exact geometry of ray reflection off a spherical mirror
        # Mirror surface: x^2 + (y - R)^2 = R^2, vertex at origin
        s = np.sqrt(R**2 - h_values**2)
        y_mirror = R - s

        # Reflected direction for incoming d = (0, -1):
        dx_ref = -2.0 * h_values * s / R**2
        dy_ref = 1.0 - 2.0 * h_values**2 / R**2

        # Marginal focus (where the edge ray crosses the axis)
        s_edge = np.sqrt(R**2 - r_max**2)
        y_marginal = R - s_edge / 2.0 - r_max**2 / (2.0 * s_edge)

        # Scan from marginal focus to just past paraxial for best focus
        test_z = np.linspace(y_marginal - 0.5, f0 + 0.5, 500)

        best_z = f0
        best_rms = float("inf")

        for z in test_z:
            t = (z - y_mirror) / dy_ref
            valid = (dy_ref > 1e-10) & (t > 0)
            if valid.sum() < 3:
                continue
            x_at_z = h_values[valid] + t[valid] * dx_ref[valid]
            rms = np.std(x_at_z)
            if rms < best_rms:
                best_rms = rms
                best_z = z

        # Transverse positions at the plane of least confusion
        t = (best_z - y_mirror) / dy_ref
        x_at_best = h_values + t * dx_ref
        return x_at_best - np.mean(x_at_best)

    else:
        raise ValueError(
            f"Analytical method not available for primary type "
            f"'{telescope.primary_type}'. Use method='traced'."
        )


def _get_focal_offsets(telescope: Telescope,
                       method: str = "analytical",
                       num_trace_rays: int = 501,
                       include_obstruction: bool = True) -> np.ndarray | None:
    """Get focal plane offsets using the specified method.

    Args:
        telescope: The telescope to analyze.
        method: "analytical" for exact mirror formulas,
                "traced" for numerical ray tracing.
        num_trace_rays: Number of rays (only used when method="traced").
        include_obstruction: If False, ignore the secondary mirror
                             obstruction (sample the full pupil).

    Returns:
        Array of transverse offsets at the focal plane (mm).
        Returns None if ray tracing produces no valid results.
    """
    if method == "analytical":
        return _analytical_focal_offsets(telescope,
                                         include_obstruction=include_obstruction)
    elif method == "traced":
        rays = _trace_dense_rays(telescope, num_trace_rays)
        return _find_focal_plane_positions(rays)
    else:
        raise ValueError(
            f"Unknown method '{method}'. Use 'analytical' or 'traced'."
        )


def _draw_spot_diagram(ax: plt.Axes, y_offsets: np.ndarray | None,
                       title: str = "Spot Diagram at Focal Plane",
                       show_rms: bool = True,
                       show_max: bool = True,
                       rays: list[Ray] | None = None,
                       focal_plane_y: float | None = None) -> None:
    """Draw a spot diagram on the given axes.

    This is the core drawing helper used by both plot_spot_diagram and
    the comparison functions.

    Args:
        ax: Matplotlib axes to draw on.
        y_offsets: Lateral offsets of rays at focal plane.
        title: Title for the plot.
        show_rms: Whether to show RMS circle.
        show_max: Whether to show max extent circle.
        rays: Optional list of Ray objects for color-coding by aperture position.
        focal_plane_y: Optional y-coordinate of focal plane for annotation.
    """
    if y_offsets is None:
        ax.set_title(title)
        ax.text(0.5, 0.5, "No fully traced rays", ha="center",
                va="center", transform=ax.transAxes)
        return

    rms_spot = np.std(y_offsets)
    max_spot = np.max(np.abs(y_offsets))

    # 2D ring expansion: the 2D ray tracer produces y-offsets along a
    # single cross-section. For an axisymmetric optical system, each
    # ray at offset r corresponds to a RING of radius |r| at the focal
    # plane in 3D. Scattering at multiple azimuthal positions gives a
    # realistic 2D spot pattern (instead of a 1D line of dots).
    n_azimuth = 36
    azimuths = np.linspace(0, 2 * np.pi, n_azimuth, endpoint=False)
    n_rays = len(y_offsets)
    abs_offsets = np.abs(y_offsets)
    # Build 2D scatter arrays: each y-offset replicated across azimuth
    x2d = np.empty(n_rays * n_azimuth)
    y2d = np.empty(n_rays * n_azimuth)
    color2d = np.empty(n_rays * n_azimuth)
    for i, r_off in enumerate(abs_offsets):
        x2d[i * n_azimuth:(i + 1) * n_azimuth] = r_off * np.cos(azimuths)
        y2d[i * n_azimuth:(i + 1) * n_azimuth] = r_off * np.sin(azimuths)

    if rays is not None:
        aperture_radii = [ray.aperture_position for ray in rays
                         if ray.aperture_position is not None]
        if aperture_radii and len(aperture_radii) == len(y_offsets):
            aperture_radii = np.array(aperture_radii)
            max_radius = np.max(aperture_radii) if np.max(aperture_radii) > 0 else 1.0
            normalized_radii = aperture_radii / max_radius
            for i in range(n_rays):
                color2d[i * n_azimuth:(i + 1) * n_azimuth] = normalized_radii[i]
            scatter = ax.scatter(x2d, y2d, c=color2d, cmap='viridis',
                               edgecolors='none', s=12, alpha=0.7, zorder=3,
                               vmin=0, vmax=1, label="Ray positions")
            cbar = plt.colorbar(scatter, ax=ax, pad=0.02, fraction=0.046)
            cbar.set_label('Incident Radial Distance\n(normalized)',
                          rotation=270, labelpad=20, fontsize=9)
        else:
            ax.scatter(x2d, y2d, c="gold", edgecolors="none",
                      s=12, alpha=0.7, zorder=3, label="Ray positions")
    else:
        ax.scatter(x2d, y2d, c="gold", edgecolors="none",
                   s=12, alpha=0.7, zorder=3, label="Ray positions")

    margin = max(max_spot * 1.5, rms_spot * 4, 0.01)
    ax.axhline(0, color="gray", linewidth=0.5, alpha=0.5)
    ax.axvline(0, color="gray", linewidth=0.5, alpha=0.5)

    if show_rms and rms_spot > 1e-6:
        rms_circle = plt.Circle((0, 0), rms_spot, fill=False,
                                color="red", linestyle="--", linewidth=1.5,
                                label=f"RMS spot: {rms_spot:.3f} mm")
        ax.add_patch(rms_circle)

    if show_max and max_spot > 1e-6:
        max_circle = plt.Circle((0, 0), max_spot, fill=False,
                                color="blue", linestyle=":", linewidth=1.5,
                                label=f"Max extent: {max_spot:.3f} mm")
        ax.add_patch(max_circle)

    ax.set_xlim(-margin, margin)
    ax.set_ylim(-margin, margin)
    ax.set_aspect("equal")
    ax.set_xlabel("Position on focal plane (mm)")
    ax.set_ylabel("Position on focal plane (mm)")
    ax.set_title(title)
    # Compact legend pinned outside the data region so it doesn't cover the
    # spot itself in small tutorial figures.
    ax.legend(loc="upper left", fontsize=7, framealpha=0.85,
              borderpad=0.3, handlelength=1.5)
    ax.grid(True, alpha=0.3)

    # Compact stats box — small font, lower right where it rarely overlaps
    ax.text(0.98, 0.02,
            f"RMS: {rms_spot:.4f} mm  |  Max spread: {max_spot * 2:.4f} mm",
            transform=ax.transAxes, fontsize=7,
            verticalalignment="bottom", horizontalalignment="right",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="wheat", alpha=0.8))

    # A geometrically perfect design (e.g. parabolic primary on-axis)
    # collapses all rays to a single point. Without an annotation the
    # user reads the single dot as a missing render. Surface it explicitly
    # below ~1 µm RMS — well below the Airy radius at typical f-ratios.
    if rms_spot < 1e-3:
        ax.text(0.98, 0.98,
                "Diffraction-limited\n(no geometric blur)",
                transform=ax.transAxes, fontsize=8,
                horizontalalignment="right", verticalalignment="top",
                color="darkgreen", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3",
                          facecolor="honeydew", edgecolor="darkgreen",
                          alpha=0.9))
    else:
        # Caustic-ring annotation: the visible ring concentrations are
        # the real caustic structure of spherical aberration — rays from
        # different aperture heights cross the best-focus plane at
        # different offsets y(h), and the rings cluster where dy/dh ≈ 0.
        # The pattern is from the actual ray trace, not a parametric
        # approximation.
        ax.text(0.98, 0.98,
                "Caustic ring structure:\n"
                "ray-traced y(h) crossings\n"
                "cluster where dy/dh ≈ 0",
                transform=ax.transAxes, fontsize=7,
                horizontalalignment="right", verticalalignment="top",
                color="dimgray", style="italic",
                bbox=dict(boxstyle="round,pad=0.3",
                          facecolor="white", edgecolor="lightgray",
                          alpha=0.85))

    # Add focal plane position annotation if provided
    if focal_plane_y is not None:
        ax.text(0.02, 0.98, f"Focal plane y = {focal_plane_y:.2f} mm",
                transform=ax.transAxes, fontsize=7, verticalalignment='top',
                horizontalalignment='left',
                bbox=dict(boxstyle='round,pad=0.25', facecolor='lightblue',
                          alpha=0.7))


def _paraxial_focal_plane_offsets(rays: list[Ray]) -> np.ndarray | None:
    """Transverse offsets at the *paraxial* focal plane, ray by ray.

    Different from `_find_focal_plane_positions` (which scans for the
    minimum-spread plane = circle of least confusion). For an SA-free
    optic, the two planes coincide and all offsets are ≈ 0. For a
    spherical primary, the paraxial plane is *farther* than the
    marginal crossing, so marginal rays arrive having already crossed
    the axis — Δy(h) follows the classical cubic textbook signature.

    Returns an array aligned to the input ray order (NaN where the
    ray failed to trace or the plane lies far outside its segment).
    """
    traced = [r for r in rays if len(r.history) >= 2]
    if not traced:
        return None

    # Detect dominant travel axis from the bundle as a whole.
    # (Cannot use a single ray — the on-axis ray for a Newtonian
    # bounces straight back and gives degenerate direction.)
    segments = [(np.array(r.history[-2]), np.array(r.history[-1]))
                for r in traced]
    total_dx = sum(abs(s[1][0] - s[0][0]) for s in segments)
    total_dy = sum(abs(s[1][1] - s[0][1]) for s in segments)
    scan_axis = 0 if total_dx >= total_dy else 1
    perp_axis = 1 - scan_axis

    # Pick the smallest *non-zero*-|h| ray with a non-degenerate
    # segment as the paraxial reference. The exactly-on-axis ray
    # often reflects back along its own path (Newtonian centerline),
    # producing direction[perp_axis] ≈ 0 — that doesn't tell us
    # where the actual focal plane lies.
    candidates = [
        r for r in traced
        if abs(r.origin[0]) > 1e-3
        and abs((np.array(r.history[-1])
                 - np.array(r.history[-2]))[perp_axis]) > 1e-6
    ]
    if not candidates:
        return None
    on_axis = min(candidates, key=lambda r: abs(r.origin[0]))
    p0 = np.array(on_axis.history[-2])
    p1 = np.array(on_axis.history[-1])
    direction = p1 - p0

    # Solve for where the reference ray's final segment crosses the
    # optical axis (perp_value = 0). That scan-axis coordinate is the
    # paraxial focal plane.
    t_ref = -p0[perp_axis] / direction[perp_axis]
    plane_pos = p0[scan_axis] + t_ref * direction[scan_axis]

    # Sample each ray at that plane, allowing generous extrapolation.
    offsets = []
    for r in rays:
        if len(r.history) < 2:
            offsets.append(np.nan)
            continue
        rp0 = np.array(r.history[-2])
        rp1 = np.array(r.history[-1])
        rdir = rp1 - rp0
        if abs(rdir[scan_axis]) < 1e-12:
            offsets.append(np.nan)
            continue
        t = (plane_pos - rp0[scan_axis]) / rdir[scan_axis]
        # Allow extrapolation beyond the traced segment (paraxial focal
        # plane is typically one focal-length past the secondary).
        if not (-5.0 <= t <= 50.0):
            offsets.append(np.nan)
            continue
        off = rp0[perp_axis] + t * rdir[perp_axis]
        offsets.append(off)

    return np.asarray(offsets, dtype=float)


def _pupil_colormap_colors(entry_heights: np.ndarray):
    """Return (per-ray RGBA colors, ScalarMappable for colorbar).

    Maps |entry height| onto the viridis colormap so the innermost
    rays are dark and marginal rays are bright. Symmetric: a ray at
    +5 mm and -5 mm share the same colour, because in a rotationally
    symmetric system they belong to the same pupil zone.
    """
    h_abs = np.abs(entry_heights)
    h_max = float(np.max(h_abs)) if len(h_abs) > 0 else 1.0
    if h_max <= 0:
        h_max = 1.0
    norm = plt.Normalize(vmin=0.0, vmax=h_max)
    cmap = plt.get_cmap("viridis")
    colors = [cmap(norm(float(h))) for h in h_abs]
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    return colors, sm


def plot_ray_fan_telescope(telescope: Telescope,
                            wavelength_nm: float = 550.0,
                            num_rays: int = 21,
                            figsize: tuple[float, float] = (7, 5),
                            title: str | None = None,
                            save_path: str | None = None,
                            ) -> plt.Figure:
    """Ray-fan plot: transverse focal-plane offset vs pupil entry height.

    This is the canonical optical-design view of an aberration: the
    shape of the curve directly reveals which Seidel aberration is
    present.

      • cubic (Δx ∝ h³)   → spherical aberration
      • parabolic (Δx ∝ h²) → coma
      • linear (Δx ∝ h)     → defocus
      • flat (Δx ≈ 0)        → diffraction-limited

    Each point is one traced ray, coloured by its pupil entry height
    using a viridis colormap that the companion ray-trace plot
    (`plot_ray_trace_pupil_colored`) reuses — so the viewer can pick
    a coloured ray in the ray trace and find the same colour in the
    ray fan, connecting "where the ray came from" to "where it
    landed".
    """
    from telescope_sim.source.light_source import create_parallel_rays
    rays = create_parallel_rays(
        num_rays=num_rays,
        aperture_diameter=telescope.primary_diameter,
        entry_height=telescope.tube_length * 1.15,
        wavelength_nm=wavelength_nm,
    )
    # Capture pupil entry heights before tracing
    entry_heights = np.array([r.origin[0] for r in rays])

    telescope.trace_rays(rays)
    # Use the paraxial focal plane (where central rays focus) so SA
    # produces the canonical Δy ∝ h³ cubic curve. Plotting at the
    # circle of least confusion (min-spread plane) instead would
    # give a less-canonical W-shape that doesn't match the textbook
    # "cubic = SA" teaching.
    y_offsets = _paraxial_focal_plane_offsets(rays)

    fig, ax = plt.subplots(figsize=figsize)

    if y_offsets is None or len(y_offsets) == 0:
        ax.text(0.5, 0.5, "Ray trace failed", ha="center", va="center",
                transform=ax.transAxes)
        return fig

    # Drop NaN rays (failed traces or far-extrapolated)
    valid = ~np.isnan(y_offsets)
    entry_heights = entry_heights[valid]
    y_offsets = y_offsets[valid]

    # Sort by pupil height for a clean trace line
    sort_idx = np.argsort(entry_heights)
    h_sorted = entry_heights[sort_idx]
    y_sorted = y_offsets[sort_idx]

    colors, sm = _pupil_colormap_colors(h_sorted)

    # The connecting trace line: faint, so it suggests "this is a
    # smooth function of h" without competing with the dots.
    ax.plot(h_sorted, y_sorted * 1000.0, color="gray", alpha=0.4,
            linewidth=1.0, zorder=1)

    # Coloured dots (one per ray)
    ax.scatter(h_sorted, y_sorted * 1000.0, c=colors, s=70,
                edgecolors="black", linewidths=0.5, zorder=3)

    # Reference axes
    ax.axhline(0.0, color="black", linestyle=":", alpha=0.4, zorder=0)
    ax.axvline(0.0, color="black", linestyle=":", alpha=0.4, zorder=0)

    # Annotations
    primary = getattr(telescope, "primary_type", "")
    primary_label = f" ({primary})" if primary else ""
    f_ratio = telescope.focal_ratio
    rms_um = float(np.std(y_sorted) * 1000.0)
    max_um = float(np.max(np.abs(y_sorted)) * 1000.0)

    if title is None:
        title = (f"Ray fan — {telescope.primary_diameter:.0f} mm "
                 f"f/{f_ratio:.1f}{primary_label}")
    ax.set_title(title, fontsize=11)
    ax.set_xlabel("Pupil entry height h (mm)")
    # The vertical axis is the TRANSVERSE ray error — where a ray lands at the
    # focal plane relative to the ideal focus, measured across the optical
    # axis. That transverse direction is the x-axis of the companion ray-trace
    # panel, so label it Δx (not Δy) for consistency with the left plot.
    ax.set_ylabel("Transverse ray error at focal plane, Δx (µm)")
    ax.grid(True, alpha=0.3)

    # Floor the y-axis to a physical (diffraction) scale so a corrected
    # system reads as FLAT, not a magnified floating-point zigzag. A
    # parabolic primary has Δy ≈ 1e-11 µm (numerical noise); left to
    # autoscale, matplotlib blows that up into a fake S/zigzag even though
    # RMS = 0.00 µm. Referencing the axis to the Airy radius makes
    # "aberration ≪ diffraction limit" look diffraction-limited (a flat
    # line through zero), while a real aberration (max |Δy| ≫ Airy)
    # autoscales normally and shows its full curve.
    airy_um = 1.22 * (wavelength_nm * 1e-6) * f_ratio * 1000.0
    y_floor_um = 3.0 * airy_um  # half-range floor ≈ 3 Airy radii
    y_half = max(max_um * 1.15, y_floor_um)
    ax.set_ylim(-y_half, y_half)

    # Pupil-zone colorbar (matches the companion ray-trace panel)
    cbar = fig.colorbar(sm, ax=ax, shrink=0.85,
                        label="|Pupil zone| (mm)")
    cbar.ax.tick_params(labelsize=8)

    # Aberration cheat-sheet
    cheat = ("Δx(h) shape ↔ aberration\n"
             "  S-shape (h³)   spherical\n"
             "  U-shape (h²)   coma\n"
             "  tilt (h¹)      defocus\n"
             "  ≈ 0 across h   diffraction-limited")
    ax.text(0.02, 0.98, cheat, transform=ax.transAxes,
            va="top", ha="left", fontsize=7,
            bbox=dict(boxstyle="round,pad=0.3",
                      facecolor="white", alpha=0.85,
                      edgecolor="gray"))
    # Stats
    ax.text(0.98, 0.02,
            f"RMS Δx = {rms_um:.2f} µm\nmax |Δx| = {max_um:.2f} µm",
            transform=ax.transAxes, va="bottom", ha="right",
            fontsize=7,
            bbox=dict(boxstyle="round,pad=0.3",
                      facecolor="white", alpha=0.85,
                      edgecolor="gray"))

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_ray_trace_pupil_colored(telescope: Telescope,
                                  wavelength_nm: float = 550.0,
                                  num_rays: int = 21,
                                  figsize: tuple[float, float] = (7, 5),
                                  title: str | None = None,
                                  save_path: str | None = None,
                                  ) -> plt.Figure:
    """Ray-trace plot with rays coloured by pupil entry zone.

    Companion to `plot_ray_fan_telescope` — both use the same
    viridis-on-|h| colormap so a ray in the trace and its point in
    the ray fan share a colour. Useful for spherical-aberration
    teaching: the user can see that the bright (marginal) rays
    cross the axis short of the dim (paraxial) rays.
    """
    from telescope_sim.source.light_source import create_parallel_rays
    rays = create_parallel_rays(
        num_rays=num_rays,
        aperture_diameter=telescope.primary_diameter,
        entry_height=telescope.tube_length * 1.15,
        wavelength_nm=wavelength_nm,
    )
    entry_heights = np.array([r.origin[0] for r in rays])

    telescope.trace_rays(rays)

    colors, sm = _pupil_colormap_colors(entry_heights)

    components = telescope.get_components_for_plotting()
    if title is None:
        primary = getattr(telescope, "primary_type", "")
        primary_label = f" ({primary})" if primary else ""
        title = (f"Ray trace — {telescope.primary_diameter:.0f} mm "
                 f"f/{telescope.focal_ratio:.1f}{primary_label}")

    fig, ax = plt.subplots(figsize=figsize)
    _draw_ray_trace(ax, rays, components, title=title,
                    ray_color="gold",  # ignored when ray_colors is set
                    ray_alpha=0.85,
                    show_tube=True,
                    ray_colors=colors,
                    show_focal_marker=False)

    # Extend each ray's final (post-primary) segment forward to the
    # paraxial focal plane. The base tracer stops at the secondary
    # depth, which hides the *whole point* of the SA scenario —
    # marginal rays crossing the axis short of paraxial. We unfold
    # the geometry and just continue the primary→secondary
    # direction; physically correct because the secondary is a flat
    # mirror that doesn't change ray convergence.
    paraxial_offsets = _paraxial_focal_plane_offsets(rays)
    if paraxial_offsets is not None:
        # Recover the paraxial focal-plane scan-axis position by
        # locating the smallest-|h| ray with a non-degenerate
        # direction (matches the logic in the offset helper).
        traced = [r for r in rays if len(r.history) >= 2]
        segments = [(np.array(r.history[-2]), np.array(r.history[-1]))
                    for r in traced]
        total_dx = sum(abs(s[1][0] - s[0][0]) for s in segments)
        total_dy = sum(abs(s[1][1] - s[0][1]) for s in segments)
        scan_axis = 0 if total_dx >= total_dy else 1
        perp_axis = 1 - scan_axis
        candidates = [
            r for r in traced
            if abs(r.origin[0]) > 1e-3
            and abs((np.array(r.history[-1])
                     - np.array(r.history[-2]))[perp_axis]) > 1e-6
        ]
        if candidates:
            ref = min(candidates, key=lambda r: abs(r.origin[0]))
            rp0 = np.array(ref.history[-2])
            rp1 = np.array(ref.history[-1])
            rdir = rp1 - rp0
            t_ref = -rp0[perp_axis] / rdir[perp_axis]
            plane_pos = rp0[scan_axis] + t_ref * rdir[scan_axis]

            # Now draw the extension for each ray
            for ray_idx, r in enumerate(rays):
                if len(r.history) < 2:
                    continue
                p0 = np.array(r.history[-2])
                p1 = np.array(r.history[-1])
                d = p1 - p0
                if abs(d[scan_axis]) < 1e-12:
                    continue
                # Stop a bit past the focal plane so the SA crossover
                # is visually obvious
                if scan_axis == 1:
                    extend_to = plane_pos + 0.05 * (plane_pos - p0[scan_axis])
                else:
                    extend_to = plane_pos + 0.05 * (plane_pos - p0[scan_axis])
                t = (extend_to - p0[scan_axis]) / d[scan_axis]
                ext_pt = p0 + t * d
                # Use the matching pupil color
                if ray_idx < len(colors):
                    c = colors[ray_idx]
                else:
                    c = "gold"
                # Draw the extension SOLID (not dotted) so each ray reads as
                # one continuous line from primary → focal plane. The old
                # dotted style created a picket-fence/checkerboard moiré
                # across the ~21 near-parallel converging rays and a jarring
                # solid→dotted transition mid-ray (user-reported). Match the
                # traced segment's weight; slight transparency keeps the
                # crossover region legible where many rays overlap.
                ax.plot([p1[0], ext_pt[0]],
                        [p1[1], ext_pt[1]],
                        color=c, alpha=0.7, linewidth=1.0,
                        linestyle="-", zorder=2)

            # Mark the paraxial focal plane with a horizontal/vertical
            # guide line + a star at the on-axis position.
            if scan_axis == 1:
                ax.axhline(plane_pos, color="gray", linestyle="--",
                            alpha=0.5, linewidth=0.8)
                ax.plot(0.0, plane_pos, "r*", markersize=12, zorder=5,
                        label="Paraxial focal plane")
            else:
                ax.axvline(plane_pos, color="gray", linestyle="--",
                            alpha=0.5, linewidth=0.8)
                ax.plot(plane_pos, 0.0, "r*", markersize=12, zorder=5,
                        label="Paraxial focal plane")

            # Focal-region zoom INSET (R3.8a): on the full-height ray trace the
            # focus is a single point and the marginal-vs-paraxial spread is
            # invisible. Magnify the axis-crossing region so the bright
            # (marginal) rays crossing the axis SHORT of the dim (paraxial)
            # rays is actually visible — the whole point of the scenario.
            # (scan_axis == 1: optical axis is y, transverse is x.)
            if scan_axis == 1:
                crossings = []
                for r in rays:
                    if len(r.history) < 2:
                        continue
                    q0 = np.array(r.history[-2]); q1 = np.array(r.history[-1])
                    dd = q1 - q0
                    if abs(dd[1]) < 1e-12:
                        continue
                    tt = -q1[0] / dd[0] if abs(dd[0]) > 1e-12 else None
                    # crossing of the optical axis (x = 0)
                    if abs(dd[0]) > 1e-12:
                        t_ax = -q1[0] / dd[0]
                        crossings.append(q1[1] + t_ax * dd[1])
                if crossings and (max(crossings) - min(crossings)) > 1e-4:
                    cmin, cmax = min(crossings), max(crossings)
                    span = cmax - cmin
                    lo = min(cmin, plane_pos) - 0.25 * span
                    hi = max(cmax, plane_pos) + 0.25 * span
                    tw = span * 0.7 + 1e-4
                    axin = ax.inset_axes([0.55, 0.28, 0.33, 0.30])
                    for ray_idx, r in enumerate(rays):
                        if len(r.history) < 2:
                            continue
                        q0 = np.array(r.history[-2])
                        q1 = np.array(r.history[-1])
                        dd = q1 - q0
                        if abs(dd[1]) < 1e-12:
                            continue
                        t2 = (lo - q1[1]) / dd[1]
                        e2 = q1 + t2 * dd
                        c = colors[ray_idx] if ray_idx < len(colors) else "gold"
                        axin.plot([q1[0], e2[0]], [q1[1], e2[1]],
                                  color=c, linewidth=1.0, alpha=0.85)
                    axin.axhline(plane_pos, color="gray", linestyle="--",
                                 linewidth=0.8, alpha=0.6)
                    axin.plot(0.0, plane_pos, "r*", markersize=8, zorder=5)
                    axin.set_xlim(-tw, tw)
                    axin.set_ylim(lo, hi)
                    axin.set_title(
                        "Focal-region zoom (marginal ✗ short of ★)",
                        fontsize=6.5)
                    axin.set_xlabel("x (mm)", fontsize=6)
                    axin.set_ylabel("y (mm)", fontsize=6)
                    axin.tick_params(labelsize=6)
                    # Move the main-axes legend out of the inset's way
                    # (recreate at lower-left; robust across mpl versions).
                    if ax.get_legend() is not None:
                        ax.legend(loc="lower left", fontsize=7, framealpha=0.9)

    # Add pupil-zone colorbar — matches the ray-fan panel
    cbar = fig.colorbar(sm, ax=ax, shrink=0.7, pad=0.02,
                        label="|Pupil zone| (mm)")
    cbar.ax.tick_params(labelsize=8)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_spot_diagram_telescope(telescope: Telescope,
                                 wavelength_nm: float = 550.0,
                                 num_rays: int = 51,
                                 figsize: tuple[float, float] = (7, 7),
                                 title: str | None = None,
                                 save_path: str | None = None) -> plt.Figure:
    """Trace parallel rays through a telescope and plot the focal-plane spot.

    Convenience wrapper around `plot_spot_diagram` for callers that have a
    telescope but no pre-traced rays (e.g. tutorial scenarios).
    """
    from telescope_sim.source.light_source import create_parallel_rays
    rays = create_parallel_rays(
        num_rays=num_rays,
        aperture_diameter=telescope.primary_diameter,
        entry_height=telescope.tube_length * 1.15,
        wavelength_nm=wavelength_nm,
    )
    telescope.trace_rays(rays)
    if title is None:
        prim = getattr(telescope, "primary_type", "")
        prim_label = f" ({prim})" if prim else ""
        title = (f"Spot diagram — {telescope.primary_diameter:.0f}mm "
                 f"f/{telescope.focal_ratio:.1f}{prim_label}")
    return plot_spot_diagram(rays, title=title, figsize=figsize,
                              save_path=save_path)


def plot_spot_diagram(rays: list[Ray],
                      title: str = "Spot Diagram at Focal Plane",
                      figsize: tuple[float, float] = (7, 7),
                      show_rms: bool = True,
                      show_max: bool = True,
                      save_path: str | None = None) -> plt.Figure:
    """Plot a spot diagram showing where rays converge at the focal plane.

    After tracing, each ray's final segment (post-secondary) travels
    toward the focal area. This function finds the focal plane position
    where the rays are most concentrated and plots their crossing points.

    Args:
        rays: List of fully traced Ray objects (with populated history).
        title: Plot title.
        figsize: Figure size in inches.
        show_rms: Show the RMS spot size circle (default True).
        show_max: Show the max extent circle (default True).
        save_path: If provided, save the figure to this path.

    Returns:
        The matplotlib Figure object.
    """
    y_offsets = _find_focal_plane_positions(rays)

    # Extract focal plane y position from rays (approximate from last ray position)
    focal_plane_y = None
    traced_rays = [r for r in rays if len(r.history) >= 2]
    if traced_rays:
        focal_plane_y = traced_rays[0].history[-1][1]

    fig, ax = plt.subplots(figsize=figsize)
    _draw_spot_diagram(ax, y_offsets, title=title,
                       show_rms=show_rms, show_max=show_max,
                       rays=rays, focal_plane_y=focal_plane_y)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


def _build_geometric_spot_2d(y_offsets: np.ndarray, half_size: float,
                             num_pixels: int) -> np.ndarray:
    """Build a 2D geometric spot image from 1D ray offsets.

    Since our ray tracer is 2D (cross-section), the y_offsets represent
    a radial slice. For a rotationally symmetric telescope, each offset
    at distance r corresponds to a ring of rays at that radius in 3D.
    We reconstruct the 2D spot by distributing intensity on rings.

    Args:
        y_offsets: 1D array of ray positions relative to center.
        half_size: Half the image width in mm.
        num_pixels: Image resolution.

    Returns:
        2D numpy array with the geometric spot pattern.
    """
    image = np.zeros((num_pixels, num_pixels))
    pixel_size = (2 * half_size) / num_pixels
    coords = np.linspace(-half_size, half_size, num_pixels)
    xx, yy = np.meshgrid(coords, coords)
    rr = np.sqrt(xx ** 2 + yy ** 2)

    # Use absolute offsets as radial distances and spread each
    # ray's intensity around a thin ring (with sub-pixel Gaussian width)
    ring_width = max(pixel_size * 1.5, 1e-7)
    for y_off in y_offsets:
        r = abs(y_off)
        ring = np.exp(-(rr - r) ** 2 / (2 * ring_width ** 2))
        # Weight by 1/(2*pi*r) for r>0 to keep total intensity correct
        # (larger rings spread same energy over more area)
        if r > ring_width:
            ring = ring / (2 * np.pi * r)
        image += ring

    return image


def _resample_fft_psf(fft_psf: np.ndarray, fft_half: float,
                      target_half: float, target_n: int) -> np.ndarray:
    """Resample an FFT PSF onto a target image grid.

    The FFT PSF covers [-fft_half, fft_half] on a grid of fft_psf.shape.
    This function samples it onto a [-target_half, target_half] grid of
    size (target_n, target_n) via bilinear interpolation.

    Args:
        fft_psf: 2D PSF array from compute_fft_psf.
        fft_half: Half-width in mm of the FFT PSF.
        target_half: Half-width in mm of the desired output.
        target_n: Output grid size.

    Returns:
        2D array of shape (target_n, target_n).
    """
    from scipy.ndimage import map_coordinates

    fft_n = fft_psf.shape[0]
    target_coords = np.linspace(-target_half, target_half, target_n)
    txx, tyy = np.meshgrid(target_coords, target_coords)

    # Map target coords to fractional FFT pixel indices
    fx = (txx + fft_half) / (2.0 * fft_half) * (fft_n - 1)
    fy = (tyy + fft_half) / (2.0 * fft_half) * (fft_n - 1)

    # Bilinear interpolation (order=1) for smooth resampling
    result = map_coordinates(fft_psf, [fy, fx], order=1, mode="constant",
                             cval=0.0)

    if result.max() > 0:
        result = result / result.max()
    return result


def _compute_focal_image(telescope: Telescope,
                         wavelength_nm: float = 550.0,
                         image_size_mm: float | None = None,
                         num_pixels: int = 512,
                         method: str = "analytical",
                         num_trace_rays: int = 501,
                         seeing_arcsec: float | None = None,
                         include_obstruction: bool = True,
                         ) -> tuple[np.ndarray | None, float, dict]:
    """Compute the focal plane image and associated metadata.

    Returns:
        Tuple of (image_array_or_None, half_size, info_dict).
        info_dict contains keys: wavelength_nm, f_ratio, airy_radius,
        rms_spot, max_spot, method, num_trace_rays, seeing_arcsec.
    """
    from scipy.signal import fftconvolve

    aperture_diameter = telescope.primary_diameter
    focal_length = telescope.focal_length

    y_offsets = _get_focal_offsets(telescope, method, num_trace_rays,
                                   include_obstruction=include_obstruction)
    if y_offsets is None:
        return None, 0.0, {}

    wavelength_mm = wavelength_nm * 1e-6
    f_ratio = focal_length / aperture_diameter
    airy_radius = 1.22 * wavelength_mm * f_ratio
    rms_spot = np.std(y_offsets)
    max_spot = np.max(np.abs(y_offsets))

    if image_size_mm is None:
        image_size_mm = max(airy_radius * 10, max_spot * 6, 0.001)

    half_size = image_size_mm / 2.0
    is_perfect_focus = rms_spot < 1e-10
    pixel_size = image_size_mm / num_pixels

    obs_ratio = telescope.obstruction_ratio if include_obstruction else 0.0

    # When spider vanes are present, use FFT-based PSF for realistic
    # diffraction spikes; otherwise use the faster analytical PSF.
    use_fft = telescope.spider_vanes > 0

    if is_perfect_focus:
        if use_fft:
            # Oversample so FFT has ~8 pixels per Airy radius (good enough
            # for smooth rendering without excessive memory use).
            base_pitch = wavelength_mm * f_ratio
            pixels_per_airy = airy_radius / base_pitch
            oversample = max(1, int(np.ceil(8.0 / pixels_per_airy)))
            oversample = min(oversample, 16)  # cap for memory
            pupil_n = 256  # pupil mask resolution (sufficient for vanes)
            fft_psf, fft_half = compute_fft_psf(
                aperture_diameter, focal_length, wavelength_mm, obs_ratio,
                telescope.spider_vanes, telescope.spider_vane_width,
                grid_size=pupil_n,
                oversample=oversample,
            )
            # Crop/resample FFT PSF to match our image extent
            image = _resample_fft_psf(fft_psf, fft_half, half_size,
                                      num_pixels)
        else:
            coords = np.linspace(-half_size, half_size, num_pixels)
            xx, yy = np.meshgrid(coords, coords)
            rr = np.sqrt(xx ** 2 + yy ** 2)
            image = compute_psf(rr, aperture_diameter, focal_length,
                                wavelength_mm, obs_ratio)
    else:
        geometric_image = _build_geometric_spot_2d(y_offsets, half_size,
                                                   num_pixels)
        if use_fft:
            # Use FFT PSF as the diffraction kernel
            kernel_half_size = max(airy_radius * 5, pixel_size * 3)
            kernel_n = min(num_pixels, 256)
            base_pitch = wavelength_mm * f_ratio
            pixels_per_airy = airy_radius / base_pitch
            oversample = max(1, int(np.ceil(8.0 / pixels_per_airy)))
            oversample = min(oversample, 16)
            pupil_n = 128
            fft_psf, fft_half = compute_fft_psf(
                aperture_diameter, focal_length, wavelength_mm, obs_ratio,
                telescope.spider_vanes, telescope.spider_vane_width,
                grid_size=pupil_n,
                oversample=oversample,
            )
            airy_kernel = _resample_fft_psf(fft_psf, fft_half,
                                            kernel_half_size, kernel_n)
            airy_kernel = airy_kernel / airy_kernel.sum()
        else:
            kernel_half_size = max(airy_radius * 5, pixel_size * 3)
            kernel_n = min(num_pixels, 256)
            kernel_coords = np.linspace(-kernel_half_size, kernel_half_size,
                                        kernel_n)
            kxx, kyy = np.meshgrid(kernel_coords, kernel_coords)
            kr = np.sqrt(kxx ** 2 + kyy ** 2)
            airy_kernel = compute_psf(kr, aperture_diameter, focal_length,
                                      wavelength_mm, obs_ratio)
            airy_kernel = airy_kernel / airy_kernel.sum()
        image = fftconvolve(geometric_image, airy_kernel, mode="same")

    if seeing_arcsec is not None and seeing_arcsec > 0:
        # Apply atmospheric seeing (Gaussian blur).
        # seeing_arcsec = FWHM of the seeing disk in arcseconds.
        # Convert to σ: σ = FWHM / 2.355
        plate_scale = 206265.0 / focal_length
        seeing_sigma_mm = (seeing_arcsec / 2.355) / plate_scale
        coords = np.linspace(-half_size, half_size, num_pixels)
        sxx, syy = np.meshgrid(coords, coords)
        seeing_kernel = np.exp(-(sxx ** 2 + syy ** 2) /
                               (2 * seeing_sigma_mm ** 2))
        seeing_kernel = seeing_kernel / seeing_kernel.sum()
        image = fftconvolve(image, seeing_kernel, mode="same")

    if image.max() > 0:
        image = image / image.max()

    info = dict(wavelength_nm=wavelength_nm, f_ratio=f_ratio,
                airy_radius=airy_radius, rms_spot=rms_spot,
                max_spot=max_spot, method=method,
                num_trace_rays=num_trace_rays,
                seeing_arcsec=seeing_arcsec,
                include_obstruction=include_obstruction)
    return image, half_size, info


def _draw_focal_image(ax: plt.Axes, telescope: Telescope,
                      title: str = "Point Spread Function",
                      wavelength_nm: float = 550.0,
                      image_size_mm: float | None = None,
                      num_pixels: int = 512,
                      method: str = "analytical",
                      num_trace_rays: int = 501,
                      seeing_arcsec: float | None = None,
                      colormap: str = "hot",
                      include_obstruction: bool = True) -> None:
    """Draw a focal plane image on the given axes.

    This is the core drawing helper used by both plot_focal_image and
    the comparison functions.
    """
    image, half_size, info = _compute_focal_image(
        telescope, wavelength_nm=wavelength_nm,
        image_size_mm=image_size_mm, num_pixels=num_pixels,
        method=method, num_trace_rays=num_trace_rays,
        seeing_arcsec=seeing_arcsec,
        include_obstruction=include_obstruction)

    if image is None:
        ax.set_title(title)
        ax.text(0.5, 0.5, "No fully traced rays", ha="center",
                va="center", transform=ax.transAxes)
        return

    ax.imshow(image, extent=[-half_size, half_size, -half_size, half_size],
              origin="lower", cmap=colormap, vmin=0, vmax=1)

    ax.set_xlabel("Position (mm)")
    ax.set_ylabel("Position (mm)")
    ax.set_title(title)

    method_label = ("Analytical" if info["method"] == "analytical"
                    else f"Traced ({info['num_trace_rays']} rays)")
    info_lines = [
        f"Airy disk radius: {info['airy_radius'] * 1000:.2f} \u00b5m",
        f"RMS geometric spot: {info['rms_spot'] * 1000:.2f} \u00b5m",
        f"\u03bb = {info['wavelength_nm']:.0f} nm | f/{info['f_ratio']:.1f}",
        f"Method: {method_label}",
    ]

    obs_ratio = telescope.obstruction_ratio
    if info.get("include_obstruction", True) and obs_ratio > 1e-6:
        info_lines.append(
            f"Obstruction: {obs_ratio:.0%} "
            f"(\u03b5={obs_ratio:.2f})"
        )
    elif not info.get("include_obstruction", True):
        info_lines.append("Obstruction: disabled")

    approx_lines = []
    if info["seeing_arcsec"] is None:
        approx_lines.append("No atmospheric seeing")
    else:
        info_lines.append(f"Seeing: {info['seeing_arcsec']:.1f}\"")
    approx_lines.append("Monochromatic")

    info_text = "\n".join(info_lines)
    approx_text = "Approx: " + "; ".join(approx_lines)

    ax.text(0.02, 0.02, info_text,
            transform=ax.transAxes, fontsize=9,
            verticalalignment="bottom", color="white",
            bbox=dict(boxstyle="round", facecolor="black", alpha=0.6))

    ax.text(0.02, 0.98, approx_text,
            transform=ax.transAxes, fontsize=7,
            verticalalignment="top", color="yellow", alpha=0.8)


def plot_focal_image(telescope: Telescope,
                     title: str = "Point Spread Function",
                     figsize: tuple[float, float] = (7, 7),
                     wavelength_nm: float = 550.0,
                     image_size_mm: float | None = None,
                     num_pixels: int = 512,
                     method: str = "analytical",
                     num_trace_rays: int = 501,
                     seeing_arcsec: float | None = None,
                     colormap: str = "hot",
                     save_path: str | None = None,
                     include_obstruction: bool = True) -> plt.Figure:
    """Render a physically-based simulated image at the focal plane.

    Combines two effects:
    1. Geometric spot — where rays actually land, reconstructed as a
       rotationally symmetric 2D pattern
    2. Diffraction PSF — Airy pattern from the circular aperture

    The geometric spot can be computed analytically from the mirror
    equation (default) or via numerical ray tracing.

    Optionally adds atmospheric seeing as a Gaussian blur.

    Physics notes (see PHYSICS.md for full inventory):
    - Monochromatic light at the specified wavelength
    - No detector noise or pixel sampling effects
    - 2D spot reconstructed assuming rotational symmetry

    Args:
        telescope: The telescope to image through.
        title: Plot title.
        figsize: Figure size in inches.
        wavelength_nm: Wavelength of light in nanometers (default 550nm green).
        image_size_mm: Width/height of the image in mm.
                       If None, auto-scales to show the full PSF.
        num_pixels: Resolution of the image grid.
        method: "analytical" (exact mirror formulas, default) or
                "traced" (numerical ray tracing).
        num_trace_rays: Number of rays (only used when method="traced").
        seeing_arcsec: Atmospheric seeing FWHM in arcseconds.
                       If None, no atmospheric blur is applied.
        colormap: Matplotlib colormap name.
        save_path: If provided, save the figure to this path.
        include_obstruction: If False, ignore secondary mirror
                             obstruction in the PSF and ray masking.

    Returns:
        The matplotlib Figure object.
    """
    fig, ax = plt.subplots(figsize=figsize)
    _draw_focal_image(ax, telescope, title=title,
                      wavelength_nm=wavelength_nm,
                      image_size_mm=image_size_mm,
                      num_pixels=num_pixels, method=method,
                      num_trace_rays=num_trace_rays,
                      seeing_arcsec=seeing_arcsec, colormap=colormap,
                      include_obstruction=include_obstruction)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


def plot_psf_profile(telescope: Telescope,
                     title: str = "Point Spread Function",
                     figsize: tuple[float, float] = (14, 7),
                     wavelength_nm: float = 550.0,
                     method: str = "analytical",
                     num_trace_rays: int = 501,
                     save_path: str | None = None,
                     include_obstruction: bool = True,
                     log_scale: bool | None = None) -> plt.Figure:
    """Plot the radial PSF profile showing diffraction and aberration effects.

    Shows three curves:
    1. Ideal Airy PSF — diffraction-limited (perfect optics)
    2. Geometric spot profile — from mirror geometry (no diffraction)
    3. Combined PSF — the actual telescope performance

    Also shows the Rayleigh resolution limit, key metrics, and the
    relevant physics formulas used.

    Args:
        telescope: The telescope to analyze.
        title: Plot title.
        figsize: Figure size in inches.
        wavelength_nm: Wavelength of light in nanometers.
        method: "analytical" (exact mirror formulas, default) or
                "traced" (numerical ray tracing).
        num_trace_rays: Number of rays (only used when method="traced").
        save_path: If provided, save the figure to this path.

    Returns:
        The matplotlib Figure object.
    """
    from scipy.signal import fftconvolve

    aperture_diameter = telescope.primary_diameter
    focal_length = telescope.focal_length

    y_offsets = _get_focal_offsets(telescope, method, num_trace_rays,
                                   include_obstruction=include_obstruction)
    if y_offsets is None:
        fig, ax = plt.subplots(figsize=figsize)
        ax.set_title(title)
        ax.text(0.5, 0.5, "No valid results", ha="center",
                va="center", transform=ax.transAxes)
        return fig

    wavelength_mm = wavelength_nm * 1e-6
    f_ratio = focal_length / aperture_diameter
    airy_radius = 1.22 * wavelength_mm * f_ratio
    rms_spot = np.std(y_offsets)
    max_spot = np.max(np.abs(y_offsets))

    # Build radial profiles
    r_max = max(airy_radius * 6, max_spot * 4, 0.001)
    r = np.linspace(0, r_max, 1000)

    # Detect perfect focus (e.g. parabolic + analytical: all offsets zero)
    is_perfect_focus = rms_spot < 1e-10

    obs_ratio = telescope.obstruction_ratio if include_obstruction else 0.0

    # 1. Ideal Airy PSF (diffraction only, with obstruction if enabled)
    airy_profile = compute_psf(r, aperture_diameter, focal_length,
                               wavelength_mm, obs_ratio)

    if is_perfect_focus:
        # No geometric aberration — combined PSF is exactly the Airy
        geo_profile = None
        combined_r = r
        combined_radial = airy_profile
    else:
        # 2. Geometric spot profile (from aberration offsets)
        radial_offsets = np.abs(y_offsets)
        bin_width = r_max / 200
        geo_profile = np.zeros_like(r)
        for r_off in radial_offsets:
            geo_profile += np.exp(-(r - r_off) ** 2 / (2 * bin_width ** 2))
        if geo_profile.max() > 0:
            geo_profile = geo_profile / geo_profile.max()

        # 3. Combined PSF (convolve geometric with Airy via 2D)
        n_px = 256
        half = r_max
        coords_1d = np.linspace(-half, half, n_px)
        cxx, cyy = np.meshgrid(coords_1d, coords_1d)
        crr = np.sqrt(cxx ** 2 + cyy ** 2)

        geo_2d = _build_geometric_spot_2d(y_offsets, half, n_px)
        airy_2d = compute_psf(crr, aperture_diameter, focal_length,
                              wavelength_mm, obs_ratio)
        airy_2d = airy_2d / airy_2d.sum()
        combined_2d = fftconvolve(geo_2d, airy_2d, mode="same")

        center = n_px // 2
        pixel_size = (2 * half) / n_px
        combined_radial = combined_2d[center, center:]
        combined_r = np.arange(len(combined_radial)) * pixel_size
        if combined_radial.max() > 0:
            combined_radial = combined_radial / combined_radial.max()

    # --- Layout ---
    # When log_scale is None: dual panel (linear + log) — the default used
    # by docs / standalone calls. When True/False: single-panel mode (used
    # by the tutorial tab so a toggle can show one scale at a time).
    fig = plt.figure(figsize=figsize)
    if log_scale is None:
        gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 0.8], wspace=0.35)
        ax1 = fig.add_subplot(gs[0])
        ax2 = fig.add_subplot(gs[1])
        ax3 = fig.add_subplot(gs[2])
    else:
        gs = fig.add_gridspec(1, 2, width_ratios=[1, 0.6], wspace=0.35)
        if log_scale:
            ax1 = None
            ax2 = fig.add_subplot(gs[0])
        else:
            ax1 = fig.add_subplot(gs[0])
            ax2 = None
        ax3 = fig.add_subplot(gs[1])

    plate_scale = 206265.0 / focal_length  # arcsec/mm
    def _um_to_arcsec(x_um):
        return x_um * plate_scale / 1000.0
    def _arcsec_to_um(x_arcsec):
        return x_arcsec * 1000.0 / plate_scale

    # Linear scale panel (may be skipped when log_scale=True)
    if ax1 is not None:
        if is_perfect_focus:
            ax1.plot(r * 1000, airy_profile, "b-", linewidth=2,
                     label="PSF = Airy (diffraction-limited)")
            ax1.plot([], [], "r--", linewidth=1.5,
                     label="Geometric: \u03b4(r) \u2014 perfect focus")
        else:
            ax1.plot(r * 1000, airy_profile, "b-", linewidth=1.5,
                     label="Ideal Airy (diffraction only)")
            ax1.plot(r * 1000, geo_profile, "r--", linewidth=1.5,
                     label="Geometric spot (no diffraction)")
            ax1.plot(combined_r * 1000, combined_radial, "k-", linewidth=2,
                     label="Combined PSF")
        ax1.axvline(airy_radius * 1000, color="gray", linestyle=":",
                    alpha=0.6,
                    label=f"Airy radius: {airy_radius * 1000:.2f} \u00b5m")
        ax1.set_xlabel("Radial distance (\u00b5m)")
        ax1.set_ylabel("Normalized intensity")
        ax1.set_title("Linear scale")
        ax1.legend(fontsize=7)
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(-0.05, 1.05)
        ax1_top = ax1.secondary_xaxis('top',
                                       functions=(_um_to_arcsec, _arcsec_to_um))
        ax1_top.set_xlabel("Angular distance (arcsec)", fontsize=8)

    # Log scale panel (may be skipped when log_scale=False)
    if ax2 is not None:
        if is_perfect_focus:
            ax2.semilogy(r * 1000, np.clip(airy_profile, 1e-6, None), "b-",
                         linewidth=2, label="PSF = Airy")
        else:
            ax2.semilogy(r * 1000, np.clip(airy_profile, 1e-6, None), "b-",
                         linewidth=1.5, label="Ideal Airy")
            ax2.semilogy(r * 1000, np.clip(geo_profile, 1e-6, None), "r--",
                         linewidth=1.5, label="Geometric spot")
            ax2.semilogy(combined_r * 1000,
                         np.clip(combined_radial, 1e-6, None),
                         "k-", linewidth=2, label="Combined PSF")
        ax2.axvline(airy_radius * 1000, color="gray", linestyle=":",
                    alpha=0.6)
        ax2.set_xlabel("Radial distance (\u00b5m)")
        ax2.set_ylabel("Normalized intensity (log)")
        ax2.set_title("Log scale")
        ax2.legend(fontsize=7)
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim(1e-4, 1.5)
        ax2_top = ax2.secondary_xaxis('top',
                                       functions=(_um_to_arcsec, _arcsec_to_um))
        ax2_top.set_xlabel("Angular distance (arcsec)", fontsize=8)

    # --- Formula & metrics panel ---
    ax3.axis("off")

    method_label = ("Analytical" if method == "analytical"
                    else f"Traced ({num_trace_rays} rays)")
    rayleigh_arcsec = rayleigh_criterion_arcsec(
        wavelength_nm * 1e-9, aperture_diameter * 1e-3, obs_ratio)

    # Strehl = geometric Strehl (from RMS spot) \u00d7 obstruction Strehl (1-\u03b5\u00b2)\u00b2
    # The previous code used only the geometric term, so for any unaberrated
    # primary (rms=0) it returned 1.0 even with a 30% central obstruction.
    strehl_geo = _estimate_strehl(rms_spot, airy_radius)
    strehl_obs = (1.0 - obs_ratio ** 2) ** 2
    strehl = strehl_geo * strehl_obs

    # Airy radius \u2014 convert to arcsec to match Rayleigh's units
    plate_scale_arcsec_per_mm = 206265.0 / focal_length
    airy_radius_arcsec = airy_radius * plate_scale_arcsec_per_mm

    # Metrics block
    if include_obstruction:
        obs_line = (f"\u03b5 = {obs_ratio:.2f} ({obs_ratio:.0%} obstruction)\n"
                    f"  geo Strehl = {strehl_geo:.3f}\n"
                    f"  obs Strehl = {strehl_obs:.3f}  (1-\u03b5\u00b2)\u00b2")
    else:
        obs_line = "Obstruction: disabled"
    metrics_text = (
        f"D = {aperture_diameter:.0f} mm,  f/{f_ratio:.1f}\n"
        f"\u03bb = {wavelength_nm:.0f} nm\n"
        f"{obs_line}\n"
        f"Airy radius: {airy_radius_arcsec:.3f}\" "
        f"({airy_radius * 1000:.2f} \u00b5m)\n"
        f"Rayleigh limit: {rayleigh_arcsec:.3f}\"\n"
        f"RMS geo spot: {rms_spot * 1000:.2f} \u00b5m\n"
        f"Strehl \u2248 {strehl:.3f}  (geo \u00d7 obs)\n"
        f"Method: {method_label}"
    )
    ax3.text(0.05, 0.97, "Metrics", fontsize=10, fontweight="bold",
             transform=ax3.transAxes, va="top")
    ax3.text(0.05, 0.90, metrics_text, fontsize=9,
             transform=ax3.transAxes, va="top", family="monospace",
             bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.9))

    # Formulas block — rendered line-by-line with a manual background
    # (matplotlib bbox doesn't size correctly around multi-line mathtext)
    from matplotlib.patches import FancyBboxPatch

    if obs_ratio > 1e-6:
        formulas = [
            (r"$I = \left[\frac{1}{1-\varepsilon^2}\right]^2"
             r"\left[\frac{2J_1(x)}{x}"
             r" - \varepsilon^2\frac{2J_1(\varepsilon x)}"
             r"{\varepsilon x}\right]^2$"),
            r"$x = \frac{\pi D r}{\lambda f}$,"
            r"  $\varepsilon = D_{sec}/D_{pri}$",
            r"Rayleigh:  $\theta = 1.22\,\frac{\lambda}{D}$",
        ]
    else:
        formulas = [
            (r"$I(r) = \left[\frac{2\,J_1(x)}{x}\right]^2$,"
             r"  $x = \frac{\pi D r}{\lambda f}$"),
            r"First zero:  $r_1 = 1.22\,\frac{\lambda f}{D}$",
            r"Rayleigh:  $\theta = 1.22\,\frac{\lambda}{D}$",
        ]
    if telescope.primary_type == "spherical":
        formulas.append(
            r"TSA (3rd order):  $\varepsilon(h) \approx \frac{-h^3}{8f^2}$"
        )
    formulas.append(
        r"Strehl $\approx \frac{1}{1+(\pi\sigma/2r_1)^2}$"
    )

    # Draw background box sized to content
    line_step = 0.065
    box_top = 0.37
    box_bottom = box_top - line_step * len(formulas) - 0.03
    formula_bg = FancyBboxPatch(
        (0.01, box_bottom), 0.97, box_top - box_bottom,
        boxstyle="round,pad=0.015",
        facecolor="aliceblue", edgecolor="lightsteelblue",
        alpha=0.9, transform=ax3.transAxes, zorder=0,
    )
    ax3.add_patch(formula_bg)

    ax3.text(0.05, 0.42, "Formulas", fontsize=10, fontweight="bold",
             transform=ax3.transAxes, va="top")

    y = box_top - 0.02
    for formula in formulas:
        ax3.text(0.06, y, formula, fontsize=8.5,
                 transform=ax3.transAxes, va="top", zorder=1)
        y -= line_step

    fig.suptitle(title, fontsize=13)

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


def _estimate_strehl(rms_spot: float, airy_radius: float) -> float:
    """Estimate the Strehl ratio from the geometric spot size.

    The Strehl ratio is the ratio of peak intensity to the peak of
    a perfect (diffraction-limited) PSF. A value of 1.0 is perfect;
    values above 0.8 are considered "diffraction-limited."

    NOTE: This is a rough approximation based on the Marechal
    approximation. A precise Strehl calculation requires wavefront
    error analysis, which is not yet implemented (see PHYSICS.md).
    """
    if airy_radius < 1e-12:
        return 0.0
    # Approximate: Strehl ~ 1 / (1 + (pi * rms_spot / (2 * airy_radius))^2)
    ratio = np.pi * rms_spot / (2 * airy_radius)
    return 1.0 / (1.0 + ratio ** 2)


# ── Per-panel physics resolution ─────────────────────────────────────


_PHYSICS_KEYS = {"wavelength_nm", "method", "seeing_arcsec", "include_obstruction"}


def _resolve_physics_params(
    n: int,
    physics_params: list[dict] | None,
    wavelength_nm: float,
    method: str,
    seeing_arcsec: float | None,
    include_obstruction: bool,
) -> list[dict]:
    """Build a list of per-panel physics dicts for comparison functions.

    When *physics_params* is ``None`` the scalar kwargs are broadcast to
    every panel (backward-compatible path).  When provided, each dict is
    merged with the scalar defaults so callers only need to specify
    overrides.

    Returns:
        List of length *n*, each dict having keys:
        ``wavelength_nm``, ``method``, ``seeing_arcsec``,
        ``include_obstruction``.
    """
    defaults = dict(
        wavelength_nm=wavelength_nm,
        method=method,
        seeing_arcsec=seeing_arcsec,
        include_obstruction=include_obstruction,
    )

    if physics_params is None:
        return [defaults.copy() for _ in range(n)]

    if len(physics_params) != n:
        raise ValueError(
            f"physics_params has {len(physics_params)} entries but "
            f"{n} telescopes were provided"
        )

    resolved = []
    for pp in physics_params:
        merged = defaults.copy()
        merged.update(pp)
        resolved.append(merged)
    return resolved


# ── Comparison functions ─────────────────────────────────────────────


def plot_ray_trace_comparison(
    telescopes: list[Telescope],
    labels: list[str],
    num_display_rays: int = 11,
    figsize_per_panel: tuple[float, float] = (7, 8),
    save_path: str | None = None,
) -> plt.Figure:
    """Plot ray trace diagrams side by side for multiple telescopes.

    Args:
        telescopes: List of telescope objects to compare.
        labels: Display label for each telescope.
        num_display_rays: Number of rays to trace per telescope.
        figsize_per_panel: (width, height) per subplot panel.
        save_path: If provided, save the figure to this path.

    Returns:
        The matplotlib Figure object.
    """
    from telescope_sim.source import create_parallel_rays

    n = len(telescopes)
    fig, axes = plt.subplots(
        1, n,
        figsize=(figsize_per_panel[0] * n, figsize_per_panel[1]),
        squeeze=False,
    )

    for i, (telescope, label) in enumerate(zip(telescopes, labels)):
        ax = axes[0, i]
        rays = create_parallel_rays(
            num_rays=num_display_rays,
            aperture_diameter=telescope.primary_diameter,
            entry_height=telescope.tube_length * 1.15,
        )
        telescope.trace_rays(rays)
        components = telescope.get_components_for_plotting()
        _draw_ray_trace(ax, rays, components, title=label)

    # Shared axis limits so telescope sizes are visually comparable
    all_xlims = [axes[0, i].get_xlim() for i in range(n)]
    all_ylims = [axes[0, i].get_ylim() for i in range(n)]
    shared_xlim = (min(lo for lo, _ in all_xlims), max(hi for _, hi in all_xlims))
    shared_ylim = (min(lo for lo, _ in all_ylims), max(hi for _, hi in all_ylims))
    for i in range(n):
        axes[0, i].set_xlim(shared_xlim)
        axes[0, i].set_ylim(shared_ylim)

    fig.suptitle("Ray Trace Comparison", fontsize=14)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


def plot_polychromatic_ray_trace(
    telescope: Telescope,
    num_display_rays: int = 5,
    wavelengths: dict[str, float] | None = None,
    figsize: tuple[float, float] = (14, 8),
    save_path: str | None = None,
    focus_wavelength_nm: float | None = None,
    show_inset: bool = True,
    idealize_sa: bool = False,
) -> plt.Figure:
    """Plot a polychromatic ray trace showing R/G/B colored rays.

    Traces the telescope at multiple wavelengths and overlays the
    ray paths with wavelength-appropriate colors.  For refracting
    telescopes this reveals chromatic aberration (different focal
    points for different colors).

    Args:
        telescope: The telescope to trace.
        num_display_rays: Number of rays per wavelength.
        wavelengths: Dict mapping label to wavelength in nm.
            Defaults to R/G/B Fraunhofer lines.
        figsize: Figure size in inches.
        save_path: If provided, save the figure to this path.
        idealize_sa: When True, draw each wavelength's post-lens rays as
            idealised convergence to that wavelength's focal point — i.e.
            spherical aberration is removed so ONLY the chromatic focal
            shift between colours remains. This is a deliberate teaching
            idealisation (flagged on the plot); the default (False) draws
            the real refracted ray paths, so a spherical singlet shows its
            true SA. Used by the chromatic-aberration tutorial so the
            singlet/achromat/APO comparison isolates colour.

    Returns:
        The matplotlib Figure object.
    """
    from telescope_sim.source import create_parallel_rays
    from telescope_sim.physics.ray import (
        CHROMATIC_WAVELENGTHS, wavelength_to_color,
    )

    if wavelengths is None:
        wavelengths = CHROMATIC_WAVELENGTHS

    # Single full-width axes; legend & focal inset float as overlays
    fig, ax = plt.subplots(figsize=figsize)
    fig.subplots_adjust(left=0.06, right=0.98, top=0.95, bottom=0.05)

    # Draw optics using the green (design) wavelength rays first
    green_wl = wavelengths.get("G", 550.0)
    green_rays = create_parallel_rays(
        num_rays=num_display_rays,
        aperture_diameter=telescope.primary_diameter,
        entry_height=telescope.tube_length * 1.15,
        wavelength_nm=green_wl,
    )
    telescope.trace_rays(green_rays)
    components = telescope.get_components_for_plotting()

    # Draw the telescope structure (optics + tube) without rays.
    # Title includes the f-ratio so it's visible as the user adjusts the
    # focal length tweak — chromatic blur scales as 1/f-ratio for a
    # singlet, so this is the most pedagogically relevant scalar.
    obj_label = getattr(telescope, "objective_type", "")
    f_ratio = telescope.focal_length / telescope.primary_diameter
    title = (f"Polychromatic Ray Trace — "
             f"{telescope.primary_diameter:.0f} mm f/{f_ratio:.1f}"
             + (f", {obj_label}" if obj_label else ""))
    _draw_ray_trace(ax, [], components,
                    title=title,
                    ray_color="gold", show_tube=True)

    # Tighten x-limits to the telescope aperture (remove excess whitespace)
    pad = telescope.primary_diameter * 0.15
    ax.set_xlim(-telescope.primary_diameter / 2 - pad,
                telescope.primary_diameter / 2 + pad)
    ax.margins(x=0, y=0.02)

    # Trace and draw rays for each wavelength.
    # Draw B first, G next, R last so longer wavelengths (red) are on top
    # and visible — otherwise blue (drawn last) hides the others because
    # ray paths overlap almost perfectly until near the focal plane.
    draw_order = sorted(wavelengths.items(), key=lambda kv: kv[1])  # short λ first
    linewidths = {"B": 1.8, "G": 1.2, "R": 0.8}  # wider underneath, thinner on top

    all_focal_points = {}  # label -> (x, y) for inset calculation

    # Two-pass strategy: the ray-traced focal y for the design wavelength
    # (550 nm) is the visual reference; per-wavelength shifts come from
    # the analytical `chromatic_defocus` function. This guarantees
    # pedagogically-monotonic ordering across objective types (the
    # thin-lens design code can otherwise produce apo-doublet residuals
    # larger than achromat residuals).
    g_ref_rays = create_parallel_rays(
        num_rays=num_display_rays,
        aperture_diameter=telescope.primary_diameter,
        entry_height=telescope.tube_length * 1.15,
        wavelength_nm=550.0,
    )
    telescope.trace_rays(g_ref_rays)
    g_axis_crossings = []
    for r in g_ref_rays:
        if len(r.history) < 2: continue
        p0 = np.array(r.history[-2]); p1 = np.array(r.history[-1])
        dx = p1[0] - p0[0]
        if abs(dx) < 1e-9: continue
        tt = -p0[0] / dx
        g_axis_crossings.append(p0[1] + tt * (p1[1] - p0[1]))
    g_focal_y = (float(np.mean(g_axis_crossings))
                 if g_axis_crossings else None)

    for label, wl in draw_order:
        color = wavelength_to_color(wl)
        lw = linewidths.get(label, 1.0)
        rays = create_parallel_rays(
            num_rays=num_display_rays,
            aperture_diameter=telescope.primary_diameter,
            entry_height=telescope.tube_length * 1.15,
            wavelength_nm=wl,
        )
        telescope.trace_rays(rays)

        # Per-wavelength focal y = green reference + analytical chromatic
        # shift. The green reference is the ACTUAL ray-traced focal y at
        # 550 nm (see g_focal_y above). The shift comes from
        # `chromatic_defocus()` which encodes the textbook ordering for
        # each objective type (singlet > achromat > apo-d > apo-t) and
        # guarantees correct visual ordering in the inset.
        if g_focal_y is None:
            focal_y = None
        else:
            defocus_mm = chromatic_defocus(telescope, wl)
            # Defocus is the focal-length shift from design (positive =
            # longer f); in our coordinate (lens at +y, focal plane below),
            # a longer f means focal point shifts to more-negative y.
            focal_y = g_focal_y - defocus_mm

        # Extension length past focal point so the user sees the rays
        # converge AND diverge — illustrates that picking a focal plane
        # means other wavelengths are spread there.
        extension_length = telescope.tube_length * 0.15

        for ray in rays:
            if len(ray.history) < 2:
                continue
            path = np.array(ray.history)
            if idealize_sa and focal_y is not None:
                # Idealised convergence: keep the real path through the lens
                # (history ends at the lens exit surface), then redirect this
                # ray straight to the wavelength's focal point and STOP there.
                # All rays of a wavelength meet cleanly at one point — spherical
                # aberration removed, chromatic focal shift preserved. We do NOT
                # extend past the focus here: three colours diverging past three
                # nearby foci produced a confusing red/green/blue fan below the
                # focal plane (R3.6b). The converge→diverge crossover is shown
                # instead in the paired focal-region zoom on the after side.
                focal_pt = np.array([0.0, focal_y])
                path = np.vstack([path, focal_pt])
            else:
                # Real refracted path: extend the last segment forward past
                # the focal plane (a singlet then shows its true SA spread).
                p_last = path[-1]
                p_prev = path[-2]
                direction = p_last - p_prev
                norm = float(np.linalg.norm(direction))
                if norm > 0:
                    unit = direction / norm
                    p_ext = p_last + unit * extension_length
                    path = np.vstack([path, p_ext])
            ax.plot(path[:, 0], path[:, 1],
                    color=color, alpha=0.8, linewidth=lw)

        if focal_y is not None:
            focal = np.array([0.0, focal_y])
            all_focal_points[label] = focal
            # Reduced marker opacity so the overlaid star doesn't
            # occlude the ray bundles crossing through it.
            ax.plot(focal[0], focal[1], "*", color=color,
                    markersize=10, label=f"{label} ({wl:.0f}nm)",
                    alpha=0.55, zorder=5)

    # Remove any auto-legend that _draw_ray_trace may have added
    if ax.get_legend() is not None:
        ax.get_legend().remove()

    # Legend OUT of the ray trace, below the plot (R3.6a) — it previously sat
    # upper-right on top of the lens/rays. The plot is tall and narrow, so a
    # horizontal legend under the axes uses otherwise-empty canvas.
    ax.legend(fontsize="small", loc="upper center",
              bbox_to_anchor=(0.5, -0.06), ncol=4, frameon=True,
              fancybox=True, framealpha=0.9)

    # Numerical focal-position readout in the RIGHT-side whitespace (the
    # converging cone is narrow at mid-height, leaving the flanks empty), so
    # it no longer overlaps the rays. Δz is along the optical axis (y here).
    if len(all_focal_points) >= 1:
        focals = np.array(list(all_focal_points.values()))
        ref = focals[:, 1].mean()
        readout_lines = ["Focal offsets", "(Δz on axis, mm):"]
        for label, fp in all_focal_points.items():
            dz = fp[1] - ref
            readout_lines.append(f"  {label}: {dz:+.3f}")
        ax.text(0.985, 0.55, "\n".join(readout_lines),
                transform=ax.transAxes, fontsize=7,
                verticalalignment="center", horizontalalignment="right",
                fontfamily="monospace",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                          alpha=0.85, edgecolor="gray"))

    # Flag the teaching idealisation so the user knows the within-colour
    # convergence is not real physics (spherical aberration suppressed).
    # Placed in the LEFT-side whitespace (mid-height) so it doesn't pile up
    # with the focal-plane label / zoom box in the crowded focal region.
    if idealize_sa:
        ax.text(0.015, 0.42,
                "Idealised: spherical\n"
                "aberration removed —\n"
                "each colour converges\n"
                "to a point so only the\n"
                "chromatic focal shift\n"
                "is shown.",
                transform=ax.transAxes, fontsize=7,
                verticalalignment="center", horizontalalignment="left",
                style="italic", color="#444",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#fffbe6",
                          alpha=0.9, edgecolor="#ccaa44"))

    # Draw a horizontal dashed line at the user's chosen focal plane so
    # the user can see WHICH plane the AFTER-side plots are taken at.
    # Only added when focus_wavelength_nm is supplied (the tutorial
    # passes this from the focal-plane combo).
    if (focus_wavelength_nm is not None
            and g_focal_y is not None):
        focus_defocus = chromatic_defocus(telescope, focus_wavelength_nm)
        focus_plane_y = g_focal_y - focus_defocus
        # Determine color from the chosen wavelength
        from telescope_sim.physics.ray import wavelength_to_color
        focus_color = wavelength_to_color(focus_wavelength_nm)
        ax.axhline(focus_plane_y, color=focus_color, linestyle="--",
                   linewidth=1.5, alpha=0.6, zorder=4)
        ax.text(0.02, focus_plane_y, f"  Focal plane (focus at {focus_wavelength_nm:.0f} nm)",
                color=focus_color, fontsize=8, fontweight="bold",
                transform=ax.get_yaxis_transform(),
                verticalalignment="bottom", alpha=0.9, zorder=5)

    # Dashed box marking the focal region that the after-side "Zoomed view of
    # the focal region" panel magnifies (R3.6c). Its extent matches
    # _draw_focal_region_zoom's limits so the two plots line up.
    if g_focal_y is not None and len(all_focal_points) >= 1:
        from matplotlib.patches import Rectangle
        focal_ys = [fp[1] for fp in all_focal_points.values()]
        spread_y = max((max(focal_ys) - min(focal_ys)),
                       telescope.primary_diameter * 0.02)
        box_half_y = spread_y * 2.5
        box_half_x = telescope.primary_diameter * 0.08
        ax.add_patch(Rectangle(
            (-box_half_x, g_focal_y - box_half_y),
            2 * box_half_x, 2 * box_half_y,
            fill=False, edgecolor="0.35", linestyle="--", linewidth=1.2,
            alpha=0.8, zorder=6))
        ax.text(box_half_x, g_focal_y + box_half_y,
                " zoomed →\n (focal-plane\n  view)",
                fontsize=6.5, color="0.35", ha="left", va="top", zorder=6)

    # Focal-region inset embedded inside the main axes (wider, shorter so
    # the colour separation is readable; horizontal layout matches the
    # along-axis chromatic spread which is the dominant signal)
    if show_inset and len(all_focal_points) >= 2:
        ax_inset = ax.inset_axes([0.42, 0.03, 0.56, 0.28])
        ax_inset.patch.set_facecolor("white")
        ax_inset.patch.set_alpha(0.9)

        focals = np.array(list(all_focal_points.values()))
        center_x = focals[:, 0].mean()
        center_y = focals[:, 1].mean()
        # Chromatic spread is along the optical axis (y); transverse
        # spread (x) is essentially zero by construction (all focal_x=0).
        spread_x = telescope.primary_diameter * 0.02
        spread_y = max(np.ptp(focals[:, 1]), telescope.primary_diameter * 0.02)
        # Asymmetric margins: tight along chromatic-spread (y, optical axis)
        # so the focal-shift difference fills the inset; loose along x.
        margin_x = 4.0
        margin_y = 2.5

        ax_inset.set_xlim(center_x - spread_x * margin_x,
                          center_x + spread_x * margin_x)
        ax_inset.set_ylim(center_y - spread_y * margin_y,
                          center_y + spread_y * margin_y)
        # Longitudinal chromatic spread along the optical axis (y in the 2D
        # plot — chromatic focus shift, not transverse blur).
        long_spread_mm = np.ptp(focals[:, 1]) if len(focals) > 1 else 0.0
        obj_type = getattr(telescope, "objective_type", "")
        obj_label = f"  |  {obj_type}" if obj_type else ""
        # Δz is the axial (longitudinal) focal-shift along the optical
        # axis between the most-shifted and least-shifted of the three
        # R/G/B focal-plane positions — NOT a transverse blur.
        inset_title = (f"Focal region{obj_label}  |  "
                        f"axial focal-shift Δz: {long_spread_mm:.3f} mm")
        ax_inset.set_title(inset_title, fontsize=7)
        ax_inset.tick_params(labelsize=6)

        # Redraw rays in the inset. Extend each ray's last segment FORWARD
        # to the per-wavelength focal point so the converging bundle visibly
        # meets at the wavelength's star marker (otherwise the ray history
        # ends at the trace exit boundary, which can be far from the inset's
        # zoom window when chromatic spread is small).
        for label, wl in draw_order:
            color = wavelength_to_color(wl)
            lw = linewidths.get(label, 1.0)
            rays = create_parallel_rays(
                num_rays=num_display_rays,
                aperture_diameter=telescope.primary_diameter,
                entry_height=telescope.tube_length * 1.15,
                wavelength_nm=wl,
            )
            telescope.trace_rays(rays)
            focal_y = (all_focal_points[label][1]
                       if label in all_focal_points else None)
            for ray in rays:
                if len(ray.history) < 2:
                    continue
                path = np.array(ray.history)
                # Extend each ray PAST its focal point so the inset shows
                # the converge → diverge crossover: rays cross at their
                # focus, then spread again. Length = the inset's y-extent
                # so we visibly traverse the focal region in both
                # directions.
                if focal_y is not None and len(path) >= 2:
                    p_last = path[-1]
                    p_prev = path[-2]
                    seg = p_last - p_prev
                    norm = float(np.linalg.norm(seg))
                    if norm > 0:
                        unit = seg / norm
                        # Extension equal to the inset's full y-extent
                        # (2× the spread × margin) so rays traverse the
                        # entire focal region.
                        ext_len = 2.0 * spread_y * margin_y
                        # First extend to focal_y (if not already there),
                        # then continue past it.
                        dy = seg[1]
                        if dy != 0:
                            t_to_focal = (focal_y - p_last[1]) / dy
                            if 0 < t_to_focal < 5.0:
                                tip_focal = p_last + t_to_focal * seg
                                path = np.vstack([path, tip_focal])
                                p_last = tip_focal
                        tip_past = p_last + unit * ext_len
                        path = np.vstack([path, tip_past])
                ax_inset.plot(path[:, 0], path[:, 1],
                              color=color, alpha=0.8, linewidth=lw)

            if label in all_focal_points:
                fp = all_focal_points[label]
                # Reduced opacity so the marker doesn't occlude the rays
                # crossing through it.
                ax_inset.plot(fp[0], fp[1], "*", color=color,
                              markersize=12, alpha=0.55, zorder=5)

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


def plot_chromatic_focal_planes(
    telescope: Telescope,
    num_pixels: int = 256,
    figsize: tuple[float, float] = (12, 4.5),
    save_path: str | None = None,
    focus_wavelength_nm: float = 550.0,
    fixed_xlim_arcsec: float = 120.0,
) -> plt.Figure:
    """Overlay three 1D radial PSF profiles (R, G, B) on a single panel.

    The `focus_wavelength_nm` parameter chooses which channel is sharp.
    For an achromat, choosing R or B picks the F-or-C focal plane (where
    the achromat brings two wavelengths together) — G becomes the
    defocused channel and you see the secondary spectrum's residual.
    Choosing G focuses at the design wavelength — R and B become the
    defocused channels.

    `fixed_xlim_arcsec` locks the x-axis range across objective toggles
    so the singlet/apo halo-width contrast is visually obvious (the
    singlet runs off the panel, the apo collapses to a vertical line at
    zero). Pass a different value to override.

    The geometric flat-top shape of each defocused profile is physically
    correct: it's the Airy core convolved with a uniform defocus disk
    (geometric-optics limit). Defocus is not Gaussian.
    """
    from scipy.signal import fftconvolve
    from telescope_sim.physics.diffraction import compute_psf as _airy_psf

    f_ratio = telescope.focal_length / telescope.primary_diameter
    plate_scale = 206265.0 / telescope.focal_length  # arcsec/mm

    obs_ratio = telescope.obstruction_ratio
    include_obs = telescope.obstruction_ratio > 0.0

    channel_wls = [("R", 656.3, "red"),
                   ("G", 550.0, "green"),
                   ("B", 486.1, "blue")]

    # Defocus per channel is computed RELATIVE TO the user's focus
    # wavelength. chromatic_defocus(λ) returns the design-relative shift;
    # subtract chromatic_defocus(focus_wl) to re-zero on the user's
    # chosen focal plane.
    focus_defocus_mm = chromatic_defocus(telescope, focus_wavelength_nm)

    def _defocus_relative(wl_nm):
        return chromatic_defocus(telescope, wl_nm) - focus_defocus_mm

    # Determine the radial extent that comfortably covers the largest
    # halo. defocus_radius_mm = |Δf| / (2F). Cap at a sensible minimum
    # so APO designs (tiny halo) still show a visible profile.
    max_defocus_mm = max(abs(_defocus_relative(wl))
                         for _, wl, _ in channel_wls)
    max_defocus_radius_mm = max_defocus_mm / (2.0 * f_ratio)
    airy_mm_design = 1.22 * 550.0e-6 * f_ratio
    half_extent_mm = max(max_defocus_radius_mm * 1.4,
                         airy_mm_design * 8.0)
    r_mm = np.linspace(0.0, half_extent_mm, 600)
    r_arcsec = r_mm * plate_scale

    # 1D PSF for each channel: radial cross-section of the wavelength-
    # dependent Airy convolved with its defocus disk.
    n_psf = 257
    coords = np.linspace(-half_extent_mm, half_extent_mm, n_psf)
    cxx, cyy = np.meshgrid(coords, coords)
    crr = np.sqrt(cxx ** 2 + cyy ** 2)
    center = n_psf // 2
    profiles = {}
    for label, wl, _ in channel_wls:
        wl_mm = wl * 1e-6
        airy_2d = _airy_psf(crr, telescope.primary_diameter,
                            telescope.focal_length, wl_mm,
                            obs_ratio if include_obs else 0.0)
        defocus_mm = _defocus_relative(wl)
        defocus_radius_mm = abs(defocus_mm) / (2.0 * f_ratio)
        pixel_mm = 2.0 * half_extent_mm / n_psf
        defocus_radius_pix = defocus_radius_mm / pixel_mm
        if defocus_radius_pix > 0.5:
            cc = np.arange(n_psf) - center
            cx, cy = np.meshgrid(cc, cc)
            rrp = np.sqrt(cx ** 2 + cy ** 2)
            disc = (rrp <= defocus_radius_pix).astype(float)
            disc_sum = disc.sum()
            if disc_sum > 0:
                disc /= disc_sum
            psf_2d = fftconvolve(airy_2d, disc, mode="same")
        else:
            psf_2d = airy_2d
        peak = psf_2d.max()
        if peak > 0:
            psf_2d = psf_2d / peak
        # Radial cut from centre outward
        profile = psf_2d[center, center:]
        # Re-sample onto r_mm (psf_2d already at the same spacing)
        # by truncating/padding
        if len(profile) >= len(r_mm):
            profiles[label] = profile[:len(r_mm)]
        else:
            padded = np.zeros(len(r_mm))
            padded[:len(profile)] = profile
            profiles[label] = padded

    # Two-row layout: focal-region ray-trace zoom on TOP, 1D radial
    # profiles BELOW. This pulls the zoomed ray trace out of the main
    # ray-trace's inset and gives it room to display the converge →
    # diverge crossover clearly. The zoom is given the larger share of
    # vertical space — the converge/diverge geometry is the primary
    # signal here; the 1D profiles below are confirmatory.
    fig = plt.figure(figsize=(figsize[0], figsize[1] * 1.8))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.5, 1.0], hspace=0.32)
    ax_zoom = fig.add_subplot(gs[0])
    ax = fig.add_subplot(gs[1])

    _draw_focal_region_zoom(ax_zoom, telescope,
                            focus_wavelength_nm=focus_wavelength_nm)

    for label, wl, color in channel_wls:
        prof = profiles[label]
        defocus_mm = _defocus_relative(wl)
        defocus_radius_arcsec = (
            abs(defocus_mm) / (2.0 * f_ratio) * plate_scale
        )
        ax.plot(r_arcsec, prof, color=color, linewidth=2.0,
                label=f"{label} {wl:.0f} nm  (Δf={defocus_mm:+.3f} mm, "
                      f"halo r≈{defocus_radius_arcsec:.2f}\")")

    obj = getattr(telescope, "objective_type", "")
    ax.set_xlim(0, fixed_xlim_arcsec)
    ax.set_ylim(-0.02, 1.05)
    ax.set_xlabel("Radial distance (arcsec)")
    ax.set_ylabel("Normalised intensity (peak = 1.0)")
    obj_label = f" — {obj}" if obj else ""
    ax.set_title(
        f"Chromatic radial profiles (focus at {focus_wavelength_nm:.0f} nm) "
        f"— {telescope.primary_diameter:.0f} mm f/{f_ratio:.1f}{obj_label}",
        fontsize=10)
    ax.legend(fontsize=8, framealpha=0.85)
    ax.grid(True, alpha=0.3)
    airy_arcsec = airy_mm_design * plate_scale
    if airy_arcsec <= fixed_xlim_arcsec:
        ax.axvline(airy_arcsec, color="gray", linestyle=":",
                   linewidth=1.0, alpha=0.6)
        ax.text(airy_arcsec, 1.02, f"  Airy {airy_arcsec:.2f}\"",
                fontsize=7, color="gray", ha="left", va="bottom")

    ax.text(0.99, 0.02,
            "Geometric defocus model: Airy core × uniform disk\n"
            "(flat-top is physically correct, not Gaussian)",
            transform=ax.transAxes, fontsize=7, color="dimgray",
            ha="right", va="bottom", style="italic",
            bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
                      edgecolor="lightgray", alpha=0.8))

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def _draw_focal_region_zoom(ax, telescope, focus_wavelength_nm=None,
                             num_display_rays: int = 5,
                             wavelengths: dict | None = None) -> None:
    """Draw a wide zoomed view of the per-wavelength focal region.

    Used by `plot_chromatic_focal_planes` as the top subpanel — shows
    the R/G/B ray bundles converging at their per-wavelength focal
    points and diverging past them, with a marker on the user's
    chosen focal plane.
    """
    from telescope_sim.source import create_parallel_rays
    from telescope_sim.physics.ray import (
        CHROMATIC_WAVELENGTHS, wavelength_to_color,
    )
    if wavelengths is None:
        wavelengths = CHROMATIC_WAVELENGTHS

    # Find the green-reference focal y first (anchor for the analytical
    # per-wavelength shifts)
    g_ref_rays = create_parallel_rays(
        num_rays=num_display_rays,
        aperture_diameter=telescope.primary_diameter,
        entry_height=telescope.tube_length * 1.15,
        wavelength_nm=550.0,
    )
    telescope.trace_rays(g_ref_rays)
    g_axis_crossings = []
    for r in g_ref_rays:
        if len(r.history) < 2:
            continue
        p0 = np.array(r.history[-2]); p1 = np.array(r.history[-1])
        dx = p1[0] - p0[0]
        if abs(dx) < 1e-9:
            continue
        tt = -p0[0] / dx
        g_axis_crossings.append(p0[1] + tt * (p1[1] - p0[1]))
    g_focal_y = (float(np.mean(g_axis_crossings))
                 if g_axis_crossings else 0.0)

    all_focal = {}
    for label, wl in wavelengths.items():
        dz = chromatic_defocus(telescope, wl)
        all_focal[label] = g_focal_y - dz

    # Per-wavelength rays: draw thin bundles converging then diverging
    spread_y = max(np.ptp(list(all_focal.values())),
                   telescope.primary_diameter * 0.02)
    margin_y = 2.5
    center_y = g_focal_y
    ax.set_xlim(-telescope.primary_diameter * 0.08,
                telescope.primary_diameter * 0.08)
    ax.set_ylim(center_y - spread_y * margin_y,
                center_y + spread_y * margin_y)
    linewidths = {"B": 1.6, "G": 1.0, "R": 0.7}
    draw_order = sorted(wavelengths.items(), key=lambda kv: kv[1])
    for label, wl in draw_order:
        color = wavelength_to_color(wl)
        lw = linewidths.get(label, 1.0)
        rays = create_parallel_rays(
            num_rays=num_display_rays,
            aperture_diameter=telescope.primary_diameter,
            entry_height=telescope.tube_length * 1.15,
            wavelength_nm=wl,
        )
        telescope.trace_rays(rays)
        focal_y = all_focal.get(label, None)
        for ray in rays:
            if len(ray.history) < 2:
                continue
            path = np.array(ray.history)
            # Extend past focal point so the bundle's diverging fan is
            # clearly visible.
            if focal_y is not None and len(path) >= 2:
                p_last = path[-1]
                p_prev = path[-2]
                seg = p_last - p_prev
                norm = float(np.linalg.norm(seg))
                if norm > 0:
                    unit = seg / norm
                    dy = seg[1]
                    if dy != 0:
                        t_to_focal = (focal_y - p_last[1]) / dy
                        if 0 < t_to_focal < 5.0:
                            tip_f = p_last + t_to_focal * seg
                            path = np.vstack([path, tip_f])
                            p_last = tip_f
                    ext = 2.0 * spread_y * margin_y
                    tip_p = p_last + unit * ext
                    path = np.vstack([path, tip_p])
            ax.plot(path[:, 0], path[:, 1],
                    color=color, alpha=0.85, linewidth=lw)
        if focal_y is not None:
            ax.plot(0.0, focal_y, "*", color=color, markersize=10,
                    alpha=0.55, zorder=5,
                    label=f"{label} ({wl:.0f}nm)")

    # User's focal plane marker
    if focus_wavelength_nm is not None:
        fwl = focus_wavelength_nm
        focus_plane_y = g_focal_y - chromatic_defocus(telescope, fwl)
        focus_color = wavelength_to_color(fwl)
        ax.axhline(focus_plane_y, color=focus_color, linestyle="--",
                   linewidth=1.2, alpha=0.6, zorder=4)
        ax.text(0.02, focus_plane_y, f"  focal plane ({fwl:.0f} nm)",
                color=focus_color, fontsize=7, fontweight="bold",
                transform=ax.get_yaxis_transform(),
                verticalalignment="bottom", alpha=0.9, zorder=5)

    ax.set_xlabel("x (mm)", fontsize=8)
    ax.set_ylabel("y (mm)", fontsize=8)
    ax.tick_params(labelsize=7)
    # Make explicit that this is a magnified view of the focal region marked
    # by the dashed box on the ray-trace plot on the LEFT (R3.6c).
    ax.set_title("Zoomed view of the focal region from the ray trace (left)\n"
                 "— R/G/B bundles converge to their own focus, then diverge",
                 fontsize=8.5)
    ax.legend(fontsize=7, loc="upper right", framealpha=0.8)
    ax.grid(True, alpha=0.2)


def plot_polychromatic_ray_trace_comparison(
    telescopes: list[Telescope],
    labels: list[str],
    num_display_rays: int = 5,
    wavelengths: dict[str, float] | None = None,
    figsize_per_panel: tuple[float, float] = (7, 8),
    save_path: str | None = None,
) -> plt.Figure:
    """Plot polychromatic ray traces side by side for comparison.

    Useful for comparing singlet vs achromat chromatic aberration.

    Args:
        telescopes: List of telescope objects to compare.
        labels: Display label for each telescope.
        num_display_rays: Number of rays per wavelength per telescope.
        wavelengths: Dict mapping label to wavelength in nm.
        figsize_per_panel: (width, height) per subplot panel.
        save_path: If provided, save the figure to this path.

    Returns:
        The matplotlib Figure object.
    """
    from telescope_sim.source import create_parallel_rays
    from telescope_sim.physics.ray import (
        CHROMATIC_WAVELENGTHS, wavelength_to_color,
    )

    if wavelengths is None:
        wavelengths = CHROMATIC_WAVELENGTHS

    n = len(telescopes)
    fig, axes = plt.subplots(
        1, n,
        figsize=(figsize_per_panel[0] * n, figsize_per_panel[1]),
        squeeze=False,
    )

    for i, (telescope, label) in enumerate(zip(telescopes, labels)):
        ax = axes[0, i]
        components = telescope.get_components_for_plotting()

        # Draw optics without rays
        _draw_ray_trace(ax, [], components, title=label, show_tube=True)

        # Trace each wavelength
        for wl_label, wl in wavelengths.items():
            color = wavelength_to_color(wl)
            rays = create_parallel_rays(
                num_rays=num_display_rays,
                aperture_diameter=telescope.primary_diameter,
                entry_height=telescope.tube_length * 1.15,
                wavelength_nm=wl,
            )
            telescope.trace_rays(rays)

            for ray in rays:
                if len(ray.history) < 2:
                    continue
                path = np.array(ray.history)
                ax.plot(path[:, 0], path[:, 1],
                        color=color, alpha=0.7, linewidth=1.0)

            end_points = [r.history[-1] for r in rays
                          if len(r.history) >= 3]
            if end_points:
                focal = np.mean(end_points, axis=0)
                ax.plot(focal[0], focal[1], "*", color=color,
                        markersize=10,
                        label=f"{wl_label} ({wl:.0f}nm)",
                        zorder=5)

        ax.legend(loc="upper right", fontsize="small")

    # Shared axis limits
    all_xlims = [axes[0, i].get_xlim() for i in range(n)]
    all_ylims = [axes[0, i].get_ylim() for i in range(n)]
    shared_xlim = (min(lo for lo, _ in all_xlims),
                   max(hi for _, hi in all_xlims))
    shared_ylim = (min(lo for lo, _ in all_ylims),
                   max(hi for _, hi in all_ylims))
    for i in range(n):
        axes[0, i].set_xlim(shared_xlim)
        axes[0, i].set_ylim(shared_ylim)

    fig.suptitle("Polychromatic Ray Trace Comparison", fontsize=14)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


def plot_spot_diagram_comparison(
    telescopes: list[Telescope],
    labels: list[str],
    num_display_rays: int = 11,
    method: str = "analytical",
    include_obstruction: bool = True,
    physics_params: list[dict] | None = None,
    figsize_per_panel: tuple[float, float] = (7, 7),
    save_path: str | None = None,
) -> plt.Figure:
    """Plot spot diagrams side by side for multiple telescopes.

    Args:
        telescopes: List of telescope objects to compare.
        labels: Display label for each telescope.
        num_display_rays: Number of rays to trace per telescope.
        figsize_per_panel: (width, height) per subplot panel.
        save_path: If provided, save the figure to this path.

    Returns:
        The matplotlib Figure object.
    """
    from telescope_sim.source import create_parallel_rays

    n = len(telescopes)
    fig, axes = plt.subplots(
        1, n,
        figsize=(figsize_per_panel[0] * n, figsize_per_panel[1]),
        squeeze=False,
    )

    for i, (telescope, label) in enumerate(zip(telescopes, labels)):
        ax = axes[0, i]
        # Resolve per-panel physics params
        pp = physics_params[i] if physics_params else {}
        panel_method = pp.get("method", method)
        panel_obstruction = pp.get("include_obstruction", include_obstruction)

        # Always create rays for color-coding
        rays = create_parallel_rays(
            num_rays=num_display_rays,
            aperture_diameter=telescope.primary_diameter,
            entry_height=telescope.tube_length * 1.15,
        )
        telescope.trace_rays(rays)
        offsets = _find_focal_plane_positions(rays)

        # Extract focal plane y position
        focal_plane_y = None
        traced_rays = [r for r in rays if len(r.history) >= 2]
        if traced_rays:
            focal_plane_y = traced_rays[0].history[-1][1]

        _draw_spot_diagram(ax, offsets, title=label, rays=rays,
                          focal_plane_y=focal_plane_y)

    fig.suptitle("Spot Diagram Comparison", fontsize=14)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


def plot_focal_image_comparison(
    telescopes: list[Telescope],
    labels: list[str],
    wavelength_nm: float = 550.0,
    method: str = "analytical",
    seeing_arcsec: float | None = None,
    figsize_per_panel: tuple[float, float] = (7, 7),
    save_path: str | None = None,
    include_obstruction: bool = True,
    physics_params: list[dict] | None = None,
) -> plt.Figure:
    """Plot focal plane images side by side for multiple telescopes.

    Args:
        telescopes: List of telescope objects to compare.
        labels: Display label for each telescope.
        wavelength_nm: Wavelength of light in nanometers (default for all panels).
        method: "analytical" or "traced" (default for all panels).
        seeing_arcsec: Atmospheric seeing FWHM in arcseconds (default for all panels).
        figsize_per_panel: (width, height) per subplot panel.
        save_path: If provided, save the figure to this path.
        include_obstruction: If False, ignore secondary mirror
                             obstruction in the PSF and ray masking (default for all panels).
        physics_params: Optional list of per-panel physics overrides.
                        Each dict may contain any subset of: wavelength_nm,
                        method, seeing_arcsec, include_obstruction.
                        Unspecified keys fall back to the scalar defaults above.

    Returns:
        The matplotlib Figure object.
    """
    n = len(telescopes)
    pp_list = _resolve_physics_params(
        n, physics_params, wavelength_nm, method,
        seeing_arcsec, include_obstruction,
    )

    fig, axes = plt.subplots(
        1, n,
        figsize=(figsize_per_panel[0] * n, figsize_per_panel[1]),
        squeeze=False,
    )

    for i, (telescope, label) in enumerate(zip(telescopes, labels)):
        ax = axes[0, i]
        pp = pp_list[i]
        _draw_focal_image(
            ax, telescope, title=label,
            wavelength_nm=pp["wavelength_nm"],
            method=pp["method"],
            seeing_arcsec=pp["seeing_arcsec"],
            include_obstruction=pp["include_obstruction"],
        )

    fig.suptitle("Focal Image Comparison", fontsize=14)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


def plot_psf_comparison(
    telescopes: list[Telescope],
    labels: list[str],
    wavelength_nm: float = 550.0,
    method: str = "analytical",
    figsize: tuple[float, float] = (14, 7),
    save_path: str | None = None,
    include_obstruction: bool = True,
    physics_params: list[dict] | None = None,
) -> plt.Figure:
    """Overlay PSF profiles from multiple telescopes on shared axes.

    Creates a two-panel figure (linear + log scale). When all panels
    share the same physics parameters and telescope geometry, a single
    ideal Airy reference curve is drawn. When physics differ across
    panels (e.g. different wavelengths or obstruction settings), each
    curve is fully self-contained with richer labels.

    Args:
        telescopes: List of telescope objects to compare.
        labels: Display label for each telescope.
        wavelength_nm: Wavelength of light in nanometers (default for all panels).
        method: "analytical" or "traced" (default for all panels).
        figsize: Figure size in inches.
        save_path: If provided, save the figure to this path.
        include_obstruction: If False, ignore secondary mirror
                             obstruction (default for all panels).
        physics_params: Optional list of per-panel physics overrides.
                        Each dict may contain any subset of: wavelength_nm,
                        method, seeing_arcsec, include_obstruction.
                        Unspecified keys fall back to the scalar defaults above.

    Returns:
        The matplotlib Figure object.
    """
    from scipy.signal import fftconvolve

    n = len(telescopes)
    pp_list = _resolve_physics_params(
        n, physics_params, wavelength_nm, method,
        None, include_obstruction,
    )

    fig, (ax_lin, ax_log) = plt.subplots(1, 2, figsize=figsize)
    colors = plt.cm.tab10.colors  # up to 10 distinct colors

    # Decide whether all configs share the same physics+geometry,
    # which lets us draw a single shared Airy reference curve.
    def _physics_signature(tel, pp):
        obs = tel.obstruction_ratio if pp["include_obstruction"] else 0.0
        return (tel.primary_diameter, tel.focal_length, pp["wavelength_nm"],
                pp["method"], pp["include_obstruction"], obs)

    signatures = [_physics_signature(t, pp)
                  for t, pp in zip(telescopes, pp_list)]
    shared_physics = len(set(signatures)) == 1

    # Determine a common radial extent
    all_airy_radii = []
    all_max_spots = []
    for telescope, pp in zip(telescopes, pp_list):
        wl_mm = pp["wavelength_nm"] * 1e-6
        f_ratio = telescope.focal_length / telescope.primary_diameter
        all_airy_radii.append(1.22 * wl_mm * f_ratio)
        y_off = _get_focal_offsets(telescope, pp["method"],
                                   include_obstruction=pp["include_obstruction"])
        if y_off is not None:
            all_max_spots.append(np.max(np.abs(y_off)))

    max_airy = max(all_airy_radii)
    r_max = max(max_airy * 6,
                max(all_max_spots) * 4 if all_max_spots else 0,
                0.001)
    r = np.linspace(0, r_max, 1000)

    if shared_physics:
        # Draw a single shared Airy reference from the first telescope
        ref = telescopes[0]
        pp0 = pp_list[0]
        wl_mm = pp0["wavelength_nm"] * 1e-6
        airy_radius = all_airy_radii[0]
        ref_obs = ref.obstruction_ratio if pp0["include_obstruction"] else 0.0

        airy_profile = compute_psf(r, ref.primary_diameter, ref.focal_length,
                                   wl_mm, ref_obs)
        airy_label = "Ideal Airy (diffraction only)"
        if ref_obs > 1e-6:
            airy_label += f" [\u03b5={ref_obs:.2f}]"
        ax_lin.plot(r * 1000, airy_profile, "b-", linewidth=1.5, alpha=0.5,
                    label=airy_label)
        ax_log.semilogy(r * 1000, np.clip(airy_profile, 1e-6, None),
                        "b-", linewidth=1.5, alpha=0.5, label=airy_label)

        ax_lin.axvline(airy_radius * 1000, color="gray", linestyle=":",
                       alpha=0.4,
                       label=f"Airy radius: {airy_radius * 1000:.2f} \u00b5m")
        ax_log.axvline(airy_radius * 1000, color="gray", linestyle=":",
                       alpha=0.4)

    for idx, (telescope, label, pp) in enumerate(
            zip(telescopes, labels, pp_list)):
        color = colors[idx % len(colors)]
        wl_mm = pp["wavelength_nm"] * 1e-6
        airy_radius = all_airy_radii[idx]
        tel_obs = telescope.obstruction_ratio if pp["include_obstruction"] else 0.0

        y_offsets = _get_focal_offsets(telescope, pp["method"],
                                       include_obstruction=pp["include_obstruction"])
        if y_offsets is None:
            continue

        rms_spot = np.std(y_offsets)
        strehl = _estimate_strehl(rms_spot, airy_radius)
        is_perfect = rms_spot < 1e-10

        if is_perfect:
            combined_r = r
            combined_radial = compute_psf(r, telescope.primary_diameter,
                                          telescope.focal_length,
                                          wl_mm, tel_obs)
        else:
            n_px = 256
            half = r_max
            coords_1d = np.linspace(-half, half, n_px)
            cxx, cyy = np.meshgrid(coords_1d, coords_1d)
            crr = np.sqrt(cxx ** 2 + cyy ** 2)

            geo_2d = _build_geometric_spot_2d(y_offsets, half, n_px)
            airy_2d = compute_psf(crr, telescope.primary_diameter,
                                  telescope.focal_length, wl_mm,
                                  tel_obs)
            airy_2d = airy_2d / airy_2d.sum()
            combined_2d = fftconvolve(geo_2d, airy_2d, mode="same")

            center = n_px // 2
            pixel_size = (2 * half) / n_px
            combined_radial = combined_2d[center, center:]
            combined_r = np.arange(len(combined_radial)) * pixel_size
            if combined_radial.max() > 0:
                combined_radial = combined_radial / combined_radial.max()

        # Build label: richer when physics differ across panels
        if shared_physics:
            curve_label = f"{label} (Strehl={strehl:.3f})"
        else:
            extras = []
            extras.append(f"\u03bb={pp['wavelength_nm']:.0f}nm")
            if pp["include_obstruction"]:
                extras.append(f"\u03b5={tel_obs:.2f}")
            else:
                extras.append("no obs.")
            extras.append(f"Strehl={strehl:.3f}")
            curve_label = f"{label} ({', '.join(extras)})"

        ax_lin.plot(combined_r * 1000, combined_radial, color=color,
                    linewidth=2, label=curve_label)
        ax_log.semilogy(combined_r * 1000,
                        np.clip(combined_radial, 1e-6, None),
                        color=color, linewidth=2, label=curve_label)

    ax_lin.set_xlabel("Radial distance (\u00b5m)")
    ax_lin.set_ylabel("Normalized intensity")
    ax_lin.set_title("Linear scale")
    ax_lin.legend(fontsize=7)
    ax_lin.grid(True, alpha=0.3)
    ax_lin.set_ylim(-0.05, 1.05)

    ax_log.set_xlabel("Radial distance (\u00b5m)")
    ax_log.set_ylabel("Normalized intensity (log)")
    ax_log.set_title("Log scale")
    ax_log.legend(fontsize=7)
    ax_log.grid(True, alpha=0.3)
    ax_log.set_ylim(1e-4, 1.5)

    fig.suptitle("PSF Comparison", fontsize=14)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


def _draw_eyepiece_icon(ax: plt.Axes, rays: list[Ray],
                        focal_area: np.ndarray,
                        components: dict) -> None:
    """Draw a small eyepiece barrel icon at the focal point.

    Detects the dominant travel direction of the final ray segments
    to orient the barrel correctly:
      - Newtonian: rays exit horizontally (+x), eyepiece points right
      - Cassegrain / Refractor: rays converge downward (-y), eyepiece
        points down
    """
    import matplotlib.patches as mpatches

    # Determine eyepiece orientation from final ray segments
    traced = [r for r in rays if len(r.history) >= 3]
    if not traced:
        return

    dx_total = sum(r.history[-1][0] - r.history[-2][0] for r in traced)
    dy_total = sum(r.history[-1][1] - r.history[-2][1] for r in traced)

    # Scale barrel size to ~3% of primary diameter
    d = components["primary_diameter"]
    barrel_length = d * 0.12
    barrel_width = d * 0.06
    flare_width = d * 0.09

    fx, fy = focal_area

    if abs(dx_total) > abs(dy_total):
        # Horizontal exit — barrel extends in +x
        sign = 1.0 if dx_total > 0 else -1.0
        # Narrow barrel
        barrel = mpatches.FancyBboxPatch(
            (fx + sign * 2, fy - barrel_width / 2),
            sign * barrel_length, barrel_width,
            boxstyle="round,pad=1",
            facecolor="silver", edgecolor="dimgray",
            linewidth=1.2, alpha=0.8, zorder=4,
        )
        ax.add_patch(barrel)
        # Eye lens flare (wider end)
        flare_x = fx + sign * (2 + barrel_length)
        ax.plot([flare_x, flare_x],
                [fy - flare_width / 2, fy + flare_width / 2],
                color="dimgray", linewidth=2.0, solid_capstyle="round",
                alpha=0.8, zorder=4)
    else:
        # Vertical exit (Cassegrain / Refractor) — barrel extends in -y
        sign = -1.0 if dy_total < 0 else 1.0
        barrel = mpatches.FancyBboxPatch(
            (fx - barrel_width / 2, fy + sign * 2),
            barrel_width, sign * barrel_length,
            boxstyle="round,pad=1",
            facecolor="silver", edgecolor="dimgray",
            linewidth=1.2, alpha=0.8, zorder=4,
        )
        ax.add_patch(barrel)
        # Eye lens flare (wider end)
        flare_y = fy + sign * (2 + barrel_length)
        ax.plot([fx - flare_width / 2, fx + flare_width / 2],
                [flare_y, flare_y],
                color="dimgray", linewidth=2.0, solid_capstyle="round",
                alpha=0.8, zorder=4)

    # Add "Eyepiece" text label near the icon
    text_offset = barrel_length * 0.8
    if abs(dx_total) > abs(dy_total):
        ax.annotate("Eyepiece", (fx + sign * (2 + barrel_length / 2), fy),
                    textcoords="offset points",
                    xytext=(0, -barrel_width * 1.5),
                    fontsize=7, color="dimgray", ha="center", va="top",
                    zorder=4)
    else:
        ax.annotate("Eyepiece",
                    (fx, fy + sign * (2 + barrel_length / 2)),
                    textcoords="offset points",
                    xytext=(text_offset * 2.5, 0),
                    fontsize=7, color="dimgray", ha="left", va="center",
                    zorder=4)


def _draw_tube(ax: plt.Axes, components: dict):
    """Draw a simple rectangular tube outline."""
    half_d = components["primary_diameter"] / 2.0
    tube_len = components["tube_length"]

    # Left wall
    ax.plot([-half_d, -half_d], [0, tube_len * 1.1],
            color="gray", linewidth=1.5, linestyle="--", alpha=0.5)
    # Right wall
    ax.plot([half_d, half_d], [0, tube_len * 1.1],
            color="gray", linewidth=1.5, linestyle="--", alpha=0.5)


# ── Coma spot helper ─────────────────────────────────────────────────


def _build_coma_spot_2d(x_offsets: np.ndarray, y_offsets: np.ndarray,
                        half_size: float,
                        num_pixels: int) -> np.ndarray:
    """Build a 2D coma spot image by direct binning with Gaussian splat.

    Unlike ``_build_geometric_spot_2d`` which assumes rotational symmetry,
    this creates the full 2D asymmetric coma pattern from explicit (x, y)
    ray positions.

    Args:
        x_offsets: 1D array of ray x-positions in mm.
        y_offsets: 1D array of ray y-positions in mm.
        half_size: Half-width of the image in mm.
        num_pixels: Image resolution.

    Returns:
        2D numpy array with the coma spot pattern.
    """
    image = np.zeros((num_pixels, num_pixels))
    pixel_size = (2.0 * half_size) / num_pixels
    splat_sigma = max(pixel_size * 1.0, 1e-7)

    coords = np.linspace(-half_size, half_size, num_pixels)
    xx, yy = np.meshgrid(coords, coords)

    for x_off, y_off in zip(x_offsets, y_offsets):
        dist_sq = (xx - x_off) ** 2 + (yy - y_off) ** 2
        image += np.exp(-dist_sq / (2.0 * splat_sigma ** 2))

    return image


# ── Vignetting plots ─────────────────────────────────────────────────


def plot_vignetting_curve(
    telescope: Telescope,
    max_field_arcsec: float | None = None,
    num_points: int = 200,
    figsize: tuple[float, float] = (9, 6),
    save_path: str | None = None,
) -> plt.Figure:
    """Plot illumination fraction vs off-axis field angle.

    Shows where the fully-illuminated field ends and how quickly
    light is lost with increasing field angle.

    NOTE: Tube wall vignetting is not modeled.

    Args:
        telescope: The telescope to analyze.
        max_field_arcsec: Maximum field angle to plot (arcseconds).
            If None, auto-scales to show the full vignetting curve.
        num_points: Number of sample points.
        figsize: Figure size in inches.
        save_path: If provided, save the figure to this path.

    Returns:
        The matplotlib Figure object.
    """
    fif = telescope.fully_illuminated_field()

    if max_field_arcsec is None:
        # Auto-scale: go far enough to see significant vignetting
        max_field_arcsec = max(fif * 5, 300.0)

    angles = np.linspace(0, max_field_arcsec, num_points)
    illumination = telescope.compute_vignetting(angles)

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(angles, illumination, "b-", linewidth=2, label="Illumination")
    ax.axhline(1.0, color="gray", linestyle=":", alpha=0.4)
    if fif > 0:
        ax.axvline(fif, color="green", linestyle="--", alpha=0.7,
                    label=f"Fully illuminated: {fif:.1f}\"")

    # Obstruction ratio drives vignetting (a larger secondary catches more of
    # the off-axis cone → larger fully-illuminated field). Label it on BOTH
    # the title and an info box so the baseline's ε is explicit (R3.7c).
    obs_ratio = telescope.obstruction_ratio
    ax.set_xlabel("Off-axis angle (arcsec)")
    ax.set_ylabel("Illumination fraction")
    ax.set_title(f"Vignetting — {telescope.primary_diameter:.0f}mm "
                 f"f/{telescope.focal_ratio:.1f}, "
                 f"obstruction ε = {obs_ratio:.2f} ({obs_ratio:.0%})")
    ax.set_ylim(-0.05, 1.1)
    ax.legend(loc="lower left")
    ax.grid(True, alpha=0.3)

    ax.text(0.98, 0.20,
            f"Obstruction ratio ε = {obs_ratio:.2f}\n"
            f"(secondary Ø / primary Ø)\n"
            f"Larger ε → less vignetting,\n"
            f"but more central obstruction.",
            transform=ax.transAxes, fontsize=8, ha="right", va="bottom",
            bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.9))
    ax.text(0.98, 0.02,
            "Approx: tube wall vignetting not modeled",
            transform=ax.transAxes, fontsize=7, ha="right",
            color="orange", alpha=0.8)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_vignetting_comparison(
    telescopes: list[Telescope],
    labels: list[str],
    max_field_arcsec: float | None = None,
    num_points: int = 200,
    figsize: tuple[float, float] = (9, 6),
    save_path: str | None = None,
) -> plt.Figure:
    """Overlay vignetting curves for multiple telescopes.

    Args:
        telescopes: List of telescope objects to compare.
        labels: Display label for each telescope.
        max_field_arcsec: Maximum field angle to plot (arcseconds).
        num_points: Number of sample points.
        figsize: Figure size in inches.
        save_path: If provided, save the figure to this path.

    Returns:
        The matplotlib Figure object.
    """
    colors = plt.cm.tab10.colors

    if max_field_arcsec is None:
        max_fif = max(t.fully_illuminated_field() for t in telescopes)
        max_field_arcsec = max(max_fif * 5, 300.0)

    angles = np.linspace(0, max_field_arcsec, num_points)

    fig, ax = plt.subplots(figsize=figsize)
    for idx, (telescope, label) in enumerate(zip(telescopes, labels)):
        color = colors[idx % len(colors)]
        illumination = telescope.compute_vignetting(angles)
        fif = telescope.fully_illuminated_field()
        suffix = f" (FIF={fif:.0f}\")" if fif > 0 else ""
        ax.plot(angles, illumination, color=color, linewidth=2,
                label=f"{label}{suffix}")

    ax.axhline(1.0, color="gray", linestyle=":", alpha=0.4)
    ax.set_xlabel("Off-axis angle (arcsec)")
    ax.set_ylabel("Illumination fraction")
    ax.set_title("Vignetting Comparison")
    ax.set_ylim(-0.05, 1.1)
    ax.legend()
    ax.grid(True, alpha=0.3)

    ax.text(0.98, 0.02,
            "Approx: tube wall vignetting not modeled",
            transform=ax.transAxes, fontsize=7, ha="right",
            color="orange", alpha=0.8)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


# ── 2D PSF plot ──────────────────────────────────────────────────────


def plot_psf_2d(
    telescope: Telescope,
    wavelength_nm: float = 550.0,
    grid_size: int = 512,
    image_scale: float | None = None,
    figsize: tuple[float, float] = (7, 7),
    colormap: str = "inferno",
    include_obstruction: bool = True,
    autoscale: bool = False,
    log_scale: bool = True,
    save_path: str | None = None,
    peak_reference: float | None = None,
) -> plt.Figure:
    """Show the 2D PSF image on a log scale, revealing diffraction spikes.

    When spider vanes are present, the PSF shows characteristic
    diffraction spikes perpendicular to each vane.

    Args:
        telescope: The telescope to analyze.
        wavelength_nm: Wavelength of light in nanometers.
        grid_size: FFT grid size.
        image_scale: Half-width of displayed region in mm.
            If None, auto-scales to ~10 Airy radii.
        figsize: Figure size in inches.
        colormap: Matplotlib colormap.
        include_obstruction: Include central obstruction.
        autoscale: If True, auto-scale the color range to show full dynamic range.
                  If False, use fixed vmin=-4, vmax=0 for consistency.
        save_path: If provided, save the figure to this path.
        peak_reference: If provided, display the PSF *relative* to this raw
            on-axis peak (from a paired compute_fft_psf call with identical
            sampling) instead of independently peak-normalising to 1.0. This
            preserves the cross-frame peak-intensity ratio — e.g. an
            obstructed PSF then peaks at its Strehl ratio (1−ε²)² rather than
            at 1.0, making the central-obstruction peak loss visible against
            an unobstructed reference. The computed raw peak is attached to
            the returned figure as ``fig._psf_raw_peak`` so the caller can
            use this frame as the reference for a paired frame.

    Returns:
        The matplotlib Figure object. The figure carries two extra
        attributes for paired/shared-normalisation rendering:
        ``_psf_raw_peak`` (this frame's pre-normalisation peak) and
        ``_psf_relative_peak`` (displayed peak relative to peak_reference;
        1.0 when peak_reference is None).
    """
    wavelength_mm = wavelength_nm * 1e-6
    obs_ratio = telescope.obstruction_ratio if include_obstruction else 0.0
    f_ratio = telescope.focal_ratio
    airy_radius = 1.22 * wavelength_mm * f_ratio

    if image_scale is None:
        image_scale = airy_radius * 10

    # Oversample for ~8 pixels per Airy radius
    base_pitch = wavelength_mm * f_ratio
    pixels_per_airy = airy_radius / base_pitch
    oversample = max(1, int(np.ceil(8.0 / pixels_per_airy)))
    oversample = min(oversample, 16)

    psf_2d, half_size, raw_peak = compute_fft_psf(
        telescope.primary_diameter, telescope.focal_length,
        wavelength_mm, obs_ratio,
        telescope.spider_vanes, telescope.spider_vane_width,
        grid_size=grid_size,
        oversample=oversample,
        return_raw_peak=True,
    )

    # Shared normalisation: rescale this (peak=1.0) PSF so its on-axis peak
    # is expressed relative to a reference raw peak from a paired frame. The
    # obstructed PSF then peaks at raw_peak/peak_reference = (1−ε²)² instead
    # of 1.0, so the Strehl peak loss is visible (and the rings, carrying the
    # redistributed energy, read correctly against the unobstructed core).
    relative_peak = 1.0
    if peak_reference is not None and peak_reference > 0:
        relative_peak = raw_peak / peak_reference
        psf_2d = psf_2d * relative_peak

    fig, ax = plt.subplots(figsize=figsize)

    # Display on log (default) or linear scale. Log reveals the full ring
    # system; linear shows the bright core only with rings nearly black.
    if log_scale:
        psf_display = np.clip(psf_2d, 1e-6, None)
        psf_img = np.log10(psf_display)
        if autoscale:
            vmin, vmax = float(psf_img.min()), float(psf_img.max())
        else:
            vmin, vmax = -4, 0
        scale_label = "log scale"
    else:
        psf_img = psf_2d
        if autoscale:
            vmin, vmax = float(psf_img.min()), float(psf_img.max())
        else:
            vmin, vmax = 0.0, 1.0
        scale_label = "linear scale"

    # Shift the extent by half a pixel so the FFT peak (which lands at
    # pixel [N/2, N/2] for an even-sized grid) maps exactly to (0, 0)
    # in data coordinates. Without this, overlays anchored at (0, 0)
    # appear ~half a pixel off the bright PSF peak.
    n_px = psf_img.shape[0]
    dp = (2.0 * half_size) / n_px
    ext_lo = -half_size - 0.5 * dp
    ext_hi = half_size - 0.5 * dp
    # Bilinear interpolation smooths the display. At small apertures the axis
    # (locked to a small image_scale) zooms into a coarsely-sampled corner of
    # the FFT PSF, so nearest-neighbour rendering shows blocky pixels — worst
    # exactly where the user reported it (R3.1). Bilinear removes the blocks.
    ax.imshow(psf_img,
              extent=[ext_lo, ext_hi, ext_lo, ext_hi],
              origin="lower", cmap=colormap,
              vmin=vmin, vmax=vmax, interpolation="bilinear")
    ax.set_xlim(-image_scale, image_scale)
    ax.set_ylim(-image_scale, image_scale)

    # Draw Airy radius circle
    airy_circle = plt.Circle((0, 0), airy_radius, fill=False,
                              color="white", linestyle="--",
                              linewidth=1.0, alpha=0.6)
    ax.add_patch(airy_circle)

    ax.set_xlabel("Position (mm)")
    ax.set_ylabel("Position (mm)")
    vane_info = (f", {telescope.spider_vanes} spider vanes"
                 if telescope.spider_vanes > 0 else "")
    ax.set_title(f"2D PSF ({scale_label}) — \u03bb={wavelength_nm:.0f}nm, "
                 f"f/{f_ratio:.1f}{vane_info}")

    info_text = (
        f"Airy radius: {airy_radius * 1000:.2f} \u00b5m\n"
        f"\u03bb = {wavelength_nm:.0f} nm\n"
        f"Spider vanes: {telescope.spider_vanes}\n"
        f"Vane width: {telescope.spider_vane_width:.1f} mm"
    )
    if peak_reference is not None and relative_peak < 0.999:
        # Shared-normalisation view: surface the peak loss explicitly so the
        # Strehl drop is a number, not just a subtle colour shift.
        info_text += (
            f"\nPeak vs unobstructed: {relative_peak:.3f}\n"
            f"  (Strehl-type peak loss)"
        )
    ax.text(0.02, 0.02, info_text,
            transform=ax.transAxes, fontsize=8,
            verticalalignment="bottom", color="white",
            bbox=dict(boxstyle="round", facecolor="black", alpha=0.6))

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    # Expose peaks for shared-normalisation pairing (see peak_reference).
    fig._psf_raw_peak = raw_peak
    fig._psf_relative_peak = relative_peak
    return fig


def plot_psf_2d_comparison(
    telescopes: list[Telescope],
    labels: list[str],
    wavelength_nm: float = 550.0,
    grid_size: int = 512,
    image_scale: float | None = None,
    figsize_per_panel: tuple[float, float] = (7, 7),
    colormap: str = "inferno",
    include_obstruction: bool = True,
    save_path: str | None = None,
) -> plt.Figure:
    """Side-by-side 2D PSF images on log scale.

    Best for comparing spider vane configurations — diffraction spikes
    are only visible in 2D and on log scale.

    Args:
        telescopes: List of telescope objects to compare.
        labels: Display label for each telescope.
        wavelength_nm: Wavelength of light in nanometers.
        grid_size: FFT grid size per panel.
        image_scale: Half-width of displayed region in mm.
        figsize_per_panel: (width, height) per subplot panel.
        colormap: Matplotlib colormap.
        include_obstruction: Include central obstruction.
        save_path: If provided, save the figure to this path.

    Returns:
        The matplotlib Figure object.
    """
    wavelength_mm = wavelength_nm * 1e-6
    n = len(telescopes)
    fig, axes = plt.subplots(
        1, n,
        figsize=(figsize_per_panel[0] * n, figsize_per_panel[1]),
        squeeze=False,
    )

    for i, (telescope, label) in enumerate(zip(telescopes, labels)):
        ax = axes[0, i]
        obs_ratio = telescope.obstruction_ratio if include_obstruction else 0.0
        f_ratio = telescope.focal_ratio
        airy_radius = 1.22 * wavelength_mm * f_ratio

        scale = image_scale if image_scale is not None else airy_radius * 10
        base_pitch = wavelength_mm * f_ratio
        pixels_per_airy = airy_radius / base_pitch
        oversample = max(1, int(np.ceil(8.0 / pixels_per_airy)))
        oversample = min(oversample, 16)

        psf_2d, half_size = compute_fft_psf(
            telescope.primary_diameter, telescope.focal_length,
            wavelength_mm, obs_ratio,
            telescope.spider_vanes, telescope.spider_vane_width,
            grid_size=grid_size, oversample=oversample,
        )

        psf_display = np.clip(psf_2d, 1e-6, None)
        ax.imshow(np.log10(psf_display),
                  extent=[-half_size, half_size, -half_size, half_size],
                  origin="lower", cmap=colormap,
                  vmin=-4, vmax=0)
        ax.set_xlim(-scale, scale)
        ax.set_ylim(-scale, scale)

        airy_circle = plt.Circle((0, 0), airy_radius, fill=False,
                                  color="white", linestyle="--",
                                  linewidth=1.0, alpha=0.6)
        ax.add_patch(airy_circle)
        ax.set_xlabel("Position (mm)")
        ax.set_ylabel("Position (mm)")

        vane_info = (f", {telescope.spider_vanes} vanes"
                     if telescope.spider_vanes > 0 else ", no vanes")
        ax.set_title(f"{label}{vane_info}")

    fig.suptitle(f"2D PSF Comparison (log scale) — "
                 f"\u03bb={wavelength_nm:.0f}nm", fontsize=14)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


# ── Coma plots ───────────────────────────────────────────────────────


def plot_coma_spot(
    telescope: Telescope,
    field_angle_arcsec: float,
    wavelength_nm: float = 550.0,
    num_pixels: int = 256,
    figsize: tuple[float, float] = (7, 7),
    colormap: str = "hot",
    include_obstruction: bool = True,
    save_path: str | None = None,
) -> plt.Figure:
    """Plot a 2D coma spot diagram convolved with the diffraction PSF.

    Shows the asymmetric comet-shaped aberration pattern with an
    Airy circle reference.

    NOTE: Seidel 3rd-order approximation — valid for small field angles.

    Args:
        telescope: The telescope to analyze.
        field_angle_arcsec: Off-axis angle in arcseconds.
        wavelength_nm: Wavelength of light in nanometers.
        num_pixels: Image resolution.
        figsize: Figure size in inches.
        colormap: Matplotlib colormap.
        include_obstruction: Include central obstruction.
        save_path: If provided, save the figure to this path.

    Returns:
        The matplotlib Figure object.
    """
    from scipy.signal import fftconvolve

    wavelength_mm = wavelength_nm * 1e-6
    obs_ratio = telescope.obstruction_ratio if include_obstruction else 0.0
    f_ratio = telescope.focal_ratio
    airy_radius = 1.22 * wavelength_mm * f_ratio

    x_off, y_off = compute_coma_spot(
        field_angle_arcsec, telescope.focal_length,
        telescope.primary_diameter, obs_ratio,
    )
    rms_coma = compute_coma_rms(
        field_angle_arcsec, telescope.focal_length,
        telescope.primary_diameter, obs_ratio,
    )

    # Auto-scale image
    max_extent = max(np.max(np.abs(x_off)), np.max(np.abs(y_off)),
                     airy_radius * 3)
    half_size = max_extent * 1.5

    # Build geometric coma spot
    coma_image = _build_coma_spot_2d(x_off, y_off, half_size, num_pixels)

    # Convolve with diffraction PSF
    kernel_n = min(num_pixels, 128)
    kernel_half = max(airy_radius * 5, half_size * 0.3)
    kernel_coords = np.linspace(-kernel_half, kernel_half, kernel_n)
    kxx, kyy = np.meshgrid(kernel_coords, kernel_coords)
    kr = np.sqrt(kxx ** 2 + kyy ** 2)
    airy_kernel = compute_psf(kr, telescope.primary_diameter,
                              telescope.focal_length, wavelength_mm,
                              obs_ratio)
    airy_kernel = airy_kernel / airy_kernel.sum()
    image = fftconvolve(coma_image, airy_kernel, mode="same")
    if image.max() > 0:
        image = image / image.max()

    fig, ax = plt.subplots(figsize=figsize)
    ax.imshow(image, extent=[-half_size, half_size, -half_size, half_size],
              origin="lower", cmap=colormap, vmin=0, vmax=1)

    # Airy radius reference circle
    airy_circle = plt.Circle((0, 0), airy_radius, fill=False,
                              color="cyan", linestyle="--",
                              linewidth=1.0, alpha=0.8,
                              label=f"Airy radius: "
                                    f"{airy_radius * 1000:.2f} \u00b5m")
    ax.add_patch(airy_circle)

    ax.set_xlabel("Position (mm)")
    ax.set_ylabel("Position (mm)")
    ax.set_title(f"Coma Spot — {field_angle_arcsec:.1f}\" off-axis, "
                 f"f/{f_ratio:.1f}")
    ax.legend(loc="upper right", fontsize=8)

    info_text = (
        f"RMS coma: {rms_coma * 1000:.2f} \u00b5m\n"
        f"Airy radius: {airy_radius * 1000:.2f} \u00b5m\n"
        f"\u03bb = {wavelength_nm:.0f} nm"
    )
    ax.text(0.02, 0.02, info_text,
            transform=ax.transAxes, fontsize=9,
            verticalalignment="bottom", color="white",
            bbox=dict(boxstyle="round", facecolor="black", alpha=0.6))

    ax.text(0.02, 0.98,
            "Approx: Seidel 3rd-order coma",
            transform=ax.transAxes, fontsize=7,
            verticalalignment="top", color="yellow", alpha=0.8)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def _draw_coma_rms_panel(ax, angles, rms_values, airy_radius_mm, cff,
                         max_field_arcsec):
    """Context panel: RMS coma vs field angle with Airy + coma-free refs.

    Shared by both coma views (ray-fan and spot-grid) so the f-ratio story
    — coma grows linearly with field angle and the coma-free field shrinks
    as f² — is always on screen.
    """
    ax.plot(angles, rms_values * 1000, "b-", linewidth=2, label="RMS coma")
    ax.axhline(airy_radius_mm * 1000, color="red", linestyle="--", alpha=0.7,
               label=f"Airy radius: {airy_radius_mm * 1000:.2f} µm")
    if cff > 0 and cff <= max_field_arcsec:
        ax.axvline(cff, color="green", linestyle="--", alpha=0.7,
                   label=f"Coma-free field: {cff:.1f}\"")
    ax.set_xlabel("Off-axis angle (arcsec)")
    ax.set_ylabel("RMS coma (µm)")
    ax.set_title("RMS Coma vs Field Angle")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    # Fixed range so changing f-ratio rescales the curve, not the axes.
    ax.set_xlim(0, max_field_arcsec)
    ax.set_ylim(0, 20)


def _draw_coma_ray_fan_panel(ax, telescope, field_angle_arcsec, obs_ratio,
                             airy_radius_mm):
    """Meridional coma ray fan (Seidel model): transverse focal-plane error
    Δx vs signed pupil entry height h.

    Coma's optical-design signature is a PARABOLA (Δx ∝ h²): BOTH edges of
    the pupil bend the same way, unlike spherical aberration's odd cubic
    (S-shape) or defocus's straight line.  This panel uses the SAME Seidel
    coma coefficient C_s = θ·h²/(4f) as the spot grid, so the two views tell
    one consistent story, and the SAME viridis-on-|h| pupil colours as the
    companion ray-fan / ray-trace plots.

    NOTE: Seidel 3rd-order approximation, tangential section — valid for
    small field angles.
    """
    r_max = telescope.primary_diameter / 2.0
    r_min = r_max * obs_ratio
    f = telescope.focal_length
    theta = field_angle_arcsec / 206265.0

    # Signed pupil height across one meridian, skipping the obstructed core.
    n = 21
    h_pos = np.linspace(r_min, r_max, n)
    h_signed = np.concatenate([-h_pos[::-1], h_pos])
    # Tangential coma transverse aberration Δx = 3·C_s = 3·θ·h²/(4f).
    # Even in h → a one-sided parabola (the coma signature).
    dx_um = (3.0 * theta * h_signed ** 2 / (4.0 * f)) * 1000.0

    colors, sm = _pupil_colormap_colors(h_signed)
    ax.plot(h_signed, dx_um, color="gray", alpha=0.4, linewidth=1.0, zorder=1)
    ax.scatter(h_signed, dx_um, c=colors, s=55, edgecolors="black",
               linewidths=0.4, zorder=3)
    ax.axhline(0.0, color="black", linestyle=":", alpha=0.4, zorder=0)
    ax.axvline(0.0, color="black", linestyle=":", alpha=0.4, zorder=0)

    # Airy-radius band: coma that stays inside it is diffraction-limited.
    airy_um = airy_radius_mm * 1000.0
    ax.axhspan(-airy_um, airy_um, color="red", alpha=0.10, zorder=0,
               label=f"± Airy radius ({airy_um:.1f} µm)")

    # Floor the y-axis to a physical scale so a slow (corrected) scope reads
    # as a nearly flat parabola rather than a magnified numerical-noise blob.
    dx_max = float(np.max(np.abs(dx_um)))
    y_top = max(dx_max * 1.25, airy_um * 2.5)
    ax.set_ylim(-y_top * 0.18, y_top)

    ax.set_xlabel("Pupil entry height h (mm)")
    ax.set_ylabel("Transverse ray error at focal plane, Δx (µm)")
    ax.set_title(f"Coma ray fan @ {field_angle_arcsec:.0f}″ off-axis")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7, loc="upper center")
    # One-line reading guide anchored in the panel.
    inside = dx_max <= airy_um
    verdict = ("coma ≤ Airy radius → diffraction-limited here"
               if inside else "parabola = coma; both pupil edges bend the "
               "same way")
    ax.text(0.5, -0.22, verdict, transform=ax.transAxes, fontsize=7,
            ha="center", va="top", style="italic", color="gray")
    return sm


def _draw_coma_spot_grid(fig, subspec, spot_data, airy_radius_mm,
                         shared_lim_um, pupil_cmap, pupil_norm, pupil_sm):
    """Spot-diagram grid: one small 2D spot per sampled field angle, dots
    coloured by pupil zone (dark = central, bright = marginal rays).  The
    comet tail is visibly built from the bright marginal rays.
    """
    n_spots = len(spot_data)
    cols = 2 if n_spots <= 4 else min(n_spots, 3)
    rows = (n_spots + cols - 1) // cols
    gs_right = subspec.subgridspec(rows, cols, wspace=0.3, hspace=0.4)

    spot_axes = []
    for idx, (angle, x_off, y_off, pupil_r) in enumerate(spot_data):
        r = idx // cols
        c = idx % cols
        ax_spot = fig.add_subplot(gs_right[r, c])
        spot_axes.append(ax_spot)

        if not (np.max(np.abs(x_off)) < 1e-10
                and np.max(np.abs(y_off)) < 1e-10):
            ax_spot.scatter(x_off * 1000, y_off * 1000, s=2,
                            c=pupil_r, cmap=pupil_cmap, norm=pupil_norm,
                            alpha=0.6, linewidths=0)

        ax_spot.set_xlim(-shared_lim_um, shared_lim_um)
        ax_spot.set_ylim(-shared_lim_um, shared_lim_um)
        airy_c = plt.Circle((0, 0), airy_radius_mm * 1000, fill=False,
                            color="white", linestyle="--",
                            linewidth=0.9, alpha=0.9)
        ax_spot.add_patch(airy_c)
        ax_spot.set_facecolor("#101010")
        ax_spot.set_aspect("equal")
        ax_spot.set_title(f"{angle:.0f}\"", fontsize=9)
        ax_spot.tick_params(labelsize=6)
        if r == rows - 1:
            ax_spot.set_xlabel("µm", fontsize=7)
        if c == 0:
            ax_spot.set_ylabel("µm", fontsize=7)

    if spot_axes:
        cbar = fig.colorbar(pupil_sm, ax=spot_axes, fraction=0.046,
                            pad=0.04, shrink=0.85)
        cbar.set_label("Pupil zone  (0 = centre, 1 = mirror edge)",
                       fontsize=7)
        cbar.ax.tick_params(labelsize=6)


def plot_coma_field_analysis(
    telescope: Telescope,
    wavelength_nm: float = 550.0,
    max_field_arcsec: float | None = None,
    num_field_points: int = 100,
    spot_angles: list[float] | None = None,
    figsize: tuple[float, float] = (14, 7),
    include_obstruction: bool = True,
    view_mode: str = "ray_fan",
    ray_fan_field_arcsec: float = 120.0,
    save_path: str | None = None,
) -> plt.Figure:
    """Two-panel coma field analysis, switchable between two left views.

    ``view_mode="ray_fan"`` (default):
        Left  — coma RAY FAN at ``ray_fan_field_arcsec`` off-axis: the
                optical-design signature curve (a parabola Δx ∝ h²).
        Right — RMS coma vs field angle (f-ratio context).
    ``view_mode="spot_grid"``:
        Left  — RMS coma vs field angle.
        Right — grid of 2D spot diagrams at several field angles.

    Both views share the Seidel coma model and the same viridis-on-|h|
    pupil-zone colour scale as the companion ray-fan / ray-trace plots.

    NOTE: Seidel 3rd-order approximation — valid for small field angles.

    Args:
        telescope: The telescope to analyze.
        wavelength_nm: Wavelength of light in nanometers.
        max_field_arcsec: Maximum field angle for the RMS plot.
        num_field_points: Number of sample points for RMS curve.
        spot_angles: List of field angles for the spot grid.
            If None, auto-selects representative angles.
        figsize: Figure size in inches.
        include_obstruction: Include central obstruction.
        view_mode: "ray_fan" (default) or "spot_grid" — selects the left
            panel's presentation (the right panel follows).
        ray_fan_field_arcsec: Off-axis field angle for the ray-fan view.
        save_path: If provided, save the figure to this path.

    Returns:
        The matplotlib Figure object.
    """
    wavelength_mm = wavelength_nm * 1e-6
    obs_ratio = telescope.obstruction_ratio if include_obstruction else 0.0
    f_ratio = telescope.focal_ratio
    airy_radius = 1.22 * wavelength_mm * f_ratio

    cff = coma_free_field(telescope.focal_length,
                          telescope.primary_diameter,
                          wavelength_mm)

    # Fixed default range (independent of f-ratio) so panels are visually
    # comparable across f-ratios. Previously max_field_arcsec = cff*5
    # scaled with f² and produced wildly different x-axes (e.g. ~900″ at
    # f/4, ~3700″ at f/8), making side-by-side comparison meaningless.
    if max_field_arcsec is None:
        max_field_arcsec = 300.0

    angles = np.linspace(0, max_field_arcsec, num_field_points)
    rms_values = np.array([
        compute_coma_rms(a, telescope.focal_length,
                         telescope.primary_diameter, obs_ratio)
        for a in angles
    ])

    if spot_angles is None:
        # Fixed sample angles across all f-ratios so the user can see
        # exactly how the same physical field angle's coma grows as
        # f-ratio shrinks. (Previously the angles scaled with CFF, which
        # changes ∝ f² — meaning each f-ratio sampled different angles
        # and visual comparison was meaningless.)
        # Angles chosen to fit the tightened 300″ (after-side) FOV.
        spot_angles = [0.0, 30.0, 60.0, 120.0]

    fig = plt.figure(figsize=figsize)
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.2], wspace=0.3)

    if view_mode == "ray_fan":
        # LEFT: the ray fan (aberration signature) at a representative angle.
        ax_fan = fig.add_subplot(gs[0])
        _draw_coma_ray_fan_panel(ax_fan, telescope, ray_fan_field_arcsec,
                                 obs_ratio, airy_radius)
        # RIGHT: the RMS-vs-field context curve.
        ax_rms = fig.add_subplot(gs[1])
        _draw_coma_rms_panel(ax_rms, angles, rms_values, airy_radius, cff,
                             max_field_arcsec)
        fig.text(
            0.5, 0.015,
            "Left: coma's optical-design signature — a PARABOLA "
            "(Δx ∝ h²), both pupil edges bending the same way "
            "(vs spherical aberration's S-cubic). Dots coloured by pupil zone "
            "(dark = centre, bright = marginal). Right: how RMS coma grows with "
            "field angle for this f-ratio. Slow the scope (raise focal length) "
            "and the parabola flattens into the Airy band.",
            fontsize=7, ha="center", va="bottom", style="italic",
            color="gray", wrap=True)
    else:
        # LEFT: RMS-vs-field context curve.
        ax_rms = fig.add_subplot(gs[0])
        _draw_coma_rms_panel(ax_rms, angles, rms_values, airy_radius, cff,
                             max_field_arcsec)

        # RIGHT: spot-diagram grid.  Pre-compute every spot pattern, colouring
        # each ray by its pupil zone on the shared viridis-on-|h| scale so the
        # comet tail visibly grows out of the marginal rays.
        spot_data = []
        for angle in spot_angles:
            x_off, y_off, pupil_r = compute_coma_spot(
                angle, telescope.focal_length,
                telescope.primary_diameter, obs_ratio,
                num_pupil_zones=30, num_azimuthal=36,
                return_pupil_radius=True,
            )
            spot_data.append((angle, x_off, y_off, pupil_r))
        # Fixed 0..1 normalized pupil-radius scale so 1.0 always maps to the
        # mirror edge regardless of aperture (colours mean the same zone in
        # every panel and match the ray-fan colorbar).
        pupil_norm = plt.Normalize(vmin=0.0, vmax=1.0)
        pupil_cmap = plt.get_cmap("viridis")
        pupil_sm = plt.cm.ScalarMappable(cmap=pupil_cmap, norm=pupil_norm)
        pupil_sm.set_array([])
        # Fixed spot window (independent of f-ratio) so the SAME field angle's
        # coma visibly shrinks as f-ratio grows.  Sized to the worst sampled
        # angle (120″): at f/4 the comet fills ~45% of the panel; at f/8 the
        # comet (2.7 µm) fits *inside* the Airy disk (5.4 µm radius) —
        # it's diffraction-limited and coma is invisible, the key lesson.  A
        # very fast scope (< f/3) may overrun the panel, the intended "coma
        # blew past the budget" cue.
        shared_lim_um = 12.0
        _draw_coma_spot_grid(fig, gs[1], spot_data, airy_radius,
                             shared_lim_um, pupil_cmap, pupil_norm, pupil_sm)
        fig.text(
            0.72, 0.015,
            "Dots: ray intersections over a grid of pupil zones and azimuths, "
            "coloured by pupil zone\n"
            "(dark = central rays, bright = marginal/edge rays — same scale "
            "as the ray fan).\n"
            "The comet tail is built almost entirely from the bright marginal "
            "rays. White circle = Airy disk.",
            fontsize=7, ha="center", va="bottom", style="italic", color="gray")

    fig.suptitle(f"Coma Field Analysis — {telescope.primary_diameter:.0f}mm "
                 f"f/{f_ratio:.1f}", fontsize=13)

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_coma_field_analysis_comparison(
    telescopes: list[Telescope],
    labels: list[str],
    wavelength_nm: float = 550.0,
    max_field_arcsec: float | None = None,
    num_field_points: int = 100,
    include_obstruction: bool = True,
    figsize: tuple[float, float] = (10, 7),
    save_path: str | None = None,
) -> plt.Figure:
    """Overlay RMS coma curves for multiple telescopes."""
    wavelength_mm = wavelength_nm * 1e-6
    fig, ax = plt.subplots(figsize=figsize)

    colors = plt.cm.tab10.colors

    # Determine shared max field angle
    if max_field_arcsec is None:
        max_field_arcsec = max(
            max(coma_free_field(t.focal_length, t.primary_diameter,
                                wavelength_mm) * 5, 120.0)
            for t in telescopes
        )

    angles = np.linspace(0, max_field_arcsec, num_field_points)

    for i, (telescope, label) in enumerate(zip(telescopes, labels)):
        obs_ratio = telescope.obstruction_ratio if include_obstruction else 0.0
        rms_values = np.array([
            compute_coma_rms(a, telescope.focal_length,
                             telescope.primary_diameter, obs_ratio)
            for a in angles
        ])
        ax.plot(angles, rms_values * 1000, color=colors[i % len(colors)],
                linewidth=2, label=label)

        # Mark coma-free field for each
        cff = coma_free_field(telescope.focal_length,
                              telescope.primary_diameter, wavelength_mm)
        if 0 < cff <= max_field_arcsec:
            ax.axvline(cff, color=colors[i % len(colors)], linestyle=":",
                       alpha=0.5)

    # Airy radius reference (use first telescope)
    airy_radius = 1.22 * wavelength_mm * telescopes[0].focal_ratio
    ax.axhline(airy_radius * 1000, color="red", linestyle="--", alpha=0.5,
               label="Airy radius")

    ax.set_xlabel("Off-axis angle (arcsec)")
    ax.set_ylabel("RMS coma (µm)")
    ax.set_title("Coma Field Comparison")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.text(0.02, 0.98, "Approx: Seidel 3rd-order",
            transform=ax.transAxes, fontsize=7,
            verticalalignment="top", color="orange", alpha=0.8)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


# ── Source imaging ──────────────────────────────────────────────────────


def chromatic_defocus(telescope: Telescope,
                      wavelength_nm: float) -> float:
    """Compute focal length shift (mm) from design wavelength (550 nm).

    For a singlet refractor the shift follows the thin-lens relation:
        f(λ) / f_design = (n_design - 1) / (n_λ - 1)

    For an achromat the residual secondary spectrum is approximated as:
        Δf ≈ f / 2500   (small, nearly constant)

    For reflectors: returns 0 (no chromatic aberration).

    Args:
        telescope: The telescope instance.
        wavelength_nm: Wavelength to compute defocus for.

    Returns:
        Focal length shift in mm (positive = focus farther from lens).
    """
    from telescope_sim.physics.refraction import (
        GLASS_CATALOG, refractive_index_cauchy,
    )

    # Reflectors have zero chromatic aberration
    if not hasattr(telescope, 'objective'):
        return 0.0

    design_wl = 550.0
    f_design = telescope.focal_length

    obj_type = getattr(telescope, 'objective_type', 'singlet')

    # Parabolic chromatic model used for corrected designs (achromat / apo).
    # Achromats bring F (486) and C (656) to a *common* focus; the residual
    # is a parabola in wavelength symmetric about the F-C midpoint (571 nm).
    # The previous linear `abs(λ - 550)` model gave F and C unequal defocus
    # (Δ=64 vs Δ=106) which produced an unphysical red-dominant halo. Shift
    # the parabola so defocus at the user's focus wavelength (550) is zero.
    def _parabolic_chromatic_defocus(scale_mm: float) -> float:
        F_line, C_line = 486.1, 656.3
        mid = (F_line + C_line) / 2.0          # 571.2 nm
        half = (C_line - F_line) / 2.0         # 85.1 nm
        delta = wavelength_nm - mid
        delta_design = design_wl - mid
        # Subtract the design-wavelength offset → defocus at design = 0
        quad = (delta / half) ** 2 - (delta_design / half) ** 2
        return scale_mm * quad

    if obj_type == "achromat":
        # Residual secondary spectrum ≈ f/2500 at the F/C wavelengths
        return _parabolic_chromatic_defocus(f_design / 2500.0)
    elif obj_type == "apo-doublet":
        # ED+crown corrected at three wavelengths; residual ~f/8000
        return _parabolic_chromatic_defocus(f_design / 8000.0)
    elif obj_type == "apo-triplet":
        # Triplet correction is near diffraction-limited; residual ~f/20000
        return _parabolic_chromatic_defocus(f_design / 20000.0)
    else:
        # Singlet: full primary chromatic aberration
        glass = getattr(telescope.objective, 'glass', 'BK7')
        if glass in GLASS_CATALOG:
            coeffs = GLASS_CATALOG[glass]
        else:
            coeffs = GLASS_CATALOG["BK7"]
        n_design = refractive_index_cauchy(design_wl, coeffs["B"],
                                           coeffs["C"])
        n_wl = refractive_index_cauchy(wavelength_nm, coeffs["B"],
                                       coeffs["C"])
        f_wl = f_design * (n_design - 1.0) / (n_wl - 1.0)
        return f_wl - f_design


def chromatic_psf_kernel(
    telescope: Telescope,
    wavelength_nm: float,
    psf_size_pixels: int,
    psf_half_mm: float,
    include_obstruction: bool = True,
    focus_wavelength_nm: float = 550.0,
) -> np.ndarray:
    """Compute PSF kernel including chromatic defocus.

    When defocused, the PSF broadens into a filled disk (defocus
    aberration) convolved with the wavelength-scaled Airy pattern.

    For small defocus (< 0.5 pixel), returns the standard Airy PSF
    at the given wavelength.

    Args:
        telescope: Telescope instance.
        wavelength_nm: Wavelength in nm.
        psf_size_pixels: Kernel size in pixels.
        psf_half_mm: Half-width of the PSF kernel in mm.
        include_obstruction: Include secondary obstruction.
        focus_wavelength_nm: Wavelength the user is focused on. The
            returned PSF's defocus is computed relative to this focal
            plane: `defocus = chromatic_defocus(λ) - chromatic_defocus(focus_wl)`.

    Returns:
        2D PSF kernel, normalized to unit sum.
    """
    defocus_mm = (chromatic_defocus(telescope, wavelength_nm)
                  - chromatic_defocus(telescope, focus_wavelength_nm))

    # Compute standard Airy PSF at this wavelength
    airy_psf = _compute_psf_at_field_angle(
        telescope, 0.0, wavelength_nm, psf_size_pixels,
        psf_half_mm, include_obstruction,
    )

    # If defocus is negligible, return the Airy PSF
    pixel_scale_mm = 2.0 * psf_half_mm / psf_size_pixels
    defocus_radius_mm = abs(defocus_mm) / (2.0 * telescope.focal_ratio)
    defocus_radius_pix = defocus_radius_mm / pixel_scale_mm

    if defocus_radius_pix < 0.5:
        total = airy_psf.sum()
        if total > 0:
            airy_psf /= total
        return airy_psf

    # Build defocus disk kernel
    center = psf_size_pixels // 2
    coords = np.arange(psf_size_pixels) - center
    xx, yy = np.meshgrid(coords, coords)
    rr = np.sqrt(xx ** 2 + yy ** 2)
    defocus_disk = np.where(rr <= defocus_radius_pix, 1.0, 0.0)
    disk_sum = defocus_disk.sum()
    if disk_sum > 0:
        defocus_disk /= disk_sum

    # Convolve Airy with defocus disk
    from scipy.signal import fftconvolve
    psf = fftconvolve(airy_psf, defocus_disk, mode="same")
    total = psf.sum()
    if total > 0:
        psf /= total
    return psf


def _compute_spherical_aberration_spot(telescope: Telescope,
                                        num_pixels: int,
                                        half_size_mm: float,
                                        wavelength_nm: float = 550.0,
                                        num_rays: int = 21) -> np.ndarray:
    """Compute geometric spot pattern from spherical aberration.

    For parabolic mirrors: returns None (no spherical aberration).
    For spherical mirrors: traces rays and creates spot diagram.

    Args:
        telescope: Telescope object.
        num_pixels: Size of the output array.
        half_size_mm: Half-width of the region in mm.
        wavelength_nm: Wavelength for ray tracing.
        num_rays: Number of rays to trace.

    Returns:
        2D array representing the geometric spot, or None if no spherical aberration.
    """
    # Only compute for spherical primaries
    primary_type = getattr(telescope, 'primary_type', 'parabolic')
    if primary_type != 'spherical':
        return None

    # Trace rays through the telescope
    from telescope_sim.source.light_source import create_parallel_rays
    rays = create_parallel_rays(
        num_rays=num_rays,
        aperture_diameter=telescope.primary_diameter,
        entry_height=telescope.tube_length * 1.15,
        wavelength_nm=wavelength_nm,
    )
    telescope.trace_rays(rays)

    # Find focal plane positions
    y_offsets = _find_focal_plane_positions(rays)
    if y_offsets is None or len(y_offsets) == 0:
        return None

    # Build 2D spot image
    pixel_size = 2.0 * half_size_mm / num_pixels
    spot_image = np.zeros((num_pixels, num_pixels))
    center = num_pixels // 2

    # Defensive overflow check (see coma analogue in
    # _compute_psf_at_field_angle). If the SA caustic exceeds the
    # caller's half_size_mm grid, the clipped rays silently disappear
    # and the PSF looks artificially clean.
    if len(y_offsets) > 0:
        _max_y = float(np.max(np.abs(y_offsets)))
        if _max_y > half_size_mm:
            import warnings
            warnings.warn(
                f"Spherical-aberration caustic extent ({_max_y:.4f} mm) "
                f"exceeds spot half-width ({half_size_mm:.4f} mm). "
                f"Some rays will be clipped; expand half_size_mm at "
                f"the call site.",
                RuntimeWarning, stacklevel=2,
            )

    for y_offset in y_offsets:
        # Place each ray's position in the image
        iy = center + int(round(y_offset / pixel_size))
        # x is always 0 for our 2D ray tracing
        ix = center
        if 0 <= ix < num_pixels and 0 <= iy < num_pixels:
            spot_image[iy, ix] += 1.0

    # Smooth slightly for stability
    from scipy.ndimage import gaussian_filter
    spot_image = gaussian_filter(spot_image, sigma=0.5)

    return spot_image


def _compute_psf_at_field_angle(telescope: Telescope,
                                field_angle_arcsec: float,
                                wavelength_nm: float,
                                num_pixels: int,
                                half_size_mm: float,
                                include_obstruction: bool = True,
                                apply_coma: bool = True,
                                ) -> np.ndarray:
    """Compute the PSF at a given field angle, including coma and spherical aberration.

    For on-axis (field_angle_arcsec ~ 0):
        - Parabolic primary: pure diffraction PSF
        - Spherical primary: diffraction PSF convolved with spherical aberration spot

    For off-axis: convolves coma spot pattern with Airy kernel, and also includes
    spherical aberration if present.

    Returns:
        2D PSF array of shape (num_pixels, num_pixels), peak-normalized.
    """
    from scipy.signal import fftconvolve

    wavelength_mm = wavelength_nm * 1e-6
    f_ratio = telescope.focal_length / telescope.primary_diameter
    airy_radius = 1.22 * wavelength_mm * f_ratio
    obs_ratio = telescope.obstruction_ratio if include_obstruction else 0.0

    use_fft = telescope.spider_vanes > 0

    if abs(field_angle_arcsec) < 1e-6:
        # On-axis: diffraction PSF, plus spherical aberration if present
        if use_fft:
            base_pitch = wavelength_mm * f_ratio
            pixels_per_airy = airy_radius / base_pitch
            oversample = max(1, int(np.ceil(8.0 / pixels_per_airy)))
            oversample = min(oversample, 16)
            fft_psf, fft_half = compute_fft_psf(
                telescope.primary_diameter, telescope.focal_length,
                wavelength_mm, obs_ratio,
                telescope.spider_vanes, telescope.spider_vane_width,
                grid_size=256, oversample=oversample,
            )
            diffraction_psf = _resample_fft_psf(fft_psf, fft_half, half_size_mm,
                                                 num_pixels)
        else:
            coords = np.linspace(-half_size_mm, half_size_mm, num_pixels)
            xx, yy = np.meshgrid(coords, coords)
            rr = np.sqrt(xx ** 2 + yy ** 2)
            diffraction_psf = compute_psf(rr, telescope.primary_diameter,
                                          telescope.focal_length, wavelength_mm,
                                          obs_ratio)

        # Add spherical aberration if spherical primary
        sph_spot = _compute_spherical_aberration_spot(
            telescope, num_pixels, half_size_mm, wavelength_nm
        )
        if sph_spot is not None:
            # Convolve diffraction PSF with geometric spherical aberration
            sph_spot = sph_spot / sph_spot.sum()
            psf = fftconvolve(diffraction_psf, sph_spot, mode="same")
            if psf.max() > 0:
                psf /= psf.max()
            return psf
        else:
            return diffraction_psf
    elif apply_coma:
        # Off-axis: compute coma spot and convolve with Airy kernel
        x_off, y_off = compute_coma_spot(
            field_angle_arcsec, telescope.focal_length,
            telescope.primary_diameter, obs_ratio,
            num_pupil_zones=50, num_azimuthal=72,
        )

        # Defensive overflow check: the caller-supplied half_size_mm
        # should accommodate the full coma extent. The per-star path in
        # plot_source_image pre-expands the kernel for this (see H1
        # fix). If a future caller forgets, log a warning so the
        # silently-clipped coma doesn't masquerade as "no aberration".
        if len(x_off) > 0:
            max_off = max(float(np.max(np.abs(x_off))),
                          float(np.max(np.abs(y_off))))
            if max_off > half_size_mm:
                import warnings
                warnings.warn(
                    f"Coma spot extent ({max_off:.4f} mm) exceeds PSF "
                    f"kernel half-width ({half_size_mm:.4f} mm) at "
                    f"field_angle={field_angle_arcsec:.1f}\". Some rays "
                    f"will be clipped; expand half_size_mm at the call "
                    f"site.",
                    RuntimeWarning, stacklevel=2,
                )

        # Build geometric coma spot image
        pixel_size = 2.0 * half_size_mm / num_pixels
        coma_image = np.zeros((num_pixels, num_pixels))
        center = num_pixels // 2
        for xo, yo in zip(x_off, y_off):
            ix = center + int(round(xo / pixel_size))
            iy = center + int(round(yo / pixel_size))
            if 0 <= ix < num_pixels and 0 <= iy < num_pixels:
                coma_image[iy, ix] += 1.0

        # Gaussian smooth the geometric spot slightly for stability
        sigma_pix = max(1.0, airy_radius / pixel_size * 0.3)
        from scipy.ndimage import gaussian_filter
        coma_image = gaussian_filter(coma_image, sigma=sigma_pix)

        # Build Airy kernel
        kernel_half = max(airy_radius * 5, pixel_size * 3)
        kernel_n = min(num_pixels, 128)
        if use_fft:
            base_pitch = wavelength_mm * f_ratio
            pixels_per_airy = airy_radius / base_pitch
            oversample = max(1, int(np.ceil(8.0 / pixels_per_airy)))
            oversample = min(oversample, 16)
            fft_psf, fft_half = compute_fft_psf(
                telescope.primary_diameter, telescope.focal_length,
                wavelength_mm, obs_ratio,
                telescope.spider_vanes, telescope.spider_vane_width,
                grid_size=128, oversample=oversample,
            )
            kernel = _resample_fft_psf(fft_psf, fft_half, kernel_half,
                                       kernel_n)
        else:
            kcoords = np.linspace(-kernel_half, kernel_half, kernel_n)
            kxx, kyy = np.meshgrid(kcoords, kcoords)
            kr = np.sqrt(kxx ** 2 + kyy ** 2)
            kernel = compute_psf(kr, telescope.primary_diameter,
                                 telescope.focal_length, wavelength_mm,
                                 obs_ratio)
        kernel = kernel / kernel.sum()

        # Convolve coma with diffraction
        psf = fftconvolve(coma_image, kernel, mode="same")

        # Add spherical aberration if present
        sph_spot = _compute_spherical_aberration_spot(
            telescope, num_pixels, half_size_mm, wavelength_nm
        )
        if sph_spot is not None:
            sph_spot = sph_spot / sph_spot.sum()
            psf = fftconvolve(psf, sph_spot, mode="same")

        if psf.max() > 0:
            psf /= psf.max()
        return psf
    else:
        # apply_coma=False: treat off-axis as on-axis (diffraction only, no coma)
        return _compute_psf_at_field_angle(
            telescope, 0.0, wavelength_nm, num_pixels, half_size_mm,
            include_obstruction, apply_coma=True,
        )


def _apply_circular_taper(kernel: np.ndarray) -> np.ndarray:
    """Zero a square PSF kernel outside its inscribed circle, with a soft rim.

    A PSF kernel is a square array. The Airy/coma content falls to ~0 well
    before the array edge, but an asinh/log display stretch lifts the tiny
    residual in the *corners* into a faint square "box" around every star
    (and the geometric defocus disk in the polychromatic path fills its
    square support outright). Masking to the inscribed circle removes the
    square boundary; a short cosine taper over the outer rim avoids a hard
    circular edge. Applied only on the star paths (point/double/field) —
    extended-source spider spikes intentionally reach the kernel edge and
    must not be tapered.
    """
    n = kernel.shape[0]
    if n < 4:
        return kernel
    c = (n - 1) / 2.0
    yy, xx = np.ogrid[:n, :n]
    r = np.sqrt((xx - c) ** 2 + (yy - c) ** 2)
    radius = c  # inscribed-circle radius = half the array width
    t0 = 0.85 * radius  # begin tapering at 85% of the radius
    taper = np.ones_like(r)
    rim = (r > t0) & (r < radius)
    taper[rim] = 0.5 * (1.0 + np.cos(np.pi * (r[rim] - t0) / (radius - t0)))
    taper[r >= radius] = 0.0
    return kernel * taper


def _render_source_through_telescope(
        source, telescope: Telescope,
        wavelength_nm: float = 550.0,
        num_pixels: int = 512,
        seeing_arcsec: float | None = None,
        include_obstruction: bool = True,
        method: str = "analytical",
        polychromatic: bool = False,
        apply_coma: bool = True,
        apply_vignetting: bool = True,
        display_stretch: str = "linear",
        focus_wavelength_nm: float = 550.0,
        display_num_pixels: int | None = None,
        exposure_level: float = 1.0,
        filter_name: str = "None",
        exit_pupil_mm: float = EYE_PUPIL_MM,
        apply_aperture_diffraction: bool = True,
) -> tuple[np.ndarray, float, dict]:
    """Render an astronomical source as seen through the telescope.

    Pipeline:
    1. Determine field of view from source extent
    2. Build ideal source image
    3. Convolve with PSF (field-dependent for point sources, on-axis for
       extended objects like Jupiter)
    4. Apply vignetting
    5. Optional atmospheric seeing blur

    When *polychromatic* is True and the telescope has an objective lens
    (refractor), each RGB channel is convolved with a wavelength-specific
    PSF that includes chromatic defocus.  This produces realistic color
    fringing on high-contrast edges (e.g. Jupiter's limb).

    Args:
        source: An AstronomicalSource instance.
        telescope: The telescope to image through.
        wavelength_nm: Wavelength of light in nm.
        num_pixels: Image resolution.
        seeing_arcsec: Atmospheric seeing FWHM (full width at half maximum)
            of the seeing disk in arcseconds. This is the angular size
            a point source appears due to atmospheric turbulence.
            None = no atmosphere (space telescope).
        include_obstruction: Include secondary obstruction in PSF.
        method: PSF method ("analytical" or "traced").
        polychromatic: Use per-channel chromatic PSFs for refractors.

    Returns:
        Tuple of (image_2d, half_fov_arcsec, info_dict).
    """
    from scipy.signal import fftconvolve
    from telescope_sim.source.sources import PointSource, StarField, Jupiter

    half_fov_arcsec = source.field_extent_arcsec / 2.0
    focal_length = telescope.focal_length
    plate_scale = 206265.0 / focal_length  # arcsec/mm

    wavelength_mm = wavelength_nm * 1e-6
    f_ratio = focal_length / telescope.primary_diameter
    airy_radius_mm = 1.22 * wavelength_mm * f_ratio
    airy_radius_arcsec = airy_radius_mm * plate_scale

    # Aperture-area photon-collection factor: a telescope of diameter D
    # collects N ∝ D² photons. The reference aperture (APERTURE_REFERENCE_MM
    # = 100 mm) is the absolute brightness anchor — combined with
    # SATURATION_LEVEL, a mag-0 star through a 100 mm scope at unit exposure
    # peaks just below saturation. Computed once and reused by every source
    # branch + the final brightness normalisation.
    aperture_factor = (telescope.primary_diameter
                       / APERTURE_REFERENCE_MM) ** 2

    # FOV is taken directly from the source. We do NOT auto-expand the
    # FOV for severe-chromatic cases (singlet) — that made the singlet
    # frame look different from achromat/apo at the same scenario,
    # which obscures the lesson. The singlet halo overflowing the frame
    # is the lesson: chromatic spread can exceed the field you're
    # observing.

    # PSF kernel half-size in mm (enough to capture the Airy pattern)
    psf_half_mm = max(airy_radius_mm * 8, 0.001)
    psf_n = min(num_pixels, 256)

    # RGB image (only produced for Jupiter; None for other sources)
    image_rgb = None

    if isinstance(source, (PointSource, StarField)):
        # Per-star rendering: compute PSF at each star's field position,
        # apply vignetting, and place at correct image position.
        image = np.zeros((num_pixels, num_pixels))
        pixel_scale_arcsec = 2.0 * half_fov_arcsec / num_pixels
        pixel_scale_mm = pixel_scale_arcsec / plate_scale

        # The PSF kernel is computed in mm coordinates where psf_half_mm ∝ 1/D.
        # Without resampling, the Airy argument x = π·D·r/(λ·f) is invariant
        # to aperture (D cancels), so all apertures produce the same pixel
        # pattern. We must resample to the image canvas pixel scale so that
        # Airy radius differs visually with aperture.
        psf_pixel_scale_mm = 2.0 * psf_half_mm / psf_n
        psf_zoom = psf_pixel_scale_mm / pixel_scale_mm

        # Polychromatic per-star rendering: for refractors, compute per-channel
        # PSFs at R/G/B wavelengths so chromatic defocus produces visible color
        # fringing on stars. Falls back to single-channel for reflectors.
        # Aperture-off (R3.10) forces the single-channel delta path — with no
        # diffraction there is no chromatic PSF to speak of.
        _star_use_chromatic = (polychromatic
                                and hasattr(telescope, 'objective')
                                and apply_aperture_diffraction)

        if isinstance(source, PointSource):
            stars = [(source.field_angle_arcsec,
                      source.position_angle_deg,
                      source.magnitude)]
        else:
            # StarField: compute field angle and PA for each star
            stars = []
            for x_as, y_as, mag in zip(source.star_x_arcsec,
                                       source.star_y_arcsec,
                                       source.star_magnitudes):
                r = np.sqrt(x_as ** 2 + y_as ** 2)
                pa = np.degrees(np.arctan2(y_as, x_as))
                stars.append((r, pa, mag))

        # aperture_factor (photon-collection ∝ D²) is computed once above.

        # Expand the PSF kernel if the off-axis coma spot for any star
        # exceeds the Airy-only kernel size. Otherwise the spot pattern
        # built by _compute_psf_at_field_angle gets clipped to the
        # kernel edge, and the coma vanishes visually (worst at fast
        # f-ratios + large aperture — the bigger the scope, the more
        # severely it overflows). Formula: full coma spot extent =
        # 3 × C_s_max where C_s_max = θ·h_max²/(4·focal_length).
        h_max = telescope.primary_diameter / 2.0
        max_coma_extent_mm = 0.0
        if apply_coma:
            for field_r, _pa, _mg in stars:
                theta_rad = field_r / 206265.0
                c_s_max = (abs(theta_rad) * h_max ** 2
                            / (4.0 * telescope.focal_length))
                max_coma_extent_mm = max(max_coma_extent_mm,
                                         3.5 * c_s_max)
        needed_for_coma = max_coma_extent_mm * 1.2  # 20% margin
        if needed_for_coma > psf_half_mm:
            old_pixel_scale_mm = 2.0 * psf_half_mm / psf_n
            new_psf_n = int(2 * needed_for_coma / old_pixel_scale_mm)
            if new_psf_n % 2 == 0:
                new_psf_n += 1  # odd for symmetric centring
            new_psf_n = min(new_psf_n, num_pixels)
            psf_half_mm = needed_for_coma
            psf_n = max(psf_n, new_psf_n)
            psf_pixel_scale_mm = 2.0 * psf_half_mm / psf_n
            psf_zoom = psf_pixel_scale_mm / pixel_scale_mm

        # Expand the kernel for spider-vane diffraction spikes. The FFT PSF
        # spans ~100× the Airy radius, but the Airy-only kernel (8×) crops the
        # spikes to a stub — so a spider'd star showed no spikes on the
        # per-star path (only the extended-source path expanded for spiders).
        # Widen to ~45× Airy so the spikes read out to a useful length; the
        # per-star stamp is additive and scaled by intensity, so faint stars
        # contribute correspondingly faint spikes.
        if telescope.spider_vanes > 0:
            needed_for_spikes = airy_radius_mm * 45.0
            if needed_for_spikes > psf_half_mm:
                old_pixel_scale_mm = 2.0 * psf_half_mm / psf_n
                new_psf_n = int(2 * needed_for_spikes / old_pixel_scale_mm)
                if new_psf_n % 2 == 0:
                    new_psf_n += 1
                new_psf_n = min(new_psf_n, num_pixels)
                psf_half_mm = needed_for_spikes
                psf_n = max(psf_n, new_psf_n)
                psf_pixel_scale_mm = 2.0 * psf_half_mm / psf_n
                psf_zoom = psf_pixel_scale_mm / pixel_scale_mm

        if _star_use_chromatic:
            image_rgb = np.zeros((num_pixels, num_pixels, 3))
            channel_wavelengths = [656.3, 550.0, 486.1]  # R, G, B

            # Expand the PSF kernel if chromatic defocus is wider than the
            # Airy-only kernel half-size. Otherwise chromatic_psf_kernel's
            # defocus disk overflows the kernel — every pixel ends up inside
            # the (clipped) disk and the kernel renders as a uniform-fill
            # rectangle ("big squares"), not a defocus blur. Keep the same
            # pixel scale so Airy sampling is preserved.
            max_defocus_mm = max(
                abs(chromatic_defocus(telescope, wl))
                for wl in channel_wavelengths
            )
            max_defocus_radius_mm = (
                max_defocus_mm / (2.0 * telescope.focal_ratio)
            )
            needed_half_mm = max_defocus_radius_mm * 1.5
            if needed_half_mm > psf_half_mm:
                old_pixel_scale_mm = 2.0 * psf_half_mm / psf_n
                new_psf_n = int(2 * needed_half_mm / old_pixel_scale_mm)
                if new_psf_n % 2 == 0:
                    new_psf_n += 1  # odd for symmetric centring
                # Cap to image-canvas size to bound memory/compute
                new_psf_n = min(new_psf_n, num_pixels)
                psf_half_mm = needed_half_mm
                psf_n = max(psf_n, new_psf_n)
                # Refresh derived quantities used downstream / in closures
                psf_pixel_scale_mm = 2.0 * psf_half_mm / psf_n
                psf_zoom = psf_pixel_scale_mm / pixel_scale_mm

        def _resample_to_canvas(psf):
            """Resample a PSF kernel to match the image-canvas pixel scale."""
            if abs(psf_zoom - 1.0) > 0.02:
                from scipy.ndimage import zoom as _ndz, gaussian_filter as _gf
                if psf_zoom < 1.0:
                    # Anti-alias BEFORE downsampling. The spider-vane FFT PSF
                    # has fine high-frequency ring structure between the
                    # spikes; point/bilinear downsampling to the coarser
                    # canvas scale aliases it into a checkerboard moiré that
                    # fills the field and reads as "general blur". A Gaussian
                    # low-pass sized to the downsample factor removes the
                    # moiré while keeping the core + spikes.
                    psf = _gf(psf, sigma=0.5 / psf_zoom)
                psf = _ndz(psf, psf_zoom, order=1)
                psf = np.maximum(psf, 0.0)
                max_half = num_pixels // 2
                h = psf.shape[0] // 2
                if h > max_half:
                    psf = psf[h - max_half:h + max_half + 1,
                               h - max_half:h + max_half + 1]
            return psf

        # Per-star spectral RGB tints (MultiColorStarField); default to
        # equal weights (white star) for plain StarField/PointSource.
        star_rgb = getattr(source, "star_spectral_rgb", None)

        for star_idx, (field_r, pa_deg, mag) in enumerate(stars):
            # Absolute intensity: photon flux from this magnitude × aperture²
            intensity = 10.0 ** (-0.4 * mag) * aperture_factor
            # Per-channel RGB weights for THIS star (used by the
            # polychromatic branch). Defaults to (1, 1, 1) — white.
            if star_rgb is not None and star_idx < len(star_rgb):
                star_color = tuple(float(c) for c in star_rgb[star_idx])
            else:
                star_color = (1.0, 1.0, 1.0)

            # Vignetting at this field angle
            vignetting = telescope.compute_vignetting(field_r) if apply_vignetting else 1.0

            # Compute PSF at this field angle (single-channel path).
            # The polychromatic branch below recomputes per-wavelength PSFs.
            if apply_aperture_diffraction:
                psf = _compute_psf_at_field_angle(
                    telescope, field_r, wavelength_nm, psf_n,
                    psf_half_mm, include_obstruction, apply_coma,
                )
                psf = _resample_to_canvas(psf)
            else:
                # Aperture diffraction suppressed (R3.10 idealization to
                # isolate the seeing limit): render the star as an ideal
                # point at the canvas scale — a delta — so only atmospheric
                # seeing (if enabled) blurs it. NOT physical (every real
                # aperture diffracts); flagged in the scenario description.
                #
                # Preserve TOTAL FLUX: give the delta the same integrated
                # flux as the real (peak-normalised) aperture PSF would
                # carry, so toggling aperture changes the star's SHARPNESS,
                # not its brightness (the display uses a fixed brightness
                # anchor, so an under-flux delta would render nearly black).
                _ref = _compute_psf_at_field_angle(
                    telescope, field_r, wavelength_nm, psf_n,
                    psf_half_mm, include_obstruction, apply_coma,
                )
                _ref = _resample_to_canvas(_ref)
                _flux = float(_ref.sum())
                psf = np.zeros((3, 3))
                psf[1, 1] = _flux if _flux > 0 else 1.0

            # Coma tails point radially outward from the optical axis.
            # compute_coma_spot produces a fixed-orientation comet (tail
            # along +x). Rotate by the star's position angle so the tail
            # points away from the optical axis at this star's location.
            # Skip rotation when the star is on-axis (pa undefined) or
            # when coma is disabled.
            if apply_coma and field_r > 1e-6 and abs(pa_deg) > 1e-6:
                from scipy.ndimage import rotate as _ndrotate
                psf = _ndrotate(psf, pa_deg, reshape=False, order=1,
                                mode='constant', cval=0.0)
                # Rotation interpolation can produce tiny negative
                # values from order=1 spline tails; clip.
                psf = np.maximum(psf, 0.0)

            # Star position in the image (pixel coords)
            pa_rad = np.radians(pa_deg)
            star_x_arcsec = field_r * np.cos(pa_rad)
            star_y_arcsec = field_r * np.sin(pa_rad)
            cx = int(round(num_pixels / 2
                           + star_x_arcsec / pixel_scale_arcsec))
            cy = int(round(num_pixels / 2
                           + star_y_arcsec / pixel_scale_arcsec))

            # Circular taper so the square kernel support doesn't show as a
            # faint box around the star under an asinh/log display stretch.
            psf = _apply_circular_taper(psf)

            # Stamp PSF into image using array slices (faster than pixel loop)
            psf_h, psf_w = psf.shape
            psf_hh = psf_h // 2

            y_start = cy - psf_hh
            x_start = cx - psf_hh
            y1 = max(0, y_start)
            y2 = min(num_pixels, y_start + psf_h)
            x1 = max(0, x_start)
            x2 = min(num_pixels, x_start + psf_w)
            py1 = y1 - y_start
            py2 = py1 + (y2 - y1)
            px1 = x1 - x_start
            px2 = px1 + (x2 - x1)

            if y2 > y1 and x2 > x1:
                image[y1:y2, x1:x2] += (
                    psf[py1:py2, px1:px2] * intensity * vignetting
                )

            # Intrinsic stellar colour (non-chromatic path): when the source
            # carries spectral tints but we're NOT doing the per-wavelength
            # chromatic render (reflector, or refractor with polychromatic
            # off), still tint the star by its SED. A star's colour is
            # intrinsic — it is NOT an artefact of chromatic aberration, so a
            # reflector must show it too. Same PSF for all channels (no
            # chromatic halo); saturation then clips all channels → white,
            # demonstrating saturation whiteout / cone desaturation on a
            # coloured star. Gated on star_rgb so plain white stars stay on
            # the grayscale path unchanged.
            if (star_rgb is not None and not _star_use_chromatic
                    and y2 > y1 and x2 > x1):
                if image_rgb is None:
                    image_rgb = np.zeros((num_pixels, num_pixels, 3))
                stamp = psf[py1:py2, px1:px2] * intensity * vignetting
                for ch in range(3):
                    image_rgb[y1:y2, x1:x2, ch] += stamp * star_color[ch]

            # Polychromatic per-channel stamping. Each R/G/B PSF includes
            # the chromatic defocus for its wavelength so a singlet refractor
            # produces visible colored halos around each star.
            #
            # chromatic_psf_kernel is sum-normalised (energy-conserving):
            # the in-focus channel concentrates energy into the Airy core
            # (bright sharp point); defocused channels spread the same
            # total energy over the defocus disk (naturally dim halo).
            # This is the physically-correct rendering — the previous
            # per-channel PEAK normalisation made every halo uniformly
            # bright at the in-focus peak, so overlapping halos from
            # multiple stars saturated R+B and washed out the in-focus G
            # cores ("all stars look red-magenta regardless of intrinsic
            # tint"). A display stretch is applied at the end of this
            # function so the now-dim halos remain visible without
            # saturating the bright cores.
            # Computation is roughly 3x the monochrome path; only enabled
            # when polychromatic and a refractor objective is present.
            if _star_use_chromatic:
                # Build all three channel kernels (sum-normalised, so the
                # in-focus channel keeps a high peak and defocused channels
                # spread into dim disks — the chromatic effect).
                ch_kernels = []
                for wl_ch in channel_wavelengths:
                    psf_ch = chromatic_psf_kernel(
                        telescope, wl_ch, psf_n, psf_half_mm,
                        include_obstruction,
                        focus_wavelength_nm=focus_wavelength_nm,
                    )
                    psf_ch = _resample_to_canvas(psf_ch)
                    # Circular taper: removes the square box and turns the
                    # geometric defocus disk (which fills its square support)
                    # into the physically-correct circular disk.
                    psf_ch = _apply_circular_taper(psf_ch)
                    ch_kernels.append(psf_ch)
                # Anchor brightness to the peak-normalised convention used by
                # the (monochrome) per-star path: divide all channels by the
                # SHARPEST channel's peak so the in-focus channel peaks at ~1
                # (× intensity), matching a non-chromatic star of the same
                # magnitude. Without this, the sum-normalised kernels made
                # chromatic stars render ~6× too faint (peak 0.16 vs 0.89) —
                # the "chromatic + seeing everything is too dim" bug. The
                # RELATIVE peaks are preserved, so defocused channels still
                # show as dim colour halos.
                common_peak = max((float(k.max()) for k in ch_kernels),
                                  default=0.0)
                if common_peak > 0:
                    ch_kernels = [k / common_peak for k in ch_kernels]
                for ch, psf_ch in enumerate(ch_kernels):
                    psf_ch_h, psf_ch_w = psf_ch.shape
                    psf_ch_hh = psf_ch_h // 2
                    y_start_c = cy - psf_ch_hh
                    x_start_c = cx - psf_ch_hh
                    y1c = max(0, y_start_c)
                    y2c = min(num_pixels, y_start_c + psf_ch_h)
                    x1c = max(0, x_start_c)
                    x2c = min(num_pixels, x_start_c + psf_ch_w)
                    py1c = y1c - y_start_c
                    py2c = py1c + (y2c - y1c)
                    px1c = x1c - x_start_c
                    px2c = px1c + (x2c - x1c)
                    if y2c > y1c and x2c > x1c:
                        # Modulate by the star's spectral RGB weight so a
                        # red star contributes mostly to R, etc. White
                        # stars (default 1,1,1) behave as before.
                        image_rgb[y1c:y2c, x1c:x2c, ch] += (
                            psf_ch[py1c:py2c, px1c:px2c]
                            * intensity * vignetting * star_color[ch]
                        )

    elif hasattr(source, 'render_ideal_rgb'):
        # Extended source with RGB colors (Jupiter, Saturn, Moon, etc.)
        # Convolve ideal image with on-axis PSF. For objects small enough
        # that PSF variation across the disk is negligible, a single
        # on-axis PSF kernel is used.
        ideal = source.render_ideal(half_fov_arcsec, num_pixels)
        ideal_rgb = source.render_ideal_rgb(half_fov_arcsec, num_pixels)

        # aperture_factor (photon-collection ∝ D²) is computed once above.
        # The source's `render_ideal*` returns a peak-normalised disk;
        # multiply by D²/D_ref² so absolute brightness tracks aperture in
        # the detector view. (The eye view rescales this at the brightness
        # step, where surface brightness is exit-pupil-driven instead.)
        ideal = ideal * aperture_factor
        ideal_rgb = ideal_rgb * aperture_factor

        # Build on-axis PSF kernel on the same angular pixel scale,
        # then convolve in image space.
        psf_angular_half = airy_radius_arcsec * 8
        # Spider spikes extend much further than 8× Airy radius; enlarge
        # kernel so spikes are not truncated before reaching the image.
        if telescope.spider_vanes > 0:
            psf_angular_half = max(psf_angular_half, airy_radius_arcsec * 60)
        # Convert to same pixel scale as the image
        pixel_scale_arcsec = 2.0 * half_fov_arcsec / num_pixels
        psf_n_img = max(16, int(2 * psf_angular_half / pixel_scale_arcsec))
        psf_n_img = min(psf_n_img, num_pixels)
        if psf_n_img % 2 == 0:
            psf_n_img += 1  # odd for symmetric kernel

        psf_half_for_kernel = psf_angular_half / plate_scale

        # Apply vignetting (uniform across small Jupiter disk)
        vignetting = telescope.compute_vignetting(0.0) if apply_vignetting else 1.0

        # Polychromatic mode: use per-channel chromatic PSFs for
        # refractors to show color fringing.
        _use_chromatic = (polychromatic
                          and hasattr(telescope, 'objective'))

        if _use_chromatic:
            # R, G, B channel wavelengths (nm)
            channel_wavelengths = [656.3, 550.0, 486.1]

            # Need a larger PSF kernel to capture chromatic defocus
            max_defocus = max(
                abs(chromatic_defocus(telescope, wl))
                for wl in channel_wavelengths
            )
            defocus_radius_mm = max_defocus / (2.0 * telescope.focal_ratio)
            defocus_angular = defocus_radius_mm * plate_scale
            chromatic_half = max(psf_angular_half,
                                 defocus_angular * 3 + psf_angular_half)
            chromatic_n = max(
                psf_n_img,
                int(2 * chromatic_half / pixel_scale_arcsec),
            )
            chromatic_n = min(chromatic_n, num_pixels)
            if chromatic_n % 2 == 0:
                chromatic_n += 1
            chromatic_half_mm = chromatic_half / plate_scale

            image_rgb = np.zeros_like(ideal_rgb)
            for ch, wl in enumerate(channel_wavelengths):
                psf_kernel = chromatic_psf_kernel(
                    telescope, wl, chromatic_n, chromatic_half_mm,
                    include_obstruction,
                )
                image_rgb[..., ch] = (
                    fftconvolve(ideal_rgb[..., ch], psf_kernel,
                                mode="same") * vignetting
                )

            # Grayscale from luminance
            image = (0.2126 * image_rgb[..., 0]
                     + 0.7152 * image_rgb[..., 1]
                     + 0.0722 * image_rgb[..., 2])

        else:
            psf = _compute_psf_at_field_angle(
                telescope, 0.0, wavelength_nm, psf_n_img,
                psf_half_for_kernel, include_obstruction, apply_coma,
            )
            psf_sum = psf.sum()
            psf_kernel = psf / psf_sum if psf_sum > 0 else psf

            image = fftconvolve(ideal, psf_kernel, mode="same") * vignetting

            # Convolve each RGB channel with the PSF for color rendering
            image_rgb = np.zeros_like(ideal_rgb)
            for c in range(3):
                image_rgb[..., c] = (
                    fftconvolve(ideal_rgb[..., c], psf_kernel,
                                mode="same") * vignetting
                )

    else:
        # Generic fallback (e.g. DoubleStar): convolve ideal with on-axis PSF.
        # The PSF kernel is built in mm coords on a fixed grid; without
        # resampling to the image's angular pixel scale, the convolution
        # produces aperture-invariant results (same bug as the per-star path
        # before F1.4). Resample the PSF to match the image pixel scale so
        # different apertures yield different rendered images.
        ideal = source.render_ideal(half_fov_arcsec, num_pixels)
        # aperture_factor (photon-collection ∝ D²) is computed once above.
        ideal = ideal * aperture_factor
        pixel_scale_arcsec = 2.0 * half_fov_arcsec / num_pixels
        pixel_scale_mm = pixel_scale_arcsec / plate_scale
        psf_pixel_scale_mm = 2.0 * psf_half_mm / psf_n
        psf_zoom = psf_pixel_scale_mm / pixel_scale_mm

        psf = _compute_psf_at_field_angle(
            telescope, 0.0, wavelength_nm, psf_n,
            psf_half_mm, include_obstruction, apply_coma,
        )
        if abs(psf_zoom - 1.0) > 0.02:
            from scipy.ndimage import zoom as _ndz, gaussian_filter as _gf
            if psf_zoom < 1.0:
                # Anti-alias before downsampling (same rationale as the
                # per-star path): avoid a spider-spike checkerboard moiré.
                psf = _gf(psf, sigma=0.5 / psf_zoom)
            psf = _ndz(psf, psf_zoom, order=1)
            psf = np.maximum(psf, 0.0)
            max_half = num_pixels // 2
            h = psf.shape[0] // 2
            if h > max_half:
                psf = psf[h - max_half:h + max_half + 1,
                           h - max_half:h + max_half + 1]

        # Circular taper so the square kernel support doesn't print as a
        # faint box around each star (DoubleStar convolves two deltas with
        # this kernel, reproducing its square edge at each star location).
        psf = _apply_circular_taper(psf)

        # Peak-normalised PSF kernel — convolving with a delta of
        # absolute intensity I yields peak = I. This matches the
        # per-star path (which stamps the peak-normalised kernel
        # scaled by intensity). Using a sum-normalised kernel here
        # would suppress the peak by 1/PSF_area and make point-like
        # sources via the generic fallback render dim relative to
        # PointSource/StarField at the same magnitude.
        psf_peak = psf.max()
        psf_kernel = psf / psf_peak if psf_peak > 0 else psf
        image = fftconvolve(ideal, psf_kernel, mode="same")

    # ── Detector binning (physically-correct flux integration) ────────
    # When an extended source is rendered at a higher internal
    # resolution (for accurate PSF convolution), the array is then
    # sum-binned down to the requested display resolution. Each output
    # pixel = sum of the high-res pixels falling within its angular
    # area — exactly what a coarser detector would record. This is
    # more physically honest than matplotlib's bilinear interpolation
    # (which averages and dilutes sub-pixel features).
    if (display_num_pixels is not None
            and 0 < display_num_pixels < num_pixels):
        bin_factor = num_pixels // display_num_pixels
        if bin_factor >= 2:
            target_n = bin_factor * display_num_pixels
            if target_n < num_pixels:
                # Crop center if num_pixels isn't an exact multiple
                start = (num_pixels - target_n) // 2
                image = image[start:start + target_n,
                              start:start + target_n]
                if image_rgb is not None:
                    image_rgb = image_rgb[start:start + target_n,
                                           start:start + target_n]
            image = image.reshape(
                display_num_pixels, bin_factor,
                display_num_pixels, bin_factor
            ).sum(axis=(1, 3))
            if image_rgb is not None:
                image_rgb = image_rgb.reshape(
                    display_num_pixels, bin_factor,
                    display_num_pixels, bin_factor, 3
                ).sum(axis=(1, 3))
            num_pixels = display_num_pixels

    # ── Absolute brightness normalisation (view-dependent) ───────────────
    # Divide by a fixed reference so a mag-0 star through a 100 mm scope at
    # unit exposure peaks just below 1.0; brighter sources / larger apertures
    # legitimately saturate, fainter ones sit at their true relative
    # brightness. (The previous code divided by image.max(), forcing every
    # frame's brightest pixel to 1.0 — that erased absolute brightness and
    # made aperture/exposure changes invisible.) Seeing-induced peak dimming
    # is captured naturally: seeing spreads flux so post-seeing peak <
    # pre-seeing peak, both referenced to the same fixed level.
    #
    # WHAT DRIVES BRIGHTNESS depends on the display view (Phase 1.4):
    #   Detector (linear): brightness ∝ collected photons × exposure time.
    #     exposure_level scales the signal linearly — a long exposure of a
    #     faint star eventually saturates. This is what a CCD records.
    #   Eye (log / log_integrated): exposure does NOT apply — the eye has a
    #     fixed ~0.1 s integration, it can't "expose longer". Brightness
    #     comes from the optics instead:
    #       • point-like sources (stars): retinal illuminance ∝ collected
    #         photons (∝ D², already in aperture_factor), magnification-
    #         independent — a bigger scope shows brighter stars.
    #       • extended sources (planets/Moon): a telescope can never raise
    #         surface brightness above the naked-eye level, and at higher
    #         magnification (smaller exit pupil) it falls as
    #         (exit_pupil / eye_pupil)². So the D² aperture_factor baked into
    #         `ideal*` is divided back out and replaced by the exit-pupil
    #         surface-brightness factor (aperture-independent surface
    #         brightness — bigger scope buys resolution, not surface
    #         brightness). Perceptual model — flagged in the UI annotation.
    is_eye_view = display_stretch in ("log", "log_integrated")
    is_extended_source = hasattr(source, "render_ideal_rgb")
    eye_surface_brightness_factor = None
    if is_eye_view:
        effective_exposure = 1.0
        if is_extended_source:
            eye_surface_brightness_factor = min(
                1.0, (exit_pupil_mm / EYE_PUPIL_MM) ** 2)
            brightness_scale = eye_surface_brightness_factor / aperture_factor
        else:
            brightness_scale = 1.0
    else:
        effective_exposure = exposure_level
        brightness_scale = 1.0

    saturation_divisor = SATURATION_LEVEL / (
        max(effective_exposure, 1e-9) * max(brightness_scale, 1e-12))

    # Optional atmospheric seeing
    if seeing_arcsec is not None and seeing_arcsec > 0:
        # Atmospheric turbulence blurs the image with a Gaussian PSF.
        # seeing_arcsec is the FWHM (full width at half maximum) of
        # the seeing disk in arcseconds.
        # Convert FWHM to standard deviation: σ = FWHM / 2.355
        # (where 2.355 ≈ 2*sqrt(2*ln(2)) for a Gaussian)
        pixel_scale_arcsec = 2.0 * half_fov_arcsec / num_pixels
        seeing_sigma_pix = (seeing_arcsec / 2.355) / pixel_scale_arcsec
        coords = np.arange(num_pixels) - num_pixels / 2
        sxx, syy = np.meshgrid(coords, coords)
        # 2D Gaussian kernel: exp(-(x²+y²)/(2σ²))
        seeing_kernel = np.exp(-(sxx ** 2 + syy ** 2)
                               / (2 * seeing_sigma_pix ** 2))
        seeing_kernel /= seeing_kernel.sum()
        image = fftconvolve(image, seeing_kernel, mode="same")
        if image_rgb is not None:
            for c in range(3):
                image_rgb[..., c] = fftconvolve(image_rgb[..., c],
                                                seeing_kernel, mode="same")
    # Three display modes (all are display-only; the simulated data
    # is unchanged — the modes differ only in how pixel values are
    # mapped to screen brightness):
    #   "linear"          (Detector view): raw per-pixel intensity.
    #                     What a calibrated CCD records.
    #   "log"             (Eye view): asinh stretch only. Matches the
    #                     eye's logarithmic intensity response (Pogson
    #                     magnitude scale). Dim features visible next
    #                     to bright ones.
    #   "log_integrated"  (Eye + integration): asinh + 1″ FWHM spatial
    #                     Gaussian. Adds the eye's spatial resolution
    #                     at ~60× eyepiece magnification — per-pixel
    #                     channels mix near each star's core, so the
    #                     perceived core color matches what an observer
    #                     would see through an eyepiece rather than
    #                     what a per-pixel detector would record.

    # Optional eye spatial integration (mode 3 only)
    if display_stretch == "log_integrated":
        from scipy.ndimage import gaussian_filter
        eye_sigma_arcsec = 1.0 / 2.355  # 1″ FWHM → sigma
        pixel_scale_arcsec = 2.0 * half_fov_arcsec / image.shape[0]
        eye_sigma_pix = eye_sigma_arcsec / pixel_scale_arcsec
        if eye_sigma_pix > 0.5:
            image = gaussian_filter(image, sigma=eye_sigma_pix)
            if image_rgb is not None:
                for c in range(3):
                    image_rgb[..., c] = gaussian_filter(
                        image_rgb[..., c], sigma=eye_sigma_pix)

    # Filter transmission — applied *before* saturation normalisation
    # so the filter genuinely reduces collected photons (a 10% ND on
    # a saturated source recovers detail; a colour filter shifts the
    # RGB balance). Channel-wise multiply for polychromatic / RGB
    # rendering, single multiply for the grayscale luminance.
    from telescope_sim.physics.filters import get_filter_by_name
    _flt = get_filter_by_name(filter_name)
    if _flt.name != "None":
        T_lum = _flt.luminance_transmission
        T_R, T_G, T_B = _flt.channel_transmissions()
        image = image * T_lum
        if image_rgb is not None:
            image_rgb = image_rgb.copy()
            image_rgb[..., 0] *= T_R
            image_rgb[..., 1] *= T_G
            image_rgb[..., 2] *= T_B

    # Apply the fixed-reference normalisation. Values above 1.0 will
    # be clipped by the final np.clip — that's the saturation effect.
    image = image / saturation_divisor
    if image_rgb is not None:
        image_rgb = image_rgb / saturation_divisor

    # Cone-desaturation (Eye-view modes only): at high linear flux the
    # eye's colour discrimination drops — bright sources appear
    # whitewashed. Blend RGB toward grey luminance by w = I / (I + I_sat)
    # so high-flux pixels desaturate smoothly without ad-hoc thresholds.
    # I_sat = 0.5 means a pixel at the saturation level is ~half-blended
    # toward grey; very bright (clipped) pixels are nearly white.
    if (display_stretch in ("log", "log_integrated")
            and image_rgb is not None):
        lum = (0.2126 * image_rgb[..., 0]
               + 0.7152 * image_rgb[..., 1]
               + 0.0722 * image_rgb[..., 2])
        I_sat = 0.5
        w_desat = lum / (lum + I_sat)
        # Broadcast: blend each channel toward luminance.
        image_rgb = (image_rgb
                     + w_desat[..., None] * (lum[..., None] - image_rgb))

    if display_stretch in ("log", "log_integrated"):
        a = 0.001
        norm = np.arcsinh(1.0 / a)
        image = np.arcsinh(image / a) / norm
        if image_rgb is not None:
            # Chroma-preserving asinh: stretch the LUMINANCE and scale the
            # RGB triplet by the same factor, instead of stretching each
            # channel independently. Per-channel asinh over-lifts the dim
            # channels (a 2%-green leak becomes ~50% after asinh), collapsing
            # every dim colour toward grey-green — which made the spectral
            # stars render uniformly green and washed out colour-filtered
            # planets. Preserving the RGB ratio keeps hue intact while still
            # boosting dim features; bright pixels are already desaturated by
            # the cone-desaturation step above.
            lum = (0.2126 * image_rgb[..., 0]
                   + 0.7152 * image_rgb[..., 1]
                   + 0.0722 * image_rgb[..., 2])
            lum_stretched = np.arcsinh(lum / a) / norm
            with np.errstate(divide="ignore", invalid="ignore"):
                scale = np.where(lum > 1e-9, lum_stretched / lum, 0.0)
            image_rgb = image_rgb * scale[..., None]

    image = np.clip(image, 0.0, 1.0)
    if image_rgb is not None:
        image_rgb = np.clip(image_rgb, 0.0, 1.0)

    info = dict(
        wavelength_nm=wavelength_nm,
        f_ratio=f_ratio,
        airy_radius_arcsec=airy_radius_arcsec,
        airy_radius_mm=airy_radius_mm,
        plate_scale=plate_scale,
        half_fov_arcsec=half_fov_arcsec,
        seeing_arcsec=seeing_arcsec,
        include_obstruction=include_obstruction,
        source_type=type(source).__name__,
        image_rgb=image_rgb,
        polychromatic=polychromatic,
        # Brightness-model metadata (Phase 1.4) for the UI annotation.
        is_eye_view=is_eye_view,
        exposure_applied=(not is_eye_view),
        exit_pupil_mm=exit_pupil_mm,
        eye_surface_brightness_factor=eye_surface_brightness_factor,
    )
    return image, half_fov_arcsec, info


def _draw_source_on_axes(ax, image, image_rgb, half_fov, log_scale,
                         colormap, fig):
    """Draw a rendered source image onto the given axes.

    Returns the imshow artist.
    """
    extent = [-half_fov, half_fov, -half_fov, half_fov]

    if image_rgb is not None:
        im = ax.imshow(image_rgb, extent=extent, origin="lower",
                       interpolation="bilinear")
    else:
        if colormap is None:
            colormap = "gray"

        if log_scale and image.max() > 0:
            display_image = np.log10(np.clip(image, 1e-4, None))
            vmin = -4.0
            vmax = 0.0
        else:
            display_image = image
            vmin = 0.0
            vmax = 1.0

        im = ax.imshow(display_image, extent=extent, origin="lower",
                       cmap=colormap, vmin=vmin, vmax=vmax,
                       interpolation="bilinear")

        cbar_label = ("log\u2081\u2080(Intensity)" if log_scale
                      else "Normalized intensity")
        fig.colorbar(im, ax=ax, label=cbar_label, shrink=0.85)

    return im


def _crop_or_pad_to_fov(image, image_rgb, current_half_fov, target_half_fov):
    """Crop or pad an image to match a target field of view.

    Args:
        image: 2D grayscale image array.
        image_rgb: 3D RGB image array or None.
        current_half_fov: Current half-FOV in arcseconds.
        target_half_fov: Desired half-FOV in arcseconds.

    Returns:
        Tuple of (cropped_image, cropped_rgb, new_half_fov).
    """
    num_pixels = image.shape[0]

    if target_half_fov < current_half_fov:
        # Crop to smaller FOV
        frac = target_half_fov / current_half_fov
        crop_size = max(1, int(num_pixels * frac))
        if crop_size % 2 == 0:
            crop_size += 1
        start = (num_pixels - crop_size) // 2
        end = start + crop_size
        image = image[start:end, start:end]
        if image_rgb is not None:
            image_rgb = image_rgb[start:end, start:end]
        new_half_fov = target_half_fov
    elif target_half_fov > current_half_fov:
        # Pad with black sky
        frac = current_half_fov / target_half_fov
        source_size = max(1, int(num_pixels * frac))
        padded = np.zeros((num_pixels, num_pixels))
        start = (num_pixels - source_size) // 2
        end = start + source_size
        # Resample source into the smaller region
        from scipy.ndimage import zoom
        scale = source_size / num_pixels
        resized = zoom(image, scale, order=1)
        # Handle rounding differences
        sy, sx = resized.shape
        padded[start:start + sy, start:start + sx] = resized
        image = padded
        if image_rgb is not None:
            padded_rgb = np.zeros((num_pixels, num_pixels, 3))
            for c in range(3):
                resized_c = zoom(image_rgb[..., c], scale, order=1)
                padded_rgb[start:start + sy, start:start + sx, c] = resized_c
            image_rgb = np.clip(padded_rgb, 0.0, 1.0)
        new_half_fov = target_half_fov
    else:
        new_half_fov = current_half_fov

    return image, image_rgb, new_half_fov


def _apply_exit_pupil_washout(image, image_rgb, exit_pupil_mm):
    """Apply perceptual washout from large exit pupil on bright extended objects.

    At low magnification (large exit pupil), bright extended objects like
    planets appear washed out with reduced contrast and color saturation.
    The "comfortable" exit pupil for planetary viewing is ~1-2mm; above
    ~3-5mm, the retina receives more light than needed, reducing perceived
    contrast.

    Approximation notes (not physiologically calibrated):
    - Sigmoid coefficients (midpoint=3mm, steepness=1.5) are empirical,
      not derived from psychophysical data.
    - Saturation reduction factor (0.8 at full washout) is aggressive;
      real desaturation varies by individual — this is tunable.
    - No surface brightness dependence: a dim extended nebula is treated
      the same as bright Jupiter at equal exit pupil.
    - No Purkinje shift: dark-adapted scotopic color sensitivity is not
      modeled (blue shift at low light levels).
    """
    # Work on copies so callers' arrays are not mutated in place
    image = image.copy()
    if image_rgb is not None:
        image_rgb = image_rgb.copy()

    washout = 1.0 / (1.0 + np.exp(-1.5 * (exit_pupil_mm - 3.0)))

    contrast_factor = 1.0 - 0.7 * washout
    saturation_factor = 1.0 - 0.8 * washout

    # Contrast reduction: blend toward mean brightness
    mean_val = image.mean()
    image = mean_val + contrast_factor * (image - mean_val)
    image = np.clip(image, 0.0, 1.0)

    if image_rgb is not None:
        # Pass 1: contrast reduction on all channels
        for c in range(3):
            channel = image_rgb[..., c]
            mean_c = channel.mean()
            image_rgb[..., c] = mean_c + contrast_factor * (channel - mean_c)

        # Pass 2: desaturation — compute luminance from *contrast-reduced*
        # channels so the blend target is consistent with the modified image
        luminance = (0.2126 * image_rgb[..., 0]
                     + 0.7152 * image_rgb[..., 1]
                     + 0.0722 * image_rgb[..., 2])
        for c in range(3):
            image_rgb[..., c] = (luminance
                                 + saturation_factor
                                 * (image_rgb[..., c] - luminance))
        image_rgb = np.clip(image_rgb, 0.0, 1.0)

    return image, image_rgb, washout


def plot_source_image(telescope: Telescope,
                      source,
                      wavelength_nm: float = 550.0,
                      num_pixels: int = 512,
                      seeing_arcsec: float | None = None,
                      include_obstruction: bool = True,
                      method: str = "analytical",
                      log_scale: bool = False,
                      colormap: str | None = None,
                      title: str | None = None,
                      figsize: tuple[float, float] = (8, 7),
                      save_path: str | None = None,
                      eyepiece=None,
                      polychromatic: bool = False,
                      eyepiece_view_figsize: tuple[float, float] | None = None,
                      apply_coma: bool = True,
                      apply_vignetting: bool = True,
                      display_stretch: str = "linear",
                      focus_wavelength_nm: float = 550.0,
                      exposure_level: float = 1.0,
                      filter_name: str = "None",
                      exit_pupil_mm: float = EYE_PUPIL_MM,
                      apply_aperture_diffraction: bool = True,
                      ) -> plt.Figure | list[plt.Figure]:
    """Plot a simulated image of an astronomical source through the telescope.

    Args:
        telescope: The telescope to image through.
        source: An AstronomicalSource instance (PointSource, StarField,
            Jupiter, Saturn, Moon, etc.).
        wavelength_nm: Wavelength of light in nm.
        num_pixels: Image resolution (pixels per side).
        seeing_arcsec: Atmospheric seeing FWHM (full width at half maximum)
            of the seeing disk in arcseconds. This is the angular size
            a point source appears due to atmospheric turbulence.
            None = no atmosphere (space telescope).
        include_obstruction: Include secondary obstruction in PSF.
        method: PSF method ("analytical" or "traced").
        log_scale: Use logarithmic intensity scaling.
        colormap: Matplotlib colormap name (default: "gray" for stars;
            extended sources with RGB ignore this).
        title: Plot title (auto-generated if None).
        figsize: Figure size in inches.
        save_path: If provided, save figure to this path.
        eyepiece: An Eyepiece instance for visual observing simulation.
            When provided, crops/pads the image to the eyepiece's true FOV
            and produces a second "true angular size" figure.

    Returns:
        A single Figure (no eyepiece) or a list of Figures (with eyepiece).
    """
    # ── Adaptive resolution cap ──────────────────────────────────────
    # Compute the resolution element (smallest feature to resolve)
    fov = source.field_extent_arcsec
    f_ratio = telescope.focal_length / telescope.primary_diameter
    plate_scale = 206265.0 / telescope.focal_length
    airy_radius_arcsec = 1.22 * (wavelength_nm * 1e-6) * f_ratio * plate_scale

    if seeing_arcsec is not None and seeing_arcsec > 0:
        seeing_sigma = seeing_arcsec / 2.355
        resolution_arcsec = max(airy_radius_arcsec, seeing_sigma)
    else:
        resolution_arcsec = airy_radius_arcsec

    # ~3 pixels per resolution element for good sampling
    target_pixel_scale = resolution_arcsec / 3.0
    pixels_for_resolution = int(fov / target_pixel_scale) if target_pixel_scale > 0 else num_pixels

    # ── Star vs extended source ─────────────────────────────────────
    # Star sources (PointSource, DoubleStar, StarField + subclasses) are
    # composed of unresolved points stamped with a PSF kernel. Rendering
    # at higher than display resolution doesn't add information — each
    # display pixel still represents the integrated photons that fell in
    # its angular area. So we cap at the user's requested num_pixels
    # (Approach A: render = display). This is what a real CCD records.
    #
    # Extended sources (Jupiter, Saturn, Moon — anything with
    # render_ideal_rgb) DO benefit from high internal resolution for
    # accurate PSF/seeing convolution against their fine surface
    # texture. They are rendered high-res and then sum-binned to the
    # display resolution before normalisation (Approach B, applied
    # inside _render_source_through_telescope). Sum-binning preserves
    # total flux per display pixel — bilinear interpolation would
    # average and dilute features.
    from telescope_sim.source.sources import (
        PointSource as _PointSrc, StarField as _StarFld,
        DoubleStar as _DblStar,
    )
    _is_star_source = isinstance(source, (_PointSrc, _StarFld, _DblStar))

    # Cap: Moon texture is 2048x1024, so ~2048 useful max; 4096 hard ceiling
    max_cap = 4096
    if hasattr(source, '_load_texture'):
        max_cap = 2048

    if _is_star_source:
        # Approach A: render at display resolution (no high-res for stars)
        effective_pixels = num_pixels
    else:
        # Approach B: render at adaptive high-res, sum-bin to display
        effective_pixels = max(num_pixels, min(pixels_for_resolution, max_cap))

    image, half_fov, info = _render_source_through_telescope(
        source, telescope,
        wavelength_nm=wavelength_nm,
        num_pixels=effective_pixels,
        seeing_arcsec=seeing_arcsec,
        include_obstruction=include_obstruction,
        method=method,
        polychromatic=polychromatic,
        apply_coma=apply_coma,
        apply_vignetting=apply_vignetting,
        display_stretch=display_stretch,
        focus_wavelength_nm=focus_wavelength_nm,
        display_num_pixels=num_pixels,
        exposure_level=exposure_level,
        filter_name=filter_name,
        exit_pupil_mm=exit_pupil_mm,
        apply_aperture_diffraction=apply_aperture_diffraction,
    )
    info["display_stretch"] = display_stretch
    info["focus_wavelength_nm"] = focus_wavelength_nm

    image_rgb = info.get("image_rgb")

    # ── Exit pupil washout (perceptual effect) ──────────────────────
    # Apply only for extended sources with an eyepiece — point sources
    # and star fields have different brightness/perception behavior.
    washout_strength = 0.0
    _is_extended = info["source_type"] not in ("PointSource", "StarField")
    if eyepiece is not None and _is_extended:
        _exit_pupil = eyepiece.exit_pupil_mm(
            telescope.primary_diameter, telescope.focal_length)
        image, image_rgb, washout_strength = _apply_exit_pupil_washout(
            image, image_rgb, _exit_pupil)

    # ── Build title and annotations ──────────────────────────────────
    if title is None:
        source_name = info["source_type"]
        title = (f"Simulated {source_name} \u2014 "
                 f"{telescope.primary_diameter:.0f}mm "
                 f"f/{info['f_ratio']:.1f} "
                 f"{telescope.primary_type.title()}")

    # Resolution annotation reflects the final image (after any
    # detector sum-binning), since that's the per-pixel scale the
    # viewer is actually looking at.
    _display_pixels = image.shape[0]
    ann_lines = [
        f"FOV: {2 * half_fov:.0f}\" \u00d7 {2 * half_fov:.0f}\"",
        f"Airy disk: {info['airy_radius_arcsec']:.2f}\" radius",
        f"\u03bb = {wavelength_nm:.0f} nm",
        f"Resolution: {_display_pixels} \u00d7 {_display_pixels} px",
    ]
    if effective_pixels > _display_pixels:
        ann_lines.append(
            f"  (rendered {effective_pixels}\u00d7{effective_pixels},"
            f" sum-binned \u00d7{effective_pixels // _display_pixels})"
        )
    if info["seeing_arcsec"] is not None:
        ann_lines.append(
            f"Seeing: {info['seeing_arcsec']:.1f}\" FWHM (Gaussian approx.)"
        )
    else:
        ann_lines.append("No atmospheric seeing")
        ann_lines.append(
            "  (concentric rings = Airy diffraction pattern;"
            " atmosphere normally blurs them)"
        )

    if polychromatic and hasattr(telescope, 'objective'):
        ann_lines.append("Polychromatic (R/G/B chromatic PSF)")
    else:
        ann_lines.append("Approx: Monochromatic, no atmospheric dispersion")

    # ── Brightness-model flag (Phase 1.4) ────────────────────────────
    # Make the eye-vs-detector brightness model explicit so the user knows
    # why the exposure slider is (or isn't) doing anything. Flagged as a
    # perceptual approximation in the Eye views.
    if info.get("is_eye_view"):
        ann_lines.append(
            "Display: asinh stretch (boosts dim features; data unchanged)"
        )
        sb = info.get("eye_surface_brightness_factor")
        if sb is not None:
            # Extended source: exit-pupil-driven surface brightness.
            ann_lines.append(
                f"Eye view (perceptual): exposure N/A — surface brightness "
                f"≈ {sb:.2f}× naked-eye"
            )
            ann_lines.append(
                f"  (exit pupil {info.get('exit_pupil_mm', EYE_PUPIL_MM):.1f}"
                f"mm; ∝ (p/{EYE_PUPIL_MM:.0f}mm)², capped)"
            )
        else:
            # Point-like source: aperture-driven.
            ann_lines.append(
                "Eye view (perceptual): exposure N/A — "
                "star brightness ∝ aperture²"
            )
    else:
        ann_lines.append(
            f"Detector view (linear): exposure "
            f"{exposure_level:.2f}× applied"
        )

    # ── Eyepiece calculations ────────────────────────────────────────
    if eyepiece is not None:
        mag = eyepiece.magnification(telescope.focal_length)
        tfov_arcsec = eyepiece.true_fov_arcsec(telescope.focal_length)
        tfov_arcmin = tfov_arcsec / 60.0
        exit_pupil = eyepiece.exit_pupil_mm(
            telescope.primary_diameter, telescope.focal_length)

        ann_lines.extend([
            f"Eyepiece: {eyepiece.focal_length_mm:.0f}mm "
            f"({eyepiece.apparent_fov_deg:.0f}\u00b0 AFOV)",
            f"Magnification: {mag:.0f}\u00d7",
            f"True FOV: {tfov_arcmin:.1f}'",
            f"Exit pupil: {exit_pupil:.1f}mm",
        ])
        if washout_strength > 0.01:
            ann_lines.append(
                f"Washout: {washout_strength:.0%} "
                f"(exit pupil {exit_pupil:.1f}mm "
                f"\u2014 approx. perceptual model)"
            )

    # ── Figure 1: Enhanced view ──────────────────────────────────────
    # For the enhanced (analysis) view: crop if TFOV < source FOV, but
    # keep the source at native scale if TFOV > source FOV so that
    # detail remains visible (the true-size view handles correct scale).
    display_half_fov = half_fov
    display_image = image.copy()
    display_rgb = image_rgb.copy() if image_rgb is not None else None

    if eyepiece is not None:
        tfov_half = tfov_arcsec / 2.0
        if tfov_half < half_fov:
            # TFOV smaller than source — crop to eyepiece field
            display_image, display_rgb, display_half_fov = (
                _crop_or_pad_to_fov(
                    display_image, display_rgb, half_fov, tfov_half))
            # Re-normalize after crop: restores display range to [0, 1]
            # while preserving the *relative* contrast reduction from washout
            if display_image.max() > 0:
                display_image = display_image / display_image.max()
            if display_rgb is not None:
                rgb_max = display_rgb.max()
                if rgb_max > 0:
                    display_rgb = display_rgb / rgb_max
                display_rgb = np.clip(display_rgb, 0.0, 1.0)

    fig, ax = plt.subplots(figsize=figsize)

    _draw_source_on_axes(ax, display_image, display_rgb,
                         display_half_fov, log_scale, colormap, fig)

    ax.set_xlabel("Field angle (arcsec)")
    ax.set_ylabel("Field angle (arcsec)")

    fig_title = title
    if eyepiece is not None:
        fig_title += f" \u2014 {mag:.0f}\u00d7 (enhanced view)"
    ax.set_title(fig_title, fontsize=12)

    ax.text(0.02, 0.98, "\n".join(ann_lines),
            transform=ax.transAxes, fontsize=7,
            verticalalignment="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="black",
                      alpha=0.6),
            color="white")

    # NOTE: Obstruction overlay removed — the secondary obstruction effect
    # is already correctly modeled in the PSF computation. Drawing a black
    # circle on the image plane is physically incorrect.

    # NOTE: AFOV circle/mask removed from enhanced view (Figure 1).
    # The enhanced view is an enlarged view for detail inspection, not at TFOV scale.
    # The true-size view (Figure 2) has the correctly-scaled field stop circle.

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    if eyepiece is None:
        return fig

    # ── Figure 2: True angular size view ─────────────────────────────
    # Scale the image so apparent angular size on screen matches what
    # the eye sees through the eyepiece at a standard viewing distance.
    figures = [fig]

    # Build the true-size image at the TFOV scale
    tfov_image, tfov_rgb, tfov_display_half = _crop_or_pad_to_fov(
        image.copy(),
        image_rgb.copy() if image_rgb is not None else None,
        half_fov, tfov_half)
    # Re-normalize: restores display range while preserving relative
    # contrast reduction from washout
    if tfov_image.max() > 0:
        tfov_image = tfov_image / tfov_image.max()
    if tfov_rgb is not None:
        rgb_max = tfov_rgb.max()
        if rgb_max > 0:
            tfov_rgb = tfov_rgb / rgb_max
        tfov_rgb = np.clip(tfov_rgb, 0.0, 1.0)

    viewing_distance_mm = 500.0  # 50cm standard
    mm_per_degree = viewing_distance_mm * np.tan(np.radians(1.0))
    # ~8.7mm per degree at 50cm

    # Apparent FOV of the eyepiece on screen
    apparent_fov_mm = eyepiece.apparent_fov_deg * mm_per_degree
    apparent_fov_inches = apparent_fov_mm / 25.4

    # Cap figure size to something reasonable (max 20 inches)
    max_fig_inches = 20.0
    scale_note = ""
    if apparent_fov_inches > max_fig_inches:
        scale_factor = max_fig_inches / apparent_fov_inches
        apparent_fov_inches = max_fig_inches
        scale_note = (f"\nNote: Scaled to {scale_factor:.1%} of true size "
                      f"(full size would be {apparent_fov_mm / 25.4:.0f}\")")
    if apparent_fov_inches < 3.0:
        apparent_fov_inches = 3.0
        scale_note = "\nNote: Enlarged for visibility"

    fig2, ax2 = plt.subplots(
        figsize=(apparent_fov_inches, apparent_fov_inches),
        subplot_kw={"aspect": "equal"},
    )
    fig2.patch.set_facecolor("black")
    ax2.set_facecolor("black")

    # Draw the source image at TFOV scale
    _draw_source_on_axes(ax2, tfov_image, tfov_rgb,
                         tfov_display_half, log_scale, colormap, fig2)

    # Draw circular eyepiece field stop
    theta = np.linspace(0, 2 * np.pi, 200)
    ax2.plot(tfov_display_half * np.cos(theta),
             tfov_display_half * np.sin(theta),
             color="gray", linewidth=1.5, alpha=0.6)

    # Clip image to circular field stop
    from matplotlib.patches import Circle
    clip_circle = Circle((0, 0), tfov_display_half,
                         transform=ax2.transData)
    for child in ax2.get_children():
        if hasattr(child, 'set_clip_path'):
            child.set_clip_path(clip_circle)

    ax2.set_xlim(-tfov_display_half * 1.05, tfov_display_half * 1.05)
    ax2.set_ylim(-tfov_display_half * 1.05, tfov_display_half * 1.05)
    ax2.set_xlabel("")
    ax2.set_ylabel("")
    ax2.set_xticks([])
    ax2.set_yticks([])

    ax2.set_title(
        f"True apparent size (at 50cm viewing distance){scale_note}",
        fontsize=10, color="white",
    )

    # Source apparent size through eyepiece
    source_diam_arcsec = source.field_extent_arcsec
    apparent_source_deg = source_diam_arcsec / 3600.0 * mag

    true_ann = [
        f"{eyepiece.focal_length_mm:.0f}mm eyepiece, {mag:.0f}\u00d7",
        f"TFOV: {tfov_arcmin:.1f}' "
        f"({eyepiece.apparent_fov_deg:.0f}\u00b0 apparent)",
        f"Source apparent size: {apparent_source_deg:.1f}\u00b0",
        f"Exit pupil: {exit_pupil:.1f}mm",
        "Assumes 50cm viewing distance, 96 DPI",
    ]
    ax2.text(0.02, 0.98, "\n".join(true_ann),
             transform=ax2.transAxes, fontsize=7,
             verticalalignment="top",
             bbox=dict(boxstyle="round,pad=0.3", facecolor="black",
                       alpha=0.6),
             color="white")

    plt.tight_layout()
    figures.append(fig2)

    # ── Figure 3: Eyepiece View (fixed-size, circular field) ─────────
    # A screen-friendly view at fixed figsize with correct proportions
    # (source size relative to FOV is accurate) but no angular
    # perception matching.
    if eyepiece_view_figsize is not None:
        ev_w, ev_h = eyepiece_view_figsize
        fig3, ax3 = plt.subplots(
            figsize=(ev_w, ev_h),
            subplot_kw={"aspect": "equal"},
        )
        fig3.patch.set_facecolor("black")
        ax3.set_facecolor("black")

        # Draw the source image at TFOV scale
        _draw_source_on_axes(ax3, tfov_image, tfov_rgb,
                             tfov_display_half, log_scale, colormap, fig3)

        # Draw circular eyepiece field stop
        theta_ev = np.linspace(0, 2 * np.pi, 200)
        ax3.plot(tfov_display_half * np.cos(theta_ev),
                 tfov_display_half * np.sin(theta_ev),
                 color="gray", linewidth=1.5, alpha=0.6)

        # Clip image to circular field stop
        from matplotlib.patches import Circle as _Circle
        clip_circle_ev = _Circle((0, 0), tfov_display_half,
                                 transform=ax3.transData)
        for child in ax3.get_children():
            if hasattr(child, 'set_clip_path'):
                child.set_clip_path(clip_circle_ev)

        ax3.set_xlim(-tfov_display_half * 1.05, tfov_display_half * 1.05)
        ax3.set_ylim(-tfov_display_half * 1.05, tfov_display_half * 1.05)
        ax3.set_xlabel("")
        ax3.set_ylabel("")
        ax3.set_xticks([])
        ax3.set_yticks([])

        source_diam_arcsec_ev = source.field_extent_arcsec
        apparent_source_deg_ev = source_diam_arcsec_ev / 3600.0 * mag

        ax3.set_title(
            f"Eyepiece View — {eyepiece.focal_length_mm:.0f}mm "
            f"({mag:.0f}\u00d7, {tfov_arcmin:.1f}' TFOV)",
            fontsize=10, color="white",
        )

        ev_ann = [
            f"TFOV: {tfov_arcmin:.1f}' "
            f"({eyepiece.apparent_fov_deg:.0f}\u00b0 AFOV)",
            f"Source apparent size: {apparent_source_deg_ev:.1f}\u00b0",
            f"Exit pupil: {exit_pupil:.1f}mm",
        ]
        if washout_strength > 0.01:
            ev_ann.append(f"Washout: {washout_strength:.0%}")

        ax3.text(0.02, 0.98, "\n".join(ev_ann),
                 transform=ax3.transAxes, fontsize=7,
                 verticalalignment="top",
                 bbox=dict(boxstyle="round,pad=0.3", facecolor="black",
                           alpha=0.6),
                 color="white")

        plt.tight_layout()
        figures.append(fig3)

    return figures
