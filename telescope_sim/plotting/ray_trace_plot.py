"""2D side-view ray trace visualization and focal plane imaging."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import matplotlib.pyplot as plt

from telescope_sim.physics.ray import Ray
from telescope_sim.physics.diffraction import compute_psf
from telescope_sim.physics.fft_psf import compute_fft_psf
from telescope_sim.physics.aberrations import (
    compute_coma_spot,
    compute_coma_rms,
    coma_free_field,
)

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


def plot_focal_image(telescope: NewtonianTelescope,
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
    telescope: NewtonianTelescope,
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

    ax.set_xlabel("Off-axis angle (arcsec)")
    ax.set_ylabel("Illumination fraction")
    ax.set_title(f"Vignetting — {telescope.primary_diameter:.0f}mm "
                 f"f/{telescope.focal_ratio:.1f}")
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


def plot_vignetting_comparison(
    telescopes: list[NewtonianTelescope],
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
    telescope: NewtonianTelescope,
    wavelength_nm: float = 550.0,
    grid_size: int = 512,
    image_scale: float | None = None,
    figsize: tuple[float, float] = (7, 7),
    colormap: str = "inferno",
    include_obstruction: bool = True,
    save_path: str | None = None,
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
        save_path: If provided, save the figure to this path.

    Returns:
        The matplotlib Figure object.
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

    psf_2d, half_size = compute_fft_psf(
        telescope.primary_diameter, telescope.focal_length,
        wavelength_mm, obs_ratio,
        telescope.spider_vanes, telescope.spider_vane_width,
        grid_size=grid_size,
        oversample=oversample,
    )

    fig, ax = plt.subplots(figsize=figsize)

    # Display on log scale for dynamic range
    psf_display = np.clip(psf_2d, 1e-6, None)
    ax.imshow(np.log10(psf_display),
              extent=[-half_size, half_size, -half_size, half_size],
              origin="lower", cmap=colormap,
              vmin=-4, vmax=0)
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
    ax.set_title(f"2D PSF (log scale) — \u03bb={wavelength_nm:.0f}nm, "
                 f"f/{f_ratio:.1f}{vane_info}")

    info_text = (
        f"Airy radius: {airy_radius * 1000:.2f} \u00b5m\n"
        f"\u03bb = {wavelength_nm:.0f} nm\n"
        f"Spider vanes: {telescope.spider_vanes}\n"
        f"Vane width: {telescope.spider_vane_width:.1f} mm"
    )
    ax.text(0.02, 0.02, info_text,
            transform=ax.transAxes, fontsize=8,
            verticalalignment="bottom", color="white",
            bbox=dict(boxstyle="round", facecolor="black", alpha=0.6))

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_psf_2d_comparison(
    telescopes: list[NewtonianTelescope],
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
    telescope: NewtonianTelescope,
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


def plot_coma_field_analysis(
    telescope: NewtonianTelescope,
    wavelength_nm: float = 550.0,
    max_field_arcsec: float | None = None,
    num_field_points: int = 100,
    spot_angles: list[float] | None = None,
    figsize: tuple[float, float] = (14, 7),
    include_obstruction: bool = True,
    save_path: str | None = None,
) -> plt.Figure:
    """Two-panel coma field analysis.

    Left: RMS coma vs field angle with Airy radius reference line.
    Right: Grid of small spot diagrams at several field angles.

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

    if max_field_arcsec is None:
        max_field_arcsec = max(cff * 5, 120.0)

    angles = np.linspace(0, max_field_arcsec, num_field_points)
    rms_values = np.array([
        compute_coma_rms(a, telescope.focal_length,
                         telescope.primary_diameter, obs_ratio)
        for a in angles
    ])

    if spot_angles is None:
        # Pick ~6 representative angles
        spot_angles = [0, cff * 0.5, cff, cff * 2, cff * 3, cff * 5]
        spot_angles = [a for a in spot_angles
                       if a <= max_field_arcsec and a >= 0]

    fig = plt.figure(figsize=figsize)
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.2], wspace=0.3)

    # Left panel: RMS coma vs field angle
    ax_rms = fig.add_subplot(gs[0])
    ax_rms.plot(angles, rms_values * 1000, "b-", linewidth=2,
                label="RMS coma")
    ax_rms.axhline(airy_radius * 1000, color="red", linestyle="--",
                    alpha=0.7,
                    label=f"Airy radius: {airy_radius * 1000:.2f} \u00b5m")
    if cff > 0 and cff <= max_field_arcsec:
        ax_rms.axvline(cff, color="green", linestyle="--", alpha=0.7,
                        label=f"Coma-free field: {cff:.1f}\"")

    ax_rms.set_xlabel("Off-axis angle (arcsec)")
    ax_rms.set_ylabel("RMS coma (\u00b5m)")
    ax_rms.set_title("RMS Coma vs Field Angle")
    ax_rms.legend(fontsize=8)
    ax_rms.grid(True, alpha=0.3)

    ax_rms.text(0.02, 0.98,
                "Approx: Seidel 3rd-order",
                transform=ax_rms.transAxes, fontsize=7,
                verticalalignment="top", color="orange", alpha=0.8)

    # Right panel: spot diagram grid
    n_spots = len(spot_angles)
    cols = min(n_spots, 3)
    rows = (n_spots + cols - 1) // cols
    gs_right = gs[1].subgridspec(rows, cols, wspace=0.3, hspace=0.4)

    for idx, angle in enumerate(spot_angles):
        r = idx // cols
        c = idx % cols
        ax_spot = fig.add_subplot(gs_right[r, c])

        x_off, y_off = compute_coma_spot(
            angle, telescope.focal_length,
            telescope.primary_diameter, obs_ratio,
            num_pupil_zones=30, num_azimuthal=36,
        )

        if np.max(np.abs(x_off)) < 1e-10 and np.max(np.abs(y_off)) < 1e-10:
            # On-axis: just show the Airy circle
            lim = airy_radius * 3
            ax_spot.set_xlim(-lim * 1000, lim * 1000)
            ax_spot.set_ylim(-lim * 1000, lim * 1000)
        else:
            ax_spot.scatter(x_off * 1000, y_off * 1000, s=1, c="gold",
                            alpha=0.5)
            max_ext = max(np.max(np.abs(x_off)), np.max(np.abs(y_off)),
                          airy_radius) * 1.5
            ax_spot.set_xlim(-max_ext * 1000, max_ext * 1000)
            ax_spot.set_ylim(-max_ext * 1000, max_ext * 1000)

        airy_c = plt.Circle((0, 0), airy_radius * 1000, fill=False,
                              color="cyan", linestyle="--",
                              linewidth=0.8, alpha=0.8)
        ax_spot.add_patch(airy_c)
        ax_spot.set_aspect("equal")
        ax_spot.set_title(f"{angle:.0f}\"", fontsize=9)
        ax_spot.tick_params(labelsize=6)
        if r == rows - 1:
            ax_spot.set_xlabel("\u00b5m", fontsize=7)

    fig.suptitle(f"Coma Field Analysis — {telescope.primary_diameter:.0f}mm "
                 f"f/{f_ratio:.1f}", fontsize=13)

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


