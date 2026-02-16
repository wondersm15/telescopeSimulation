"""2D side-view ray trace visualization and focal plane imaging."""

import numpy as np
import matplotlib.pyplot as plt
from scipy.special import j1

from telescope_sim.physics.ray import Ray


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

    # Draw telescope tube
    if show_tube:
        _draw_tube(ax, components)

    # Draw primary mirror
    primary_pts = components["primary_surface"]
    ax.plot(primary_pts[:, 0], primary_pts[:, 1],
            color=mirror_color, linewidth=mirror_linewidth,
            solid_capstyle="round", label="Primary mirror")

    # Draw secondary mirror
    secondary_pts = components["secondary_surface"]
    ax.plot(secondary_pts[:, 0], secondary_pts[:, 1],
            color="firebrick", linewidth=mirror_linewidth,
            solid_capstyle="round", label="Secondary mirror")

    # Draw rays
    for ray in rays:
        if len(ray.history) < 2:
            continue
        path = np.array(ray.history)
        ax.plot(path[:, 0], path[:, 1],
                color=ray_color, alpha=ray_alpha, linewidth=1.0)

    # Mark focal area (average end-point of fully traced rays)
    end_points = [ray.history[-1] for ray in rays if len(ray.history) >= 3]
    if end_points:
        focal_area = np.mean(end_points, axis=0)
        ax.plot(focal_area[0], focal_area[1], "r*", markersize=12,
                label="Focal point", zorder=5)

    # Formatting
    ax.set_aspect("equal")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_title(title)
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)

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
    if y_offsets is None:
        fig, ax = plt.subplots(figsize=figsize)
        ax.set_title(title)
        ax.text(0.5, 0.5, "No fully traced rays", ha="center",
                va="center", transform=ax.transAxes)
        return fig

    # Spot size metrics
    rms_spot = np.std(y_offsets)
    max_spot = np.max(np.abs(y_offsets))

    # Plot
    fig, ax = plt.subplots(figsize=figsize)

    # Plot ray crossing points
    ax.scatter(y_offsets, np.zeros_like(y_offsets), c="gold",
               edgecolors="darkorange", s=80, zorder=3, label="Ray positions")

    # Draw the focal plane line
    margin = max(max_spot * 3, 0.5)
    ax.axhline(0, color="gray", linewidth=0.5, alpha=0.5)
    ax.axvline(0, color="gray", linewidth=0.5, alpha=0.5)

    # Draw spot size circles
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

    # Add spot size text
    ax.text(0.02, 0.02,
            f"RMS spot size: {rms_spot:.4f} mm\n"
            f"Max spread: {max_spot * 2:.4f} mm",
            transform=ax.transAxes, fontsize=10,
            verticalalignment="bottom",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8))

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


def _airy_psf(r: np.ndarray, aperture_diameter: float,
              focal_length: float,
              wavelength_mm: float) -> np.ndarray:
    """Compute the Airy diffraction pattern intensity.

    This is the physically correct point spread function for a
    circular aperture telescope:

        PSF(r) = [2 * J1(x) / x]^2

    where x = pi * D * r / (lambda * f), J1 is the Bessel function
    of the first kind (order 1), D is the aperture diameter, f is
    the focal length, and lambda is the wavelength.

    NOTE: This assumes an unobstructed circular aperture. Real
    Newtonian telescopes have a central obstruction from the
    secondary mirror, which modifies the PSF (not yet implemented,
    see PHYSICS.md).

    Args:
        r: Array of radial distances from center in mm.
        aperture_diameter: Telescope aperture diameter in mm.
        focal_length: Telescope focal length in mm.
        wavelength_mm: Wavelength of light in mm.

    Returns:
        Normalized intensity array (peak = 1.0).
    """
    x = np.pi * aperture_diameter * r / (wavelength_mm * focal_length)
    # Handle x=0 (center of pattern) to avoid division by zero
    psf = np.ones_like(x)
    nonzero = x != 0
    psf[nonzero] = (2.0 * j1(x[nonzero]) / x[nonzero]) ** 2
    return psf


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


