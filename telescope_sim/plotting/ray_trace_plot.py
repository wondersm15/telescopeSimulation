"""2D side-view ray trace visualization and focal plane imaging."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import matplotlib.pyplot as plt

from telescope_sim.physics.ray import Ray
from telescope_sim.physics.diffraction import compute_psf

if TYPE_CHECKING:
    from telescope_sim.geometry.telescope import NewtonianTelescope


def _draw_ray_trace(ax: plt.Axes, rays: list[Ray], components: dict,
                    title: str = "Newtonian Telescope Ray Trace",
                    ray_color: str = "gold",
                    ray_alpha: float = 0.7,
                    mirror_color: str = "steelblue",
                    mirror_linewidth: float = 3.0,
                    show_tube: bool = True) -> None:
    """Draw a ray trace diagram on the given axes.

    This is the core drawing helper used by both plot_ray_trace and
    the comparison functions.
    """
    if show_tube:
        _draw_tube(ax, components)

    primary_pts = components["primary_surface"]
    ax.plot(primary_pts[:, 0], primary_pts[:, 1],
            color=mirror_color, linewidth=mirror_linewidth,
            solid_capstyle="round", label="Primary mirror")

    secondary_pts = components["secondary_surface"]
    ax.plot(secondary_pts[:, 0], secondary_pts[:, 1],
            color="firebrick", linewidth=mirror_linewidth,
            solid_capstyle="round", label="Secondary mirror")

    for ray in rays:
        if len(ray.history) < 2:
            continue
        path = np.array(ray.history)
        ax.plot(path[:, 0], path[:, 1],
                color=ray_color, alpha=ray_alpha, linewidth=1.0)

    end_points = [ray.history[-1] for ray in rays if len(ray.history) >= 3]
    if end_points:
        focal_area = np.mean(end_points, axis=0)
        ax.plot(focal_area[0], focal_area[1], "r*", markersize=12,
                label="Focal point", zorder=5)

    ax.set_aspect("equal")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_title(title)
    ax.legend(loc="upper right")
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

    Extracts the final segment of each ray (post-secondary), scans
    for the x-position where ray spread is minimized, and returns
    the y-offsets (centered on zero) at that plane.

    Args:
        rays: List of fully traced Ray objects.

    Returns:
        Array of y-offsets at the focal plane, centered on zero.
        Returns None if no valid rays are found.
    """
    traced_rays = [r for r in rays if len(r.history) >= 4]
    if not traced_rays:
        return None

    segments = []
    for ray in traced_rays:
        p_start = np.array(ray.history[-2])
        p_end = np.array(ray.history[-1])
        segments.append((p_start, p_end))

    # Scan x-positions to find best focus
    x_min = min(s[0][0] for s in segments)
    x_max = max(s[1][0] for s in segments)
    test_x_positions = np.linspace(x_min, x_max, 200)

    best_x = x_min
    best_spread = float("inf")

    for test_x in test_x_positions:
        y_crossings = []
        for p_start, p_end in segments:
            dx = p_end[0] - p_start[0]
            if abs(dx) < 1e-12:
                continue
            t = (test_x - p_start[0]) / dx
            if 0 <= t <= 1.5:
                y_at_x = p_start[1] + t * (p_end[1] - p_start[1])
                y_crossings.append(y_at_x)
        if len(y_crossings) >= 2:
            spread = np.std(y_crossings)
            if spread < best_spread:
                best_spread = spread
                best_x = test_x

    # Compute ray positions at the best focal plane
    y_positions = []
    for p_start, p_end in segments:
        dx = p_end[0] - p_start[0]
        if abs(dx) < 1e-12:
            continue
        t = (best_x - p_start[0]) / dx
        y_at_x = p_start[1] + t * (p_end[1] - p_start[1])
        y_positions.append(y_at_x)

    y_positions = np.array(y_positions)
    y_center = np.mean(y_positions)
    return y_positions - y_center