# ── Source imaging ──────────────────────────────────────────────────────


def _compute_psf_at_field_angle(telescope: NewtonianTelescope,
                                field_angle_arcsec: float,
                                wavelength_nm: float,
                                num_pixels: int,
                                half_size_mm: float,
                                include_obstruction: bool = True,
                                ) -> np.ndarray:
    """Compute the PSF at a given field angle, including coma.

    For on-axis (field_angle_arcsec ~ 0), returns the diffraction PSF.
    For off-axis, convolves the coma spot pattern with the Airy kernel.

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
        # On-axis: pure diffraction PSF
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
            return _resample_fft_psf(fft_psf, fft_half, half_size_mm,
                                     num_pixels)
        else:
            coords = np.linspace(-half_size_mm, half_size_mm, num_pixels)
            xx, yy = np.meshgrid(coords, coords)
            rr = np.sqrt(xx ** 2 + yy ** 2)
            psf = compute_psf(rr, telescope.primary_diameter,
                              telescope.focal_length, wavelength_mm,
                              obs_ratio)
            return psf
    else:
        # Off-axis: compute coma spot and convolve with Airy kernel
        x_off, y_off = compute_coma_spot(
            field_angle_arcsec, telescope.focal_length,
            telescope.primary_diameter, obs_ratio,
            num_pupil_zones=50, num_azimuthal=72,
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

        psf = fftconvolve(coma_image, kernel, mode="same")
        if psf.max() > 0:
            psf /= psf.max()
        return psf


def _render_source_through_telescope(
        source, telescope: NewtonianTelescope,
        wavelength_nm: float = 550.0,
        num_pixels: int = 512,
        seeing_arcsec: float | None = None,
        include_obstruction: bool = True,
        method: str = "analytical",
) -> tuple[np.ndarray, float, dict]:
    """Render an astronomical source as seen through the telescope.

    Pipeline:
    1. Determine field of view from source extent
    2. Build ideal source image
    3. Convolve with PSF (field-dependent for point sources, on-axis for
       extended objects like Jupiter)
    4. Apply vignetting
    5. Optional atmospheric seeing blur

    Args:
        source: An AstronomicalSource instance.
        telescope: The telescope to image through.
        wavelength_nm: Wavelength of light in nm.
        num_pixels: Image resolution.
        seeing_arcsec: Atmospheric seeing FWHM (None = no atmosphere).
        include_obstruction: Include secondary obstruction in PSF.
        method: PSF method ("analytical" or "traced").

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

        # Determine brightest star for intensity normalization
        min_mag = min(s[2] for s in stars)

        for field_r, pa_deg, mag in stars:
            # Star intensity relative to brightest
            intensity = 10.0 ** (-0.4 * (mag - min_mag))

            # Vignetting at this field angle
            vignetting = telescope.compute_vignetting(field_r)

            # Compute PSF at this field angle
            psf = _compute_psf_at_field_angle(
                telescope, field_r, wavelength_nm, psf_n,
                psf_half_mm, include_obstruction,
            )

            # Star position in the image (pixel coords)
            pa_rad = np.radians(pa_deg)
            star_x_arcsec = field_r * np.cos(pa_rad)
            star_y_arcsec = field_r * np.sin(pa_rad)
            cx = int(round(num_pixels / 2
                           + star_x_arcsec / pixel_scale_arcsec))
            cy = int(round(num_pixels / 2
                           + star_y_arcsec / pixel_scale_arcsec))

            # Place PSF into image at star position
            psf_half_pix = psf_n // 2
            for py in range(psf_n):
                for px in range(psf_n):
                    img_y = cy + py - psf_half_pix
                    img_x = cx + px - psf_half_pix
                    if (0 <= img_x < num_pixels
                            and 0 <= img_y < num_pixels):
                        image[img_y, img_x] += (
                            psf[py, px] * intensity * vignetting
                        )

    elif hasattr(source, 'render_ideal_rgb'):
        # Extended source with RGB colors (Jupiter, Saturn, Moon, etc.)
        # Convolve ideal image with on-axis PSF. For objects small enough
        # that PSF variation across the disk is negligible, a single
        # on-axis PSF kernel is used.
        ideal = source.render_ideal(half_fov_arcsec, num_pixels)
        ideal_rgb = source.render_ideal_rgb(half_fov_arcsec, num_pixels)

        # Build on-axis PSF kernel on the same angular pixel scale,
        # then convolve in image space.
        psf_angular_half = airy_radius_arcsec * 8
        # Convert to same pixel scale as the image
        pixel_scale_arcsec = 2.0 * half_fov_arcsec / num_pixels
        psf_n_img = max(16, int(2 * psf_angular_half / pixel_scale_arcsec))
        psf_n_img = min(psf_n_img, num_pixels)
        if psf_n_img % 2 == 0:
            psf_n_img += 1  # odd for symmetric kernel

        psf_half_for_kernel = psf_angular_half / plate_scale
        psf = _compute_psf_at_field_angle(
            telescope, 0.0, wavelength_nm, psf_n_img,
            psf_half_for_kernel, include_obstruction,
        )
        psf_kernel = psf / psf.sum()

        # Apply vignetting (uniform across small Jupiter disk)
        vignetting = telescope.compute_vignetting(0.0)
        image = fftconvolve(ideal, psf_kernel, mode="same") * vignetting

        # Convolve each RGB channel with the PSF for color rendering
        image_rgb = np.zeros_like(ideal_rgb)
        for c in range(3):
            image_rgb[..., c] = (fftconvolve(ideal_rgb[..., c], psf_kernel,
                                             mode="same") * vignetting)

    else:
        # Generic fallback: convolve ideal with on-axis PSF
        ideal = source.render_ideal(half_fov_arcsec, num_pixels)
        psf = _compute_psf_at_field_angle(
            telescope, 0.0, wavelength_nm, psf_n,
            psf_half_mm, include_obstruction,
        )
        psf_kernel = psf / psf.sum()
        image = fftconvolve(ideal, psf_kernel, mode="same")

    # Optional atmospheric seeing
    if seeing_arcsec is not None and seeing_arcsec > 0:
        pixel_scale_arcsec = 2.0 * half_fov_arcsec / num_pixels
        seeing_sigma_pix = (seeing_arcsec / 2.355) / pixel_scale_arcsec
        coords = np.arange(num_pixels) - num_pixels / 2
        sxx, syy = np.meshgrid(coords, coords)
        seeing_kernel = np.exp(-(sxx ** 2 + syy ** 2)
                               / (2 * seeing_sigma_pix ** 2))
        seeing_kernel /= seeing_kernel.sum()
        image = fftconvolve(image, seeing_kernel, mode="same")
        if image_rgb is not None:
            for c in range(3):
                image_rgb[..., c] = fftconvolve(image_rgb[..., c],
                                                seeing_kernel, mode="same")

    # Normalize
    if image.max() > 0:
        image /= image.max()
    if image_rgb is not None:
        rgb_max = image_rgb.max()
        if rgb_max > 0:
            image_rgb /= rgb_max
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


