"""2D side-view ray trace visualization and focal plane imaging."""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

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


def plot_focal_image(rays: list[Ray],
                     title: str = "Simulated Focal Plane Image",
                     figsize: tuple[float, float] = (7, 7),
                     image_size_mm: float | None = None,
                     num_pixels: int = 256,
                     blur_sigma_mm: float | None = None,
                     colormap: str = "hot",
                     save_path: str | None = None) -> plt.Figure:
    """Render a simulated image at the focal plane.

    Each ray's crossing point on the focal plane contributes a
    Gaussian blob of intensity. The result looks like what you'd
    see through the eyepiece:
    - Point source: a blurred dot (tighter = better optics)
    - Uniform source: even illumination

    This same approach will work for extended sources (e.g., Jupiter)
    once source rays carry angular/positional information.

    Args:
        rays: List of fully traced Ray objects.
        title: Plot title.
        figsize: Figure size in inches.
        image_size_mm: Width/height of the image region in mm.
                       If None, auto-scales based on the ray spread.
        num_pixels: Resolution of the image grid.
        blur_sigma_mm: Gaussian blur radius in mm for each ray.
                       If None, auto-scales to ~3x the RMS spot size
                       (or a minimum for very tight spots).
        colormap: Matplotlib colormap name.
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

    rms_spot = np.std(y_offsets)

    # Auto-determine blur size if not specified
    if blur_sigma_mm is None:
        blur_sigma_mm = max(rms_spot * 3.0, 0.005)

    # Auto-determine image extent
    if image_size_mm is None:
        extent = max(np.max(np.abs(y_offsets)) * 8, blur_sigma_mm * 10)
        image_size_mm = extent

    half_size = image_size_mm / 2.0
    pixel_size = image_size_mm / num_pixels

    # Build the 2D image by accumulating Gaussian blobs
    # Since we're in 2D simulation, rays only have y-offsets.
    # We place them along y=0 on the focal plane (x-axis of image).
    image = np.zeros((num_pixels, num_pixels))

    # Pixel coordinate arrays
    coords = np.linspace(-half_size, half_size, num_pixels)
    xx, yy = np.meshgrid(coords, coords)

    for y_off in y_offsets:
        # Each ray contributes a 2D Gaussian centered at (y_off, 0)
        dist_sq = (xx - y_off) ** 2 + yy ** 2
        image += np.exp(-dist_sq / (2.0 * blur_sigma_mm ** 2))

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

    # Add info text
    ax.text(0.02, 0.02,
            f"RMS spot: {rms_spot:.4f} mm\n"
            f"Blur sigma: {blur_sigma_mm:.4f} mm\n"
            f"Rays: {len(y_offsets)}",
            transform=ax.transAxes, fontsize=9,
            verticalalignment="bottom", color="white",
            bbox=dict(boxstyle="round", facecolor="black", alpha=0.6))

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