def _trace_dense_rays(telescope: NewtonianTelescope,
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


def _analytical_focal_offsets(telescope: NewtonianTelescope,
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

    if telescope.primary_type == "parabolic":
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


def _get_focal_offsets(telescope: NewtonianTelescope,
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
                       show_max: bool = True) -> None:
    """Draw a spot diagram on the given axes.

    This is the core drawing helper used by both plot_spot_diagram and
    the comparison functions.
    """
    if y_offsets is None:
        ax.set_title(title)
        ax.text(0.5, 0.5, "No fully traced rays", ha="center",
                va="center", transform=ax.transAxes)
        return

    rms_spot = np.std(y_offsets)
    max_spot = np.max(np.abs(y_offsets))

    ax.scatter(y_offsets, np.zeros_like(y_offsets), c="gold",
               edgecolors="darkorange", s=80, zorder=3, label="Ray positions")

    margin = max(max_spot * 3, 0.5)
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
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)

    ax.text(0.02, 0.02,
            f"RMS spot size: {rms_spot:.4f} mm\n"
            f"Max spread: {max_spot * 2:.4f} mm",
            transform=ax.transAxes, fontsize=10,
            verticalalignment="bottom",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8))


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
    fig, ax = plt.subplots(figsize=figsize)
    _draw_spot_diagram(ax, y_offsets, title=title,
                       show_rms=show_rms, show_max=show_max)
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


def _compute_focal_image(telescope: NewtonianTelescope,
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

    if is_perfect_focus:
        coords = np.linspace(-half_size, half_size, num_pixels)
        xx, yy = np.meshgrid(coords, coords)
        rr = np.sqrt(xx ** 2 + yy ** 2)
        image = compute_psf(rr, aperture_diameter, focal_length,
                            wavelength_mm, obs_ratio)
    else:
        geometric_image = _build_geometric_spot_2d(y_offsets, half_size,
                                                   num_pixels)
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


def _draw_focal_image(ax: plt.Axes, telescope: NewtonianTelescope,
                      title: str = "Simulated Focal Plane Image",
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


def plot_focal_image(telescope: NewtonianTelescope,
                     title: str = "Simulated Focal Plane Image",
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


def plot_psf_profile(telescope: NewtonianTelescope,
                     title: str = "Point Spread Function",
                     figsize: tuple[float, float] = (14, 7),
                     wavelength_nm: float = 550.0,
                     method: str = "analytical",
                     num_trace_rays: int = 501,
                     save_path: str | None = None,
                     include_obstruction: bool = True) -> plt.Figure:
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

    # --- Layout: two plot panels + formula/metrics panel ---
    fig = plt.figure(figsize=figsize)
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 0.8], wspace=0.35)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])
    ax3 = fig.add_subplot(gs[2])

    # Linear scale
    if is_perfect_focus:
        # Only one meaningful curve — the Airy IS the combined PSF
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
                alpha=0.6, label=f"Airy radius: {airy_radius * 1000:.2f} \u00b5m")
    ax1.set_xlabel("Radial distance (\u00b5m)")
    ax1.set_ylabel("Normalized intensity")
    ax1.set_title("Linear scale")
    ax1.legend(fontsize=7)
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(-0.05, 1.05)

    # Log scale
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

    # --- Formula & metrics panel ---
    ax3.axis("off")

    method_label = ("Analytical" if method == "analytical"
                    else f"Traced ({num_trace_rays} rays)")
    rayleigh_arcsec = (1.22 * wavelength_nm * 1e-9
                       / (aperture_diameter * 1e-3) * 206265)
    strehl = _estimate_strehl(rms_spot, airy_radius)

    # Metrics block
    if include_obstruction:
        obs_line = f"\u03b5 = {obs_ratio:.2f} ({obs_ratio:.0%} obstruction)"
    else:
        obs_line = "Obstruction: disabled"
    metrics_text = (
        f"D = {aperture_diameter:.0f} mm,  f/{f_ratio:.1f}\n"
        f"\u03bb = {wavelength_nm:.0f} nm\n"
        f"{obs_line}\n"
        f"Airy radius: {airy_radius * 1000:.2f} \u00b5m\n"
        f"Rayleigh limit: {rayleigh_arcsec:.2f}\"\n"
        f"RMS geo spot: {rms_spot * 1000:.2f} \u00b5m\n"
        f"Strehl \u2248 {strehl:.3f}\n"
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
    telescopes: list[NewtonianTelescope],
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

    fig.suptitle("Ray Trace Comparison", fontsize=14)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


def plot_spot_diagram_comparison(
    telescopes: list[NewtonianTelescope],
    labels: list[str],
    num_display_rays: int = 11,
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
        rays = create_parallel_rays(
            num_rays=num_display_rays,
            aperture_diameter=telescope.primary_diameter,
            entry_height=telescope.tube_length * 1.15,
        )
        telescope.trace_rays(rays)
        y_offsets = _find_focal_plane_positions(rays)
        _draw_spot_diagram(ax, y_offsets, title=label)

    fig.suptitle("Spot Diagram Comparison", fontsize=14)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


def plot_focal_image_comparison(
    telescopes: list[NewtonianTelescope],
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
    telescopes: list[NewtonianTelescope],
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