def plot_source_image(telescope: NewtonianTelescope,
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
                      ) -> plt.Figure | list[plt.Figure]:
    """Plot a simulated image of an astronomical source through the telescope.

    Args:
        telescope: The telescope to image through.
        source: An AstronomicalSource instance (PointSource, StarField,
            Jupiter, Saturn, Moon, etc.).
        wavelength_nm: Wavelength of light in nm.
        num_pixels: Image resolution (pixels per side).
        seeing_arcsec: Atmospheric seeing FWHM (None = no atmosphere).
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

    # Cap: Moon texture is 2048x1024, so ~2048 useful max; 4096 hard ceiling
    max_cap = 4096
    if hasattr(source, '_load_texture'):
        max_cap = 2048

    effective_pixels = max(num_pixels, min(pixels_for_resolution, max_cap))

    image, half_fov, info = _render_source_through_telescope(
        source, telescope,
        wavelength_nm=wavelength_nm,
        num_pixels=effective_pixels,
        seeing_arcsec=seeing_arcsec,
        include_obstruction=include_obstruction,
        method=method,
    )

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

    ann_lines = [
        f"FOV: {2 * half_fov:.0f}\" \u00d7 {2 * half_fov:.0f}\"",
        f"Airy disk: {info['airy_radius_arcsec']:.2f}\" radius",
        f"\u03bb = {wavelength_nm:.0f} nm",
        f"Resolution: {effective_pixels} \u00d7 {effective_pixels} px",
    ]
    if info["seeing_arcsec"] is not None:
        ann_lines.append(
            f"Seeing: {info['seeing_arcsec']:.1f}\" FWHM (Gaussian approx.)"
        )
    else:
        ann_lines.append("No atmospheric seeing")

    ann_lines.append("Approx: Monochromatic, no atmospheric dispersion")

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
    return figures