def plot_focal_image(rays: list[Ray],
                     aperture_diameter: float,
                     focal_length: float,
                     title: str = "Simulated Focal Plane Image",
                     figsize: tuple[float, float] = (7, 7),
                     wavelength_nm: float = 550.0,
                     image_size_mm: float | None = None,
                     num_pixels: int = 512,
                     seeing_arcsec: float | None = None,
                     colormap: str = "hot",
                     save_path: str | None = None) -> plt.Figure:
    """Render a physically-based simulated image at the focal plane.

    Combines two effects:
    1. Geometric spot — where rays actually land (from ray tracing),
       reconstructed as a rotationally symmetric 2D pattern
    2. Diffraction PSF — Airy pattern from the circular aperture

    Each ray's focal plane position is convolved with the Airy PSF
    to produce the final image. This correctly captures both geometric
    aberrations (e.g., spherical aberration) and the diffraction limit.

    Optionally adds atmospheric seeing as a Gaussian blur.

    Physics notes (see PHYSICS.md for full inventory):
    - Airy pattern assumes unobstructed circular aperture
    - Monochromatic light at the specified wavelength
    - No detector noise or pixel sampling effects
    - 2D spot reconstructed from 1D cross-section (assumes rotational symmetry)

    Args:
        rays: List of fully traced Ray objects.
        aperture_diameter: Telescope aperture diameter in mm.
        focal_length: Telescope focal length in mm.
        title: Plot title.
        figsize: Figure size in inches.
        wavelength_nm: Wavelength of light in nanometers (default 550nm green).
        image_size_mm: Width/height of the image in mm.
                       If None, auto-scales to show the full PSF.
        num_pixels: Resolution of the image grid.
        seeing_arcsec: Atmospheric seeing FWHM in arcseconds.
                       If None, no atmospheric blur is applied.
        colormap: Matplotlib colormap name.
        save_path: If provided, save the figure to this path.

    Returns:
        The matplotlib Figure object.
    """
    from scipy.signal import fftconvolve

    y_offsets = _find_focal_plane_positions(rays)
    if y_offsets is None:
        fig, ax = plt.subplots(figsize=figsize)
        ax.set_title(title)
        ax.text(0.5, 0.5, "No fully traced rays", ha="center",
                va="center", transform=ax.transAxes)
        return fig

    wavelength_mm = wavelength_nm * 1e-6  # Convert nm to mm
    f_ratio = focal_length / aperture_diameter

    # Airy disk radius: first zero at r = 1.22 * lambda * f/D
    airy_radius = 1.22 * wavelength_mm * f_ratio
    rms_spot = np.std(y_offsets)
    max_spot = np.max(np.abs(y_offsets))

    # Auto-determine image extent to show the full structure
    if image_size_mm is None:
        image_size_mm = max(airy_radius * 10, max_spot * 6, 0.001)

    half_size = image_size_mm / 2.0

    # Step 1: Build rotationally symmetric geometric spot
    geometric_image = _build_geometric_spot_2d(y_offsets, half_size,
                                               num_pixels)

    # Step 2: Build Airy PSF kernel
    pixel_size = image_size_mm / num_pixels
    kernel_half_size = max(airy_radius * 5, pixel_size * 3)
    kernel_n = min(num_pixels, 256)
    kernel_coords = np.linspace(-kernel_half_size, kernel_half_size, kernel_n)
    kxx, kyy = np.meshgrid(kernel_coords, kernel_coords)
    kr = np.sqrt(kxx ** 2 + kyy ** 2)
    airy_kernel = _airy_psf(kr, aperture_diameter, focal_length,
                            wavelength_mm)
    airy_kernel = airy_kernel / airy_kernel.sum()

    # Step 3: Convolve geometric spot with Airy PSF
    image = fftconvolve(geometric_image, airy_kernel, mode="same")

    # Step 4: Optionally apply atmospheric seeing
    if seeing_arcsec is not None and seeing_arcsec > 0:
        plate_scale = 206265.0 / focal_length
        seeing_sigma_mm = (seeing_arcsec / 2.355) / plate_scale
        coords = np.linspace(-half_size, half_size, num_pixels)
        sxx, syy = np.meshgrid(coords, coords)
        seeing_kernel = np.exp(-(sxx ** 2 + syy ** 2) /
                               (2 * seeing_sigma_mm ** 2))
        seeing_kernel = seeing_kernel / seeing_kernel.sum()
        image = fftconvolve(image, seeing_kernel, mode="same")

    # Normalize to [0, 1]
    if image.max() > 0:
        image = image / image.max()

    # Plot
    fig, ax = plt.subplots(figsize=figsize)

    ax.imshow(image, extent=[-half_size, half_size, -half_size, half_size],
              origin="lower", cmap=colormap, vmin=0, vmax=1)

    ax.set_xlabel("Position (mm)")
    ax.set_ylabel("Position (mm)")
    ax.set_title(title)

    # Build info text with physics details
    info_lines = [
        f"Airy disk radius: {airy_radius * 1000:.2f} \u00b5m",
        f"RMS geometric spot: {rms_spot * 1000:.2f} \u00b5m",
        f"\u03bb = {wavelength_nm:.0f} nm | f/{f_ratio:.1f}",
        f"Rays: {len(y_offsets)}",
    ]

    approx_lines = []
    if seeing_arcsec is None:
        approx_lines.append("No atmospheric seeing")
    else:
        info_lines.append(f"Seeing: {seeing_arcsec:.1f}\"")
    approx_lines.append("Unobstructed aperture")
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

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    return fig


def plot_psf_profile(rays: list[Ray],
                     aperture_diameter: float,
                     focal_length: float,
                     title: str = "Point Spread Function",
                     figsize: tuple[float, float] = (10, 6),
                     wavelength_nm: float = 550.0,
                     save_path: str | None = None) -> plt.Figure:
    """Plot the radial PSF profile showing diffraction and aberration effects.

    Shows three curves:
    1. Ideal Airy PSF — diffraction-limited (perfect optics)
    2. Geometric spot profile — from ray tracing only (no diffraction)
    3. Combined PSF — the actual telescope performance

    Also shows the Rayleigh resolution limit and key metrics.

    Args:
        rays: List of fully traced Ray objects.
        aperture_diameter: Telescope aperture diameter in mm.
        focal_length: Telescope focal length in mm.
        title: Plot title.
        figsize: Figure size in inches.
        wavelength_nm: Wavelength of light in nanometers.
        save_path: If provided, save the figure to this path.

    Returns:
        The matplotlib Figure object.
    """
    from scipy.signal import fftconvolve

    y_offsets = _find_focal_plane_positions(rays)
    if y_offsets is None:
        fig, ax = plt.subplots(figsize=figsize)
        ax.set_title(title)
        ax.text(0.5, 0.5, "No fully traced rays", ha="center",
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

    # 1. Ideal Airy PSF (diffraction only)
    airy_profile = _airy_psf(r, aperture_diameter, focal_length,
                             wavelength_mm)

    # 2. Geometric spot profile (ray tracing only)
    # Build a histogram of radial ray positions
    radial_offsets = np.abs(y_offsets)
    bin_width = r_max / 200
    geo_profile = np.zeros_like(r)
    for r_off in radial_offsets:
        geo_profile += np.exp(-(r - r_off) ** 2 / (2 * bin_width ** 2))
    if geo_profile.max() > 0:
        geo_profile = geo_profile / geo_profile.max()

    # 3. Combined PSF (convolve geometric with Airy in 1D radial approx)
    # Build 2D images, convolve, then extract radial profile
    n_px = 256
    half = r_max
    coords_1d = np.linspace(-half, half, n_px)
    cxx, cyy = np.meshgrid(coords_1d, coords_1d)
    crr = np.sqrt(cxx ** 2 + cyy ** 2)

    geo_2d = _build_geometric_spot_2d(y_offsets, half, n_px)
    airy_2d = _airy_psf(crr, aperture_diameter, focal_length, wavelength_mm)
    airy_2d = airy_2d / airy_2d.sum()
    combined_2d = fftconvolve(geo_2d, airy_2d, mode="same")

    # Extract radial profile from center of combined image
    center = n_px // 2
    pixel_size = (2 * half) / n_px
    combined_radial = combined_2d[center, center:]
    combined_r = np.arange(len(combined_radial)) * pixel_size
    if combined_radial.max() > 0:
        combined_radial = combined_radial / combined_radial.max()

    # Plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)

    # Linear scale
    ax1.plot(r * 1000, airy_profile, "b-", linewidth=1.5,
             label="Ideal Airy (diffraction only)")
    ax1.plot(r * 1000, geo_profile, "r--", linewidth=1.5,
             label="Geometric spot (no diffraction)")
    ax1.plot(combined_r * 1000, combined_radial, "k-", linewidth=2,
             label="Combined PSF")
    ax1.axvline(airy_radius * 1000, color="blue", linestyle=":",
                alpha=0.5, label=f"Airy radius: {airy_radius * 1000:.2f} \u00b5m")
    ax1.set_xlabel("Radial distance (\u00b5m)")
    ax1.set_ylabel("Normalized intensity")
    ax1.set_title("Linear scale")
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)

    # Log scale
    ax2.semilogy(r * 1000, np.clip(airy_profile, 1e-6, None), "b-",
                 linewidth=1.5, label="Ideal Airy")
    ax2.semilogy(r * 1000, np.clip(geo_profile, 1e-6, None), "r--",
                 linewidth=1.5, label="Geometric spot")
    ax2.semilogy(combined_r * 1000, np.clip(combined_radial, 1e-6, None),
                 "k-", linewidth=2, label="Combined PSF")
    ax2.axvline(airy_radius * 1000, color="blue", linestyle=":",
                alpha=0.5)
    ax2.set_xlabel("Radial distance (\u00b5m)")
    ax2.set_ylabel("Normalized intensity (log)")
    ax2.set_title("Log scale")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(1e-4, 1.5)

    fig.suptitle(title, fontsize=13)

    # Add metrics text
    rayleigh_arcsec = 1.22 * wavelength_nm * 1e-9 / (aperture_diameter * 1e-3)
    rayleigh_arcsec *= 206265  # radians to arcsec
    metrics = (
        f"\u03bb = {wavelength_nm:.0f} nm | "
        f"f/{f_ratio:.1f} | "
        f"D = {aperture_diameter:.0f} mm\n"
        f"Airy radius: {airy_radius * 1000:.2f} \u00b5m | "
        f"Rayleigh limit: {rayleigh_arcsec:.2f}\"\n"
        f"RMS geometric spot: {rms_spot * 1000:.2f} \u00b5m | "
        f"Strehl approx: {_estimate_strehl(rms_spot, airy_radius):.3f}"
    )
    fig.text(0.5, -0.02, metrics, ha="center", fontsize=9,
             bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.9))

    plt.tight_layout()

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
